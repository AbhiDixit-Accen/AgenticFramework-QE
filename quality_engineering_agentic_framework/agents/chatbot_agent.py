import json
import asyncio
from typing import Dict, List, Any, Optional

from quality_engineering_agentic_framework.llm.llm_factory import LLMFactory
from quality_engineering_agentic_framework.utils.rag.rag_system import (
    load_documents, 
    split_documents, 
    create_vector_db, 
    synthesize_requirements_for_query
)
from quality_engineering_agentic_framework.agents.requirement_interpreter import TestCaseGenerationAgent
from quality_engineering_agentic_framework.agents.test_script_generator import TestScriptGenerator

class ChatbotAgent:
    """
    ChatbotAgent handles the intelligence for the Quality Engineering Chat Bot.
    It manages intent detection, RAG retrieval, and response generation.
    """
    
    def __init__(self, llm_config: Dict[str, Any]):
        """
        Initialize the agent with LLM configuration.
        """
        self.llm_config = llm_config
        self.llm = LLMFactory.create_llm(llm_config)
        
        # Initialize specialized agents
        try:
            self.test_case_agent = TestCaseGenerationAgent(self.llm, {})
        except Exception as e:
            print(f"Warning: Could not initialize TestCaseGenerationAgent: {e}")
            self.test_case_agent = None
        
        try:
            self.script_generator = TestScriptGenerator(self.llm, {})
        except Exception as e:
            print(f"Warning: Could not initialize TestScriptGenerator: {e}")
            self.script_generator = None
        
        self.role_and_goals = """You are a Smart Test Engineer Assistant.

CORE CAPABILITIES:
1. Understand natural language requirements
2. Ask clarifying questions if requirements are incomplete or ambiguous
3. Generate structured outputs (test cases, automation scripts)
4. Answer questions using RAG from: requirements, test cases, scripts, domain docs
5. Guide users through testing workflows

WORKFLOW MODES:
- Requirement → Test Case: Convert requirements into structured test cases
- Test Case → Automation Script: Convert test cases into executable scripts

INTERACTION STYLE:
- If user input is vague or incomplete, ASK CLARIFYING QUESTIONS before generating
- Provide structured, actionable outputs
- Cite sources from RAG when answering questions
- Be helpful to both technical and non-technical users

PRIMARY GOALS:
- Reduce manual effort in test design
- Improve test coverage & consistency
- Make testing accessible to everyone"""

    async def process_request(self, user_input: str, test_cases: List[Dict] = None, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process a user request and return the response and context.
        
        Args:
            user_input: Current user message
            test_cases: Available test cases
            chat_history: Previous conversation messages (list of {"role": "user"/"assistant", "content": "..."})
        
        Returns:
            Dict containing:
            - response (str): The bot's response
            - intent (str): Detected intent
            - rag_context (str): Retrieved context
            - new_test_cases (List): If generation occurred
        """
        # 1. Detect Intent
        intent = self._detect_intent(user_input)
        
        # 2. Get RAG Context
        rag_context = self._get_rag_context(user_input)
        
        # 3. Construct Prompt with conversation history
        prompt = self._construct_prompt(user_input, intent, rag_context, test_cases, chat_history or [])
        
        # 4. Generate Response
        response_text = ""
        test_cases_result = None  # Track agent result for later extraction
        
        # Use specialized agent for test case generation if available
        if intent == "generate" and self.test_case_agent:
            try:
                # Delegate to TestCaseGenerationAgent for better test case generation
                test_cases_result = await self.test_case_agent.process(user_input)
                if test_cases_result:
                    # TestCaseGenerationAgent returns a list of test cases directly
                    response_text = json.dumps(test_cases_result, indent=2)
            except Exception as e:
                print(f"TestCaseGenerationAgent failed, falling back to LLM: {e}")
                response_text = await self.llm.generate(prompt)
        
        # Use specialized agent for script generation if available
        elif intent == "script" and self.script_generator and test_cases:
            try:
                # Delegate to TestScriptGenerator for better script generation
                script_result = await self.script_generator.process(test_cases)
                if script_result:
                    response_text = f"✅ Generated automation script:\n\n```python\n{script_result}\n```"
            except Exception as e:
                print(f"TestScriptGenerator failed, falling back to LLM: {e}")
                response_text = await self.llm.generate(prompt)
        
        else:
            # Use regular LLM for other intents
            response_text = await self.llm.generate(prompt)
        
        # 5. Post-process (e.g. JSON extraction)
        result = {
            "response": response_text,
            "intent": intent,
            "rag_context": rag_context,
            "new_test_cases": None
        }
        
        if intent == "generate":
            # Extract test cases from response (handles both agent and LLM responses)
            new_cases = None
            
            # If using agent, test_cases_result is already the list
            if test_cases_result:
                new_cases = test_cases_result
            else:
                # If using LLM, extract from JSON string
                new_cases = self._extract_json_test_cases(response_text)
            
            if new_cases:
                result["new_test_cases"] = new_cases
                # Format test cases for human readability
                result["response"] = self._format_test_cases_for_display(new_cases)
                                   
        return result

    def _detect_intent(self, user_input: str) -> str:
        user_lower = user_input.lower()
        if any(word in user_lower for word in ["explain", "what is", "what are", "describe"]):
            return "explain"
        elif any(word in user_lower for word in ["suggest", "improve", "better"]):
            return "suggest"
        elif any(word in user_lower for word in ["generate", "create", "make", "write"]) and "test" in user_lower:
            return "generate"
        elif any(word in user_lower for word in ["script", "code", "automate", "python", "java"]):
            return "script"
        return "general"

    def _get_rag_context(self, query: str) -> str:
        try:
            # Note: Optimized to use existing DB if possible in real impl
            documents = load_documents()
            if documents:
                chunks = split_documents(documents)
                # Use key from config
                api_key = self.llm_config.get("api_key")
                vector_db = create_vector_db(chunks, openai_api_key=api_key)
                return synthesize_requirements_for_query(
                    vector_db, 
                    query=query, 
                    openai_api_key=api_key, 
                    model=self.llm_config.get("model"), 
                    top_k=5
                )
        except Exception as e:
            print(f"RAG Error: {e}")
        return ""

    def _construct_prompt(self, user_input: str, intent: str, context: str, test_cases: List, chat_history: List[Dict]) -> str:
        base = self.role_and_goals
        
        # Format conversation history (last 5 messages for context)
        history_text = ""
        if chat_history:
            recent_history = chat_history[-5:]  # Keep last 5 messages
            history_text = "\n\nCONVERSATION HISTORY:\n"
            for msg in recent_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n"
        
        if intent == "explain":
            return f"{base}{history_text}\n\nExplain these test cases:\n{json.dumps(test_cases)}\n\nUser: {user_input}"
        elif intent == "suggest":
            return f"{base}{history_text}\n\nSuggest improvements for:\n{json.dumps(test_cases)}\n\nContext:\n{context}"
        elif intent == "generate":
            return f"{base}{history_text}\n\nGenerate 3 test cases for: {user_input}\nContext: {context}\nFormat as JSON list."
        elif intent == "script":
            if not test_cases:
                return f"{base}{history_text}\n\nThe user wants scripts but hasn't generated test cases yet. Politely guide them to generate test cases first. User: {user_input}"
            return f"{base}{history_text}\n\nConvert these test cases into an automation script:\n{json.dumps(test_cases)}\n\nUser Request: {user_input}"
            
        return f"{base}{history_text}\n\nAnswer this: {user_input}\nContext: {context}"

    def _extract_json_test_cases(self, text: str) -> Optional[List]:
        import re
        try:
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return None

    def _format_test_cases_for_display(self, test_cases: List[Dict]) -> str:
        """
        Format test cases as human-readable markdown for chat display.
        """
        if not test_cases:
            return "No test cases generated."
        
        output = f"✅ **Generated {len(test_cases)} Test Cases**\n\n"
        
        for i, tc in enumerate(test_cases, 1):
            output += f"### {i}. {tc.get('title', 'Untitled Test Case')}\n\n"
            
            if tc.get('description'):
                output += f"**Description:** {tc['description']}\n\n"
            
            if tc.get('preconditions'):
                output += "**Preconditions:**\n"
                for pre in tc['preconditions']:
                    output += f"- {pre}\n"
                output += "\n"
            
            if tc.get('actions'):
                output += "**Test Steps:**\n"
                for j, action in enumerate(tc['actions'], 1):
                    output += f"{j}. {action}\n"
                output += "\n"
            
            if tc.get('expected_results'):
                output += "**Expected Results:**\n"
                for result in tc['expected_results']:
                    output += f"- {result}\n"
                output += "\n"
            
            if tc.get('test_data') and tc['test_data']:
                output += f"**Test Data:** `{json.dumps(tc['test_data'])}`\n\n"
            
            output += "---\n\n"
        
        return output
