"""
Test Case Generation Agent

This agent converts plaintext or structured software requirements into structured test cases.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple

from quality_engineering_agentic_framework.agents.agent_interface import AgentInterface
from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface
from quality_engineering_agentic_framework.utils.logger import get_logger
from quality_engineering_agentic_framework.web.api.models import ChatMessage, TestCase
from quality_engineering_agentic_framework.utils.rag.rag_system import DATA_PATH, load_documents, split_documents, create_vector_db, synthesize_requirements, synthesize_requirements_for_query

logger = get_logger(__name__)


class TestCaseGenerationAgent(AgentInterface):
    """
    Agent that converts requirements into structured test cases.
    """
    
    def __init__(self, llm: LLMInterface, config: Dict[str, Any]):
        """
        Initialize the Test Case Generation agent.
        
        Args:
            llm: LLM instance to use for generation
            config: Dictionary containing agent-specific configuration
        """
        super().__init__(llm, config)
        self.output_format = config.get("output_format", "gherkin")
        
        # Load prompt template
        prompt_template_path = config.get("prompt_template")
        self.prompt_template = self._load_prompt_template(prompt_template_path)
        
        # Initialize context
        self.context = {
            "output_format": self.output_format,
            "last_requirements": "",
            "last_generated_count": 0
        }
        
        logger.info(f"Initialized Test Case Generation agent with output format: {self.output_format}")
    
    def _load_prompt_template(self, template_path: Optional[str]) -> str:
        """
        Load the prompt template from a file or use default.
        
        Args:
            template_path: Path to the prompt template file
            
        Returns:
            Prompt template as a string
        """
        default_template = """
        You are a test case generator and working a senior QA engineer that converts software requirements into structured test cases.
        
        Product/System Context:
        {product_context}
        

        Given the following software requirement:
        
        {requirement}
        
        Generate required unique, non-redundant test cases as possible, covering all combinations, edge cases, and scenarios, in {output_format} format.
        
        Each test case should include:
        - A clear title/description
        - Preconditions (Given)
        - Actions (When)
        - Expected results (Then)
        - Any relevant test data or variables
        
        Be exhaustive, specific, and detailed in your test cases. Avoid duplicates and ensure coverage of all possible situations.
        """
        
        if template_path and os.path.exists(template_path):
            try:
                with open(template_path, 'r') as file:
                    return file.read()
            except Exception as e:
                logger.warning(f"Failed to load prompt template from {template_path}: {str(e)}")
                logger.warning("Using default prompt template instead")
        
        return default_template
    
    async def process(self, input_data: str, selected_documents: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Process the requirements and generate structured test cases.
        
        Args:
            input_data: Requirements text
            selected_documents: Optional list of specific filenames to use for RAG
            
        Returns:
            List of structured test cases
        """
        print("\n\n!!! TestCaseGenerationAgent.process CALLED !!!\n\n")
        logger.info("Processing requirements with Test Case Generation agent")
        
        # Update context
        self.context["last_requirements"] = input_data
        
        # 1. Synthesize Product/System Context using RAG
        try:
            # Re-using the functions from rag_system module
            from quality_engineering_agentic_framework.utils.rag.rag_system import (
                load_documents, split_documents, create_vector_db, 
                synthesize_requirements_for_query, get_selection_fingerprint, CACHE_PATH
            )
            from langchain_core.documents import Document
            import os
            import json
            
            logger.info("Calling RAG: load_documents")
            print(f"[RAG DEBUG] Starting RAG system with selected_documents: {selected_documents}")
            
            api_key = self.llm.config.get('api_key') if hasattr(self.llm, 'config') else None
            llm_model = self.llm.config.get('model') if hasattr(self.llm, 'config') else None
            
            # FAST PATH: Check fingerprint before loading anything
            current_fingerprint = get_selection_fingerprint(file_list=selected_documents)
            print(f"[RAG DEBUG] Selection fingerprint: {current_fingerprint}")
            
            reuse_cache = False
            if os.path.exists(CACHE_PATH):
                try:
                    with open(CACHE_PATH, 'r') as f:
                        cached_fp = json.load(f).get("fingerprint")
                        if cached_fp == current_fingerprint:
                            reuse_cache = True
                            print("[RAG DEBUG] CACHE HIT: Skipping all ingestion steps.")
                except: pass

            if not reuse_cache:
                # 2. INGESTION PATH
                documents = load_documents(file_list=selected_documents)
                
                if not documents:
                    if selected_documents is not None and len(selected_documents) == 0:
                        error_detail = "No documents selected in the Knowledge Hub. Please select at least one document to provide context."
                    elif selected_documents:
                        error_detail = f"None of the selected documents could be loaded: {selected_documents}"
                    else:
                        error_detail = f"No documents found in Knowledge Hub directory ({DATA_PATH})"
                    
                    logger.warning(error_detail)
                    print(f"[RAG DEBUG] {error_detail}")
                    product_context = f"Unable to retrieve documentation. {error_detail}"
                else:
                    logger.info(f"Loaded {len(documents)} documents")
                    print(f"[RAG DEBUG] Successfully loaded {len(documents)} documents")
                    
                    # LAYERED INDEXING: Generate summaries for each document
                    from quality_engineering_agentic_framework.utils.rag.rag_system import summarize_document
                    summary_documents = []
                    docs_by_source = {}
                    for d in documents:
                        src = d.metadata.get("source", "unknown")
                        if src not in docs_by_source:
                            docs_by_source[src] = []
                        docs_by_source[src].append(d.page_content)
                    
                    for src, contents in docs_by_source.items():
                        print(f"[RAG DEBUG] Summarizing document: {src}")
                        full_content = "\n\n".join(contents)
                        summary_text, doc_type = summarize_document(full_content, src, openai_api_key=api_key, model=llm_model)
                        summary_documents.append(Document(
                            page_content=summary_text,
                            metadata={
                                "source": src,
                                "layer": "document_summary",
                                "type": doc_type
                            }
                        ))
                    
                    # Split raw documents into chunks
                    raw_chunks = split_documents(documents)
                    all_chunks = raw_chunks + summary_documents
                    
                    if not all_chunks:
                        print("[RAG DEBUG] Processing resulted in 0 manageable data segments")
                        product_context = "No specific project documentation found. (Processing resulted in 0 segments)"
                    else:
                        print(f"[RAG DEBUG] Indexing {len(all_chunks)} segments (raw + summaries)")
                        try:
                            print("[RAG DEBUG] Creating vector database...")
                            vector_db = create_vector_db(all_chunks, openai_api_key=api_key, fingerprint=current_fingerprint)
                            print("[RAG DEBUG] Vector DB ready")
                        except Exception as inner_error:
                            print(f"[RAG DEBUG] Vector DB creation FAILED: {inner_error}")
                            raise inner_error
            else:
                # 3. CACHE HIT PATH
                try:
                    print("[RAG DEBUG] Loading existing vector database from cache...")
                    vector_db = create_vector_db(None, openai_api_key=api_key, fingerprint=current_fingerprint)
                    print("[RAG DEBUG] Vector DB loaded from cache.")
                except Exception as cache_err:
                    print(f"[RAG DEBUG] Cache load FAILED: {cache_err}. FORCING RE-INGESTION...")
                    # FALLBACK: If cache load fails, recurse or repeat ingestion logic
                    # To keep it simple, we'll just repeat the ingestion logic here or clear reuse_cache
                    reuse_cache = False
                    # Triggering ingestion path manually by repeating the block
                    documents = load_documents(file_list=selected_documents)
                    if documents:
                        # Re-run full ingestion logic to be safe
                        from quality_engineering_agentic_framework.utils.rag.rag_system import summarize_document
                        summary_documents = []
                        docs_by_source = {}
                        for d in documents:
                            src = d.metadata.get("source", "unknown")
                            if src not in docs_by_source:
                                docs_by_source[src] = []
                            docs_by_source[src].append(d.page_content)
                        
                        for src, contents in docs_by_source.items():
                            full_content = "\n\n".join(contents)
                            summary_text, _ = summarize_document(full_content, src, openai_api_key=api_key, model=llm_model)
                            summary_documents.append(Document(page_content=summary_text, metadata={"source": src, "layer": "document_summary"}))
                        
                        raw_chunks = split_documents(documents)
                        all_chunks = raw_chunks + summary_documents
                        vector_db = create_vector_db(all_chunks, openai_api_key=api_key, fingerprint=current_fingerprint)
                    else:
                        raise cache_err

            # If we have a DB (either new or cached), retrieve context
            if 'vector_db' in locals():
                print("[RAG DEBUG] Retrieving relevant context based on user input...")
                product_context = synthesize_requirements_for_query(
                    vector_db, 
                    query=input_data,
                    openai_api_key=api_key, 
                    model=llm_model,
                    top_k=20
                )
                print("[RAG DEBUG] Context retrieved and synthesized successfully")
            else:
                # Handle cases where DB fails to load or load_documents fails
                if 'product_context' not in locals():
                    product_context = "No specific project documentation found. (Database could not be initialized)"
                    
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"[RAG DEBUG] TOP-LEVEL EXCEPTION: {type(e).__name__}: {error_msg}")
            logger.error(f"Failed to synthesize requirements via RAG: {e}")
            logger.error(traceback.format_exc())
            
            # Add user-friendly error handling for common issues
            if "readonly database" in error_msg.lower() or "code: 1032" in error_msg.lower():
                friendly_msg = (
                    "Database Persistence Error: The system encountered a filesystem lock while trying to update the knowledge base. "
                    "I've implemented a fallback mechanism, so please try again—it should work on the next attempt."
                )
            elif "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                friendly_msg = "API Key Error: Please check if your OpenAI API key is correct and has sufficient credits."
            else:
                friendly_msg = f"Knowledge synthesis encountered an issue: {error_msg}"
                
            product_context = f"Unable to retrieve documentation. {friendly_msg}"

        
        # Prepare the final prompt with product context
        prompt = f"""
        ### PROJECT SOURCE OF TRUTH (Product Details)
        The following information is the authoritative documentation for the software under test. 
        Treat this as your primary reference for all feature behavior, technical details, and business rules.
        
        --- START PROJECT DETAILS ---
        {product_context}
        --- END PROJECT DETAILS ---
        
        ### USER REQUIREMENT
        The user wants to test the following:
        "{input_data}"
        
        ### INSTRUCTION
        Please generate comprehensive test cases based on the User Requirement above.
        - If 'Project Source of Truth' contains specific details, use them to fill in all missing data and logic.
        - If 'Project Source of Truth' indicates no documentation was found, use general industry standards and best practices for the domain mentioned in the User Requirement.
        
        Cite your sources in the 'rag_ref' field (if no documentation, mention 'General Knowledge').
        """
        
        print("\n" + "#" * 80)
        print("FINAL PROMPT SENT TO LLM (VERIFY RAG CONTENT BELOW)")
        print("#" * 80)
        print(f"\nPRODUCT CONTEXT RETRIEVED:\n{product_context[:1000]}...\n")
        print("#" * 80 + "\n")
        
        logger.info(f"Generated Prompt (First 2000 chars):\n{prompt[:2000]}...")
        
        # Define the expected JSON schema for the output
        json_schema = {
            "type": "object",
            "properties": {
                "test_cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "preconditions": {"type": "array", "items": {"type": "string"}},
                            "actions": {"type": "array", "items": {"type": "string"}},
                            "expected_results": {"type": "array", "items": {"type": "string"}},
                            "test_data": {"type": "object"},
                            "rag_ref": {"type": "string", "description": "Cite a specific detail from the Product Context used in this test case"}
                        },
                        "required": ["title", "preconditions", "actions", "expected_results", "rag_ref"]
                    }
                }
            },
            "required": ["test_cases"]
        }
        
        system_message = f"""
        You are a Quality Engineering Expert and Test Architect.
        
        Your mission is to map incoming "User Requirements" against the "Project Source of Truth" documentation.
        
          CRITICAL RULES:
          1. AUTHORITATIVE DATA: Never use generic placeholders if the Project Details contain specific data (e.g., specific usernames like 'performance_glitch_user', specific error strings, or specific URLs).
          2. BEHAVIORAL FIDELITY: Ensure the 'Actions' and 'Expected Results' exactly match the logic described in the Project Details.
          3. PROJECT IDENTITY: Test cases should explicitly name the product (e.g., 'Verify Login') and reference its specific components.
          4. DATA DICTIONARY: Populate the 'test_data' field with real values found in the Project Details.
          5. LOGIN/NAVIGATION/URL STEPS (MANDATORY WHEN PRESENT IN RAG):
              - If the Product Details mention authentication, login, SSO/MFA, base URLs, or navigation paths, you MUST include those as explicit steps inside 'Actions'.
              - Do NOT skip initial steps (open URL, login, navigate) when they are present in the context.
              - Each such step must be grounded in the Product Details and referenced in 'rag_ref'.
        
        For each test case, you MUST populate the 'rag_ref' field with the specific section or quote from the Project Details that justifies this test case.
        
        Your output must be in valid JSON format according to the provided schema.
        """
        
        try:
            # Generate test cases using the LLM
            response = await self.llm.generate_with_json_output(
                prompt=prompt,
                json_schema=json_schema,
                system_message=system_message
            )
            
            test_cases = response.get("test_cases", [])
            logger.info(f"Generated {len(test_cases)} test cases")
            
            # Update context
            self.context["last_generated_count"] = len(test_cases)
            
            return {
                "test_cases": test_cases,
                "product_context": product_context
            }
        
        except Exception as e:
            logger.error(f"Error generating test cases: {str(e)}")
            raise
    
    async def chat(self, messages: List[ChatMessage]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Process a list of chat messages and return a response.
        
        Args:
            messages: List of chat messages
            
        Returns:
            Tuple of (response message content, artifacts if any)
        """
        # Extract the latest user message
        latest_user_message = next((m for m in reversed(messages) if m.role == "user"), None)
        
        if not latest_user_message:
            return "I'm a Test Case Generation Agent. How can I help you today?", None
        
        user_message = latest_user_message.content
        
        # FOR ANY USER MESSAGE, ALWAYS TREAT IT AS A TEST CASE GENERATION REQUEST
        # This ensures the agent will always try to generate test cases
        
        # First check if it's a prompt request
        if self._is_prompt_request(user_message):
            return await self._handle_prompt_request(user_message)
        # Format the conversation for the LLM in a structured way
        formatted_messages = []
        for msg in messages[-10:]:  # Limit to last 10 messages for context
            formatted_messages.append(f"{msg.role.upper()}: {msg.content}")
        
        conversation = "\n".join(formatted_messages)
        
        # Create a prompt with guidance specific to test case generation
        prompt = f"""You are a Test Case Generation Agent that helps create test cases from requirements.

Previous conversation:
{conversation}

Respond to the user's latest message. Be helpful, concise, and professional.
If they ask about test case generation, explain your capabilities and what information you need.
If they ask about testing methodologies, provide accurate information.
If they ask about other testing topics, provide helpful guidance.
"""
        
        # Get response from LLM
        response = await self.llm.generate(prompt)
        
        return response, None
    
    def _is_prompt_request(self, message: str) -> bool:
        """
        Check if a message is a request to view or update the prompt/context.
        
        Args:
            message: Message content
            
        Returns:
            True if the message is a prompt/context request, False otherwise
        """
        prompt_keywords = [
            "show prompt", "display prompt", "view prompt", 
            "update prompt", "change prompt", "modify prompt",
            "show context", "display context", "view context",
            "update context", "change context", "modify context",
            "set output format", "change output format"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in prompt_keywords)
        
    def _is_generation_request(self, message: str) -> bool:
        """
        Check if a message is a request to generate test cases.
        
        Args:
            message: Message content
            
        Returns:
            True if the message is a test case generation request, False otherwise
        """
        # FIXED: Always return True for any message to ensure test cases are generated
        # This ensures that any user input will be treated as a test case generation request
        return True
    
    async def _handle_prompt_request(self, message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Handle a request to view or update the prompt/context.
        
        Args:
            message: Message content
            
        Returns:
            Tuple of (response message content, artifacts if any)
        """
        message_lower = message.lower()
        
        # Show prompt
        if any(keyword in message_lower for keyword in ["show prompt", "display prompt", "view prompt"]):
            return self._get_prompt_template_response()
        
        # Update prompt
        elif any(keyword in message_lower for keyword in ["update prompt", "change prompt", "modify prompt"]):
            # Extract the new prompt from the message
            if ":" in message:
                new_prompt = message.split(":", 1)[1].strip()
                return self._update_prompt_template(new_prompt)
            else:
                return "To update the prompt, please provide the new prompt after a colon. For example: 'update prompt: Your new prompt here'", None
        
        # Show context
        elif any(keyword in message_lower for keyword in ["show context", "display context", "view context"]):
            return self._get_context_response()
        
        # Update output format
        elif any(keyword in message_lower for keyword in ["set output format", "change output format"]):
            # Extract the new format from the message
            if ":" in message:
                new_format = message.split(":", 1)[1].strip()
                return self._update_output_format(new_format)
            else:
                return "To update the output format, please provide the new format after a colon. For example: 'set output format: gherkin'", None
        
        return "I'm not sure what you're asking about the prompt or context. You can show or update the prompt, view the context, or change the output format.", None
    
    def _get_prompt_template_response(self) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Get a response showing the current prompt template.
        
        Returns:
            Tuple of (response message content, artifacts if any)
        """
        if not self.prompt_template:
            return "No prompt template is currently set. You can set one with 'update prompt: Your prompt here'", None
        
        response = f"Current prompt template:\n\n```\n{self.prompt_template}\n```\n\nYou can update it with 'update prompt: Your new prompt here'"
        return response, {"prompt_template": self.prompt_template}
    
    def _update_prompt_template(self, new_prompt: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Update the prompt template.
        
        Args:
            new_prompt: New prompt template
            
        Returns:
            Tuple of (response message content, artifacts if any)
        """
        self.prompt_template = new_prompt
        self.config["prompt_template"] = new_prompt
        
        response = f"Prompt template updated successfully. The new prompt is:\n\n```\n{self.prompt_template}\n```"
        return response, {"prompt_template": self.prompt_template}
    
    def _get_context_response(self) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Get a response showing the current context.
        
        Returns:
            Tuple of (response message content, artifacts if any)
        """
        context_str = json.dumps(self.context, indent=2)
        response = f"Current context variables:\n\n```json\n{context_str}\n```\n\nYou can change the output format with 'set output format: <format>'"
        return response, {"context": self.context}
    
    def _update_output_format(self, new_format: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Update the output format.
        
        Args:
            new_format: New output format
            
        Returns:
            Tuple of (response message content, artifacts if any)
        """
        self.output_format = new_format
        self.config["output_format"] = new_format
        self.context["output_format"] = new_format
        
        response = f"Output format updated successfully to '{new_format}'."
        return response, {"context": self.context}
    
    def _extract_requirements(self, messages: List[ChatMessage]) -> str:
        """
        Extract requirements from the conversation.
        
        Args:
            messages: List of chat messages
            
        Returns:
            Extracted requirements as a string
        """
        # Look for requirements in the latest message first
        latest_user_message = next((m for m in reversed(messages) if m.role == "user"), None)
        if not latest_user_message:
            return ""
        
        # Check if the latest message contains requirements
        if len(latest_user_message.content.split()) > 20:  # Assume longer messages might contain requirements
            return latest_user_message.content
        
        # Look for requirements in previous messages
        requirements = []
        for msg in reversed(messages):
            if msg.role == "user" and len(msg.content.split()) > 20:
                requirements.append(msg.content)
                if len(requirements) >= 2:  # Limit to last 2 substantial messages
                    break
        
        return "\n\n".join(requirements)
    
    def get_name(self) -> str:
        """
        Get the name of the agent.
        
        Returns:
            Agent name as a string
        """
        return "test_case_generation"
    
    def get_description(self) -> str:
        """
        Get a description of what the agent does.
        
        Returns:
            Agent description as a string
        """
        return "Converts plaintext or structured software requirements into structured test cases."
    

# Add this function at the end of your requirement_interpreter.py file
# This provides a simple interface for other parts of your application

def generate_test_cases_from_requirements(requirements_text: str, llm_config: Dict[str, Any] = None) -> str:
    """
    Simple wrapper function to generate test cases from requirements text.
    This provides backward compatibility with the simple function interface.
    
    Args:
        requirements_text: Requirements text input
        llm_config: Optional LLM configuration
        
    Returns:
        Formatted test cases as a string
    """
    try:
        # Default LLM config if none provided
        if llm_config is None:
            llm_config = {
                "provider": "openai",
                "model": "gpt-3.5-turbo", 
                "temperature": 0.7,
                "max_tokens": 2000
            }
        
        # You'll need to implement this based on your LLM interface
        # For now, return a simple formatted response
        if not requirements_text or not requirements_text.strip():
            return "Please provide requirements to generate test cases."
        
        # Handle simple cases like "gmail.com"
        if any(domain in requirements_text.lower() for domain in ['gmail', 'gmail.com']):
            return """Thank you for providing your requirement around Gmail.com. To generate comprehensive test cases, I'll need specific details such as:

1. What functionalities of Gmail do you want to test? (login, compose email, attachments, etc.)
2. Are there specific user interactions you're concerned about?
3. Any particular features or edge cases that should be covered?

Please provide more details so I can generate thorough test cases for your Gmail-related requirements."""
        
        # For more complex requirements, generate structured test cases
        requirements_list = [req.strip() for req in requirements_text.split('\n') if req.strip()]
        
        test_cases = ["# Generated Test Cases\n"]
        
        for i, req in enumerate(requirements_list, 1):
            test_cases.extend([
                f"## Test Case {i}: Verify {req}",
                f"**Requirement**: {req}",
                "**Preconditions**:",
                "• Test environment is set up and accessible",
                "• Required test data is available",
                "• System is in a clean state",
                "",
                "**Actions**:",
                "1. Initialize the test environment",
                "2. Set up necessary preconditions",
                f"3. Execute actions to verify: {req}",
                "4. Capture and validate results",
                "5. Clean up test environment",
                "",
                "**Expected Results**:",
                f"• The requirement '{req}' is successfully verified",
                "• System behaves as expected",
                "• No errors or unexpected behavior occurs",
                "• All validation criteria are met",
                "",
                "**Test Data**: [Specify relevant test data requirements]",
                "**Environment**: [Specify test environment requirements]",
                ""
            ])
        
        return "\n".join(test_cases)
        
    except Exception as e:
        logger.error(f"Error in generate_test_cases_from_requirements wrapper: {str(e)}")
        return f"Error generating test cases: {str(e)}"


def generate_test_cases_for_ui(requirements_text: str, llm_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Generate test cases in a format suitable for UI display.
    
    Args:
        requirements_text: Requirements text input
        llm_config: Optional LLM configuration
        
    Returns:
        List of structured test case dictionaries
    """
    try:
        # Get the formatted text
        test_cases_text = generate_test_cases_from_requirements(requirements_text, llm_config)
        
        # Parse into structured format
        test_cases = []
        current_case = None
        
        for line in test_cases_text.split('\n'):
            if line.startswith('## Test Case'):
                if current_case:
                    test_cases.append(current_case)
                
                # Extract test case name
                import re
                match = re.search(r'Test Case \d+: (.*)', line)
                title = match.group(1) if match else "Untitled Test Case"
                
                current_case = {
                    "title": title,
                    "description": "",
                    "preconditions": [],
                    "actions": [],
                    "expected_results": [],
                    "test_data": {}
                }
            
            elif current_case:
                if line.startswith('**Requirement**:'):
                    current_case["description"] = line.replace('**Requirement**:', '').strip()
                elif line.startswith('**Preconditions**:'):
                    continue  # Header
                elif line.startswith('**Actions**:'):
                    continue  # Header  
                elif line.startswith('**Expected Results**:'):
                    continue  # Header
                elif line.startswith('• ') and 'preconditions' in str(current_case):
                    current_case["preconditions"].append(line[2:].strip())
                elif line.strip() and any(line.strip().startswith(f'{i}.') for i in range(1, 10)):
                    current_case["actions"].append(line.strip())
                elif line.startswith('• ') and len(current_case["preconditions"]) > 0:
                    current_case["expected_results"].append(line[2:].strip())
        
        # Add the last test case
        if current_case:
            test_cases.append(current_case)
        
        return test_cases
        
    except Exception as e:
        logger.error(f"Error in generate_test_cases_for_ui: {str(e)}")
        return []