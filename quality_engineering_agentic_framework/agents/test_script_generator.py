"""
Test Script Generator Agent

This agent transforms structured test cases into executable Selenium test scripts.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple

from quality_engineering_agentic_framework.agents.agent_interface import AgentInterface
from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface
from quality_engineering_agentic_framework.utils.logger import get_logger
from quality_engineering_agentic_framework.web.api.models import ChatMessage

logger = get_logger(__name__)


class TestScriptGenerator(AgentInterface):
    """
    Agent that generates executable Selenium test scripts from test cases.
    """
    
    def __init__(self, llm: LLMInterface, config: Dict[str, Any]):
        """
        Initialize the Test Script Generator agent.
        
        Args:
            llm: LLM instance to use for generation
            config: Dictionary containing agent-specific configuration
        """
        super().__init__(llm, config)
        # Ensure all configuration values are properly set with defaults
        self.language = str(config.get("language", "python")).lower().strip()
        self.framework = str(config.get("framework", "pytest")).lower().strip()
        self.browser = str(config.get("browser", "chrome")).lower().strip()
        
        # Log the configuration for debugging
        logger.info(f"Initialized TestScriptGenerator with: language={self.language}, framework={self.framework}, browser={self.browser}")
        
        # Validate language and framework combination
        self._validate_config()
        
        # Load prompt template
        prompt_template_path = config.get("prompt_template")
        self.prompt_template = self._load_prompt_template(prompt_template_path)
        
        logger.info(f"Initialized Test Script Generator agent with framework: {self.framework}, browser: {self.browser}")
    
    def _load_prompt_template(self, template_path: Optional[str]) -> str:
        """
        Load the prompt template from a file or use default.
        
        Args:
            template_path: Path to the prompt template file
            
        Returns:
            Prompt template as a string
        """
        default_template = """
        You are a test automation expert that converts structured test cases into executable test scripts.
        
        Given the following test cases:
        
        {test_cases}
        
        Generate test scripts using {language} programming language, {framework} framework and {browser} browser that implement these test cases.
        
        Your code should:
        1. Include all necessary imports
        2. Use appropriate design patterns (like Page Object Model for UI tests)
        3. Include proper setup and teardown methods
        4. Handle waits and synchronization properly
        5. Include appropriate assertions
        6. Be well-commented and follow the language's style guidelines
        7. Use appropriate testing libraries for the selected language and framework
        
        Provide complete, executable code that can be run with minimal modifications.
        """
        
        if template_path and os.path.exists(template_path):
            try:
                with open(template_path, 'r') as file:
                    return file.read()
            except Exception as e:
                logger.warning(f"Failed to load prompt template from {template_path}: {str(e)}")
                logger.warning("Using default prompt template instead")
        
        return default_template
    
    def _validate_config(self):
        """Validate the language and framework configuration."""
        valid_languages = {
            'python': ['pytest', 'unittest', 'robot'],
            'java': ['junit', 'testng', 'cucumber'],
            'javascript': ['jest', 'mocha', 'cypress'],
            'c#': ['nunit', 'xunit', 'mstest']
        }
        
        if self.language not in valid_languages:
            raise ValueError(f"Unsupported language: {self.language}. Supported languages: {', '.join(valid_languages.keys())}")
        
        if self.framework not in valid_languages[self.language]:
            raise ValueError(f"Unsupported framework '{self.framework}' for language '{self.language}'. "
                         f"Supported frameworks: {', '.join(valid_languages[self.language])}")
        
        logger.info(f"Validated configuration: language={self.language}, framework={self.framework}")

    async def process(self, input_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Process the test cases and generate executable test scripts.
        
        Args:
            input_data: List of structured test cases
            
        Returns:
            Dictionary mapping file names to test script content
        """
        logger.info(f"Processing test cases with Test Script Generator agent (language={self.language}, framework={self.framework})")
        
        if not input_data:
            logger.warning("No test cases provided to process")
            return {"error": "No test cases provided"}
        
        # Convert test cases to a string representation
        test_cases_str = ""
        for i, test_case in enumerate(input_data):
            if not isinstance(test_case, dict):
                test_case = test_case.dict() if hasattr(test_case, 'dict') else {}
                
            test_cases_str += f"Test Case {i+1}: {test_case.get('title', 'Untitled')}\n"
            test_cases_str += f"Description: {test_case.get('description', 'N/A')}\n"
            test_cases_str += "Preconditions:\n"
            for pre in test_case.get('preconditions', []):
                test_cases_str += f"- {pre}\n"
            test_cases_str += "Actions:\n"
            for action in test_case.get('actions', []):
                test_cases_str += f"- {action}\n"
            test_cases_str += "Expected Results:\n"
            for result in test_case.get('expected_results', []):
                test_cases_str += f"- {result}\n"
            if test_case.get('test_data'):
                test_cases_str += f"Test Data: {test_case['test_data']}\n"
            test_cases_str += "\n"
        
        # Prepare the prompt with clear instructions
        language_name = {
            'python': 'Python',
            'java': 'Java',
            'javascript': 'JavaScript',
            'c#': 'C#'
        }.get(self.language, self.language.capitalize())
        
        file_extensions = {
            'python': 'py',
            'java': 'java',
            'javascript': 'js',
            'c#': 'cs'
        }
        
        prompt = f"""
        You are a senior test automation engineer. Please generate test scripts based on the following test cases.
        
        Requirements:
        - Language: {language_name}
        - Test Framework: {self.framework}
        - Browser: {self.browser}
        
        Test Cases:
        {test_cases_str}
        
        Your response MUST include:
        1. A main test file with test functions (e.g., test_*.{file_extensions.get(self.language, 'py')}, *Test.{file_extensions.get(self.language, 'java')})
        2. Any necessary page object/utility files
        3. Required configuration files (e.g., pom.xml for Java, package.json for JavaScript, requirements.txt for Python)
        4. Any utility or helper files
        
        Important Guidelines:
        - Use the exact framework and language specified above
        - Include all necessary imports and dependencies
        - Follow best practices for {language_name} and {self.framework}
        - Make sure the code is production-ready and well-documented
        
        Format your response with each file in a separate code block with the filename and appropriate extension:
        ```{self.language}:filename.{file_extensions.get(self.language, 'txt')}
        // code here
        ```
        """
        
        system_message = f"""
        You are a senior test automation engineer specializing in {self.language.capitalize()} test automation.
        Generate clean, maintainable, and well-documented test automation code.
        Follow these guidelines:
        - Use appropriate design patterns (like Page Object Model for UI tests)
        - Add proper waits and error handling
        - Include meaningful assertions
        - Follow the language's style guide ({'PEP 8 for Python' if self.language == 'python' else 'standard conventions'})
        - Add appropriate documentation and type hints
        - Include necessary imports and dependencies
        - Make the tests independent and idempotent
        - Use appropriate testing libraries for {self.framework}
        - Follow best practices for {self.language} test automation
        """
        
        try:
            logger.info("Sending request to LLM for test script generation")
            # Generate test scripts using the LLM with a higher temperature for more creative responses
            response = await self.llm.generate(
                prompt=prompt,
                system_message=system_message,
                temperature=0.7,
                max_tokens=3000
            )
            
            logger.debug(f"LLM response: {response[:500]}...")  # Log first 500 chars of response
            
            # Parse the response to extract individual files
            files = self._parse_files_from_response(response)
            
            if not files:
                logger.warning("No test script files were generated from the response")
                # Return the raw response as a fallback
                return {"test_script.py": f"""# Generated Test Script\n# Note: Could not parse files from response\n\n{response}"""}
            
            logger.info(f"Successfully generated {len(files)} test script files")
            return files
            
        except Exception as e:
            error_msg = f"Error generating test scripts: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Return a helpful error message as a file
            return {
                "error.txt": error_msg,
                "debug_info.txt": f"""Failed to generate test scripts. Please check the following:
- Test case format is correct
- LLM API key is valid
- LLM service is accessible

Error details: {str(e)}"""
            }
    
    async def chat(self, messages: List[ChatMessage]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Process a chat conversation with the agent.
        
        Args:
            messages: List of chat messages
            
        Returns:
            Tuple of (response message content, artifacts if any)
        """
        # Extract the latest user message
        latest_user_message = next((m for m in reversed(messages) if m.role == "user"), None)
        
        if not latest_user_message:
            return "I don't see any messages from you. How can I help with test script generation?", None
        
        # Check if this is a request to generate test scripts
        if self._is_generation_request(latest_user_message.content):
            # Check if there are test cases in the conversation
            test_cases = self._extract_test_cases(messages)
            
            if test_cases:
                try:
                    # Generate test scripts
                    test_scripts = await self.process(test_cases)
                    
                    # Create a response that includes the generated test scripts
                    response = f"I've generated {len(test_scripts)} test script files based on your test cases. Here's a summary:\n\n"
                    
                    # Add a summary of the test scripts
                    for i, (filename, _) in enumerate(list(test_scripts.items())[:3], 1):  # Show first 3 files
                        response += f"{i}. {filename}\n"
                    
                    if len(test_scripts) > 3:
                        response += f"... and {len(test_scripts) - 3} more files.\n"
                    
                    response += "\nYou can view all the test scripts in the artifacts section."
                    
                    return response, {"test_scripts": test_scripts}
                except Exception as e:
                    logger.error(f"Error generating test scripts in chat: {str(e)}")
                    return f"I encountered an error while generating test scripts: {str(e)}", None
            else:
                return "I'd be happy to generate test scripts for you. Could you please provide the test cases you'd like me to implement? You can either paste them here or upload a JSON file with the test cases.", None
        
        # Format the conversation for the LLM in a structured way
        formatted_messages = []
        for msg in messages[-10:]:  # Limit to last 10 messages for context
            formatted_messages.append(f"{msg.role.upper()}: {msg.content}")
        
        conversation = "\n".join(formatted_messages)
        
        # Create a prompt with guidance specific to test script generation
        prompt = f"""You are a Test Script Generator Agent that helps create Selenium test scripts from test cases.

Previous conversation:
{conversation}

Respond to the user's latest message. Be helpful, concise, and professional.
If they ask about test script generation, explain your capabilities and what information you need.
If they ask about Selenium, testing frameworks, or automation best practices, provide accurate information.
If they ask about other testing topics, provide helpful guidance.
"""
        
        # Get response from LLM
        response = await self.llm.generate(prompt)
        
        return response, None
    
    def _extract_test_cases(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """
        Extract test cases from the conversation.
        
        Args:
            messages: List of chat messages
            
        Returns:
            List of test cases
        """
        # Look for test cases in JSON format in the messages
        for msg in reversed(messages):
            if msg.role == "user":
                # Try to find JSON in the message
                try:
                    # Look for content between triple backticks
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', msg.content)
                    if json_match:
                        json_content = json_match.group(1)
                        test_cases = json.loads(json_content)
                        if isinstance(test_cases, list) and len(test_cases) > 0:
                            return test_cases
                        elif isinstance(test_cases, dict) and "test_cases" in test_cases:
                            return test_cases["test_cases"]
                except:
                    pass
                
                # Try to parse the entire message as JSON
                try:
                    test_cases = json.loads(msg.content)
                    if isinstance(test_cases, list) and len(test_cases) > 0:
                        return test_cases
                    elif isinstance(test_cases, dict) and "test_cases" in test_cases:
                        return test_cases["test_cases"]
                except:
                    pass
        
        return []
    
    def _parse_files_from_response(self, response: str) -> Dict[str, str]:
        """
        Parse the response to extract individual files.
        
        Args:
            response: LLM response containing multiple file contents
            
        Returns:
            Dictionary mapping file names to test script content
        """
        files = {}
        if not response:
            return files
            
        # Try to handle different response formats
        
        # Format 1: Code blocks with language and filename
        # ```python:test_example.py
        # code here
        # ```
        code_blocks = re.findall(r'```(?:python|py):?(\S*)\n([\s\S]*?)\n```', response)
        for filename, content in code_blocks:
            if not filename:
                filename = f'test_script_{len(files) + 1}.py'
            elif not filename.endswith('.py'):
                filename = f'{filename}.py'
            files[filename] = content.strip()
        
        # If we found files in code blocks, return them
        if files:
            logger.info(f"Found {len(files)} files in code blocks")
            return files
            
        # Format 2: Filename followed by code block
        # test_example.py:
        # ```python
        # code here
        # ```
        filename_blocks = re.findall(r'(\S+\.py):\s*\n```(?:python|py)?\n([\s\S]*?)\n```', response)
        for filename, content in filename_blocks:
            files[filename] = content.strip()
            
        if files:
            logger.info(f"Found {len(files)} files in filename + code blocks")
            return files
            
        # Format 3: Just code blocks without filenames
        code_blocks = re.findall(r'```(?:python|py)\n([\s\S]*?)\n```', response)
        if code_blocks:
            for i, content in enumerate(code_blocks, 1):
                files[f'test_script_{i}.py'] = content.strip()
            logger.info(f"Found {len(files)} code blocks without filenames")
            return files
            
        # Format 4: If no code blocks found, try to extract Python code directly
        python_code = re.findall(r'(?:^|\n)((?:from\s+\S+\s+)?import\s+[\w\s,]+\n|def\s+test_\w+\([^)]*\)[\s\S]*?(?=\n\s*\n|\Z))', response)
        if python_code:
            files['test_script.py'] = '\n'.join(code.strip() for code in python_code)
            logger.info("Extracted Python code directly from response")
            return files
            
        # If no code found, try to use the entire response as a test script
        if not files and 'def test_' in response:
            files['test_script.py'] = response.strip()
        return files
    
    def get_name(self) -> str:
        """
        Get the name of the agent.
        
        Returns:
            Agent name as a string
        """
        return "test_script_generator"
    
    def get_description(self) -> str:
        """
        Get a description of what the agent does.
        
        Returns:
            Agent description as a string
        """
        return "Transforms structured test cases into executable Selenium test scripts."