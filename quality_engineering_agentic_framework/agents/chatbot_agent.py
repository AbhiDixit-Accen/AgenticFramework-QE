import json
from typing import Dict, List, Any, Optional, Tuple
from quality_engineering_agentic_framework.llm.llm_factory import LLMFactory
from quality_engineering_agentic_framework.utils.rag.rag_system import (
    load_documents, 
    split_documents, 
    create_vector_db, 
    synthesize_requirements_for_query
)
from quality_engineering_agentic_framework.agents.requirement_interpreter import TestCaseGenerationAgent
from quality_engineering_agentic_framework.agents.test_script_generator import TestScriptGenerator
from quality_engineering_agentic_framework.agents.agent_interface import AgentInterface
from quality_engineering_agentic_framework.web.api.models import ChatMessage

class ChatbotAgent(AgentInterface):
    """
    ChatbotAgent handles the intelligence for the Quality Engineering Chat Bot.
    It manages intent detection, RAG retrieval, and response generation.
    """
    
    def __init__(self, llm: Any, config: Dict[str, Any]):
        """
        Initialize the agent with LLM and configuration.
        """
        super().__init__(llm, config)
        
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

    async def process(self, input_data: Any, test_cases: List[Dict] = None, agent_config: Dict[str, Any] = None) -> Any:
        """
        Implementation of the abstract process method.
        Simply delegates to process_request for now.
        """
        if isinstance(input_data, str):
            return await self.process_request(input_data, test_cases=test_cases, agent_config=agent_config)
        return "Invalid input data for ChatbotAgent"

    async def chat(self, messages: List[ChatMessage], test_cases: List[Dict] = None, agent_config: Dict[str, Any] = None) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Process a chat conversation.
        """
        latest_user_message = next((m for m in reversed(messages) if m.role == "user"), None)
        if not latest_user_message:
            return "I'm ready to help. What's on your mind?", None
            
        # Convert ChatMessage list to history format expected by process_request
        history = [{"role": m.role, "content": m.content} for m in messages[:-1]]
        
        # Process request using existing logic
        result = await self.process_request(latest_user_message.content, test_cases=test_cases, chat_history=history, agent_config=agent_config)
        
        # Extract artifacts
        artifacts = {}
        if result.get("new_test_cases"):
            artifacts["test_cases"] = result["new_test_cases"]
        
        if result.get("new_test_scripts"):
            artifacts["test_scripts"] = result["new_test_scripts"]
            
        if result.get("rag_context"):
            artifacts["product_context"] = result["rag_context"]
        
        return result["response"], artifacts if artifacts else None

    async def process_request(self, user_input: str, test_cases: List[Dict] = None, chat_history: List[Dict] = None, agent_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a user request and return the response and context.
        """
        # 1. Detect Intent
        intent = self._detect_intent(user_input, test_cases)
        
        # 2. Get RAG Context
        rag_context = self._get_rag_context(user_input)
        
        # 3. Construct Prompt with conversation history
        prompt = self._construct_prompt(user_input, intent, rag_context, test_cases, chat_history or [])
        
        # 4. Generate Response
        response_text = ""
        
        # Handle Refinement (Update existing test cases)
        if intent == "refine" and self.test_case_agent and test_cases:
            try:
                refine_result = await self.test_case_agent.refine(test_cases, user_input)
                new_cases = refine_result.get("test_cases", [])
                rag_context = refine_result.get("product_context", rag_context)
                
                if new_cases:
                    response_text = f"I've updated the test cases based on your feedback. You can find the revised set in the artifacts section of this chat."
                    return {
                        "response": response_text,
                        "intent": intent,
                        "rag_context": rag_context,
                        "new_test_cases": new_cases
                    }
            except Exception as e:
                print(f"Refinement failed: {e}")

        # Use specialized agent for test case generation if available
        if intent == "generate" and self.test_case_agent:
            try:
                # Delegate to TestCaseGenerationAgent
                test_cases_result = await self.test_case_agent.process(user_input)
                # Handle both list and dict returns from specialized agent
                if isinstance(test_cases_result, dict):
                    new_cases = test_cases_result.get("test_cases", [])
                    rag_context = test_cases_result.get("product_context", rag_context)
                else:
                    new_cases = test_cases_result
                
                if new_cases:
                    response_text = f"I've generated {len(new_cases)} test cases based on your requirements. You can view and download them in the artifacts section below."
                    result = {
                        "response": response_text,
                        "intent": intent,
                        "rag_context": rag_context,
                        "new_test_cases": new_cases
                    }
                    return result
            except Exception as e:
                print(f"TestCaseGenerationAgent failed, falling back to LLM: {e}")
        
        # Use specialized agent for script generation if available
        if intent == "script" and self.script_generator and test_cases:
            try:
                # Smart detection of language and framework from user input
                detected_lang = None
                detected_framework = None
                
                lang_keywords = ["python", "java", "javascript", "c#", "typesript"]
                for lang in lang_keywords:
                    if lang in user_input.lower():
                        detected_lang = lang
                        break
                
                framework_keywords = ["pytest", "unittest", "robot", "junit", "testng", "cucumber", "jest", "mocha", "cypress", "nunit", "xunit", "mstest"]
                for fw in framework_keywords:
                    if fw in user_input.lower():
                        detected_framework = fw
                        break

                # Update script generator config if options provided or detected
                if agent_config or detected_lang or detected_framework:
                    lang_to_use = detected_lang or (agent_config.get("language") if agent_config else None)
                    fw_to_use = detected_framework or (agent_config.get("framework") if agent_config else None)
                    
                    if lang_to_use:
                        self.script_generator.language = lang_to_use.lower()
                    if fw_to_use:
                        self.script_generator.framework = fw_to_use.lower()
                    
                    try:
                        self.script_generator._validate_config()
                    except Exception as ve:
                        print(f"Config validation partial failure: {ve}")

                script_result = await self.script_generator.process(test_cases)
                if script_result:
                    response_text = f"✅ I've generated the {self.script_generator.language} ({self.script_generator.framework}) automation scripts for you. You can find them in the section below."
                    if detected_lang or detected_framework:
                        response_text = f"✅ I've detected your preference for **{self.script_generator.language}** and **{self.script_generator.framework}**. " + response_text
                        
                    return {
                        "response": response_text,
                        "intent": intent,
                        "rag_context": rag_context,
                        "new_test_cases": None,
                        "new_test_scripts": script_result if isinstance(script_result, dict) else {"script.py": script_result}
                    }
            except Exception as e:
                print(f"TestScriptGenerator failed: {e}")
                response_text = f"⚠️ Error generating script: {str(e)}"
                return {"response": response_text, "intent": intent, "rag_context": rag_context, "new_test_cases": None}
        
        # Default LLM generation if specialized agents fail or intent is different
        response_text = await self.llm.generate(prompt)
        
        # Post-process
        result = {
            "response": response_text,
            "intent": intent,
            "rag_context": rag_context,
            "new_test_cases": None
        }
        
        if intent == "generate":
            new_cases = self._extract_json_test_cases(response_text)
            if new_cases:
                result["new_test_cases"] = new_cases
                result["response"] = f"I've identified {len(new_cases)} test cases in my response. You can view them formatted in the artifacts section below."
                                   
        return result

    def _detect_intent(self, user_input: str, test_cases: List = None) -> str:
        user_lower = user_input.lower()
        
        # 1. Script Generation
        if any(word in user_lower for word in ["script", "code", "automate", "automation"]):
            return "script"
            
        # 2. Refinement (if test cases exist and user is asking for changes)
        if test_cases and any(word in user_lower for word in ["add", "remove", "delete", "update", "change", "modify", "instead", "refine", "step"]):
            return "refine"
            
        # 3. Test Case Generation
        if any(word in user_lower for word in ["generate", "create", "make", "write"]) and "test" in user_lower:
            return "generate"
            
        # 4. Explanation
        if any(word in user_lower for word in ["explain", "what is", "what are", "describe"]):
            return "explain"
            
        # 5. Suggestions
        if any(word in user_lower for word in ["suggest", "improve", "better"]):
            return "suggest"
            
        return "general"

    def _get_rag_context(self, query: str) -> str:
        try:
            documents = load_documents()
            if documents:
                chunks = split_documents(documents)
                api_key = self.config.get("api_key")
                vector_db = create_vector_db(chunks, openai_api_key=api_key)
                return synthesize_requirements_for_query(
                    vector_db, 
                    query=query, 
                    openai_api_key=api_key, 
                    model=self.config.get("model"), 
                    top_k=5
                )
        except Exception as e:
            print(f"RAG Error: {e}")
        return ""

    def _construct_prompt(self, user_input: str, intent: str, context: str, test_cases: List, chat_history: List[Dict]) -> str:
        base = self.role_and_goals
        
        history_text = ""
        if chat_history:
            recent_history = chat_history[-5:]
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
