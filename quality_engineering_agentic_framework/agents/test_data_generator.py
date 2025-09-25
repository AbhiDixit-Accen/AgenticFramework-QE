"""
Test Data Generator Agent
 
This agent generates synthetic test data for test cases or test scripts.
"""
 
import os
import json
import re
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
 
from quality_engineering_agentic_framework.agents.agent_interface import AgentInterface
from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface
from quality_engineering_agentic_framework.utils.logger import get_logger
from quality_engineering_agentic_framework.web.api.models import ChatMessage
 
logger = get_logger(__name__)
 
 
class TestDataGenerator(AgentInterface):
    """
    Agent that generates synthetic test data for test cases or test scripts.
    """
   
    def __init__(self, llm: LLMInterface, config: Dict[str, Any]):
        """
        Initialize the Test Data Generator agent.
       
        Args:
            llm: LLM instance to use for generation
            config: Dictionary containing agent-specific configuration
        """
        super().__init__(llm, config)
        self.output_format = config.get("output_format", "json")
        self.data_variations = config.get("data_variations", 5)
        self.include_edge_cases = config.get("include_edge_cases", True)
       
        # Load prompt template
        prompt_template_path = config.get("prompt_template")
        self.prompt_template = self._load_prompt_template(prompt_template_path)
       
        logger.info(f"Initialized Test Data Generator agent with output format: {self.output_format}")
   
    def _load_prompt_template(self, template_path: Optional[str]) -> str:
        """
        Load the prompt template from a file or use default.
       
        Args:
            template_path: Path to the prompt template file
           
        Returns:
            Prompt template as a string
        """
        default_template = """
        You are a test data generator that creates synthetic test data for software testing.
       
        Given the following test cases or test scripts:
       
        {input_data}
       
        Generate {data_variations} variations of test data that can be used for testing.
        {edge_cases_instruction}
       
        Your output should be in {output_format} format and include all necessary data fields for the test cases.
       
        Be creative but realistic with the test data. Include a mix of valid and invalid data where appropriate.
        """
       
        if template_path and os.path.exists(template_path):
            try:
                with open(template_path, 'r') as file:
                    return file.read()
            except Exception as e:
                logger.warning(f"Failed to load prompt template from {template_path}: {str(e)}")
                logger.warning("Using default prompt template instead")
       
        return default_template
   
    async def process(self, input_data: Union[List[Dict[str, Any]], Dict[str, str]]) -> Dict[str, Any]:
        """
        Process the input data and generate synthetic test data.
       
        Args:
            input_data: Test cases or test scripts
           
        Returns:
            Dictionary containing generated test data
        """
        logger.info("Processing input with Test Data Generator agent")
       
        # Convert input data to a string representation
        input_data_str = self._format_input_data(input_data)
       
        # Prepare edge cases instruction
        edge_cases_instruction = "Include edge cases and boundary values in your test data." if self.include_edge_cases else ""
       
        # Prepare the prompt
        prompt = self.prompt_template.format(
            input_data=input_data_str,
            data_variations=self.data_variations,
            edge_cases_instruction=edge_cases_instruction,
            output_format=self.output_format
        )
       
        # Define the expected JSON schema for the output
        json_schema = {
            "type": "object",
            "properties": {
                "test_data": {
                    "type": "object",
                    "additionalProperties": True
                }
            },
            "required": ["test_data"]
        }
       
        system_message = f"""
        You are a test data generator that creates synthetic test data for software testing.
        You must analyze the test cases or test scripts carefully and create realistic test data.
        Your output must be in valid JSON format according to the provided schema.
        """
       
        try:
            # Generate test data using the LLM
            response = await self.llm.generate_with_json_output(
                prompt=prompt,
                json_schema=json_schema,
                system_message=system_message
            )
           
            test_data = response.get("test_data", {})
            logger.info(f"Generated test data with {len(test_data)} entries")
           
            return test_data
       
        except Exception as e:
            logger.error(f"Error generating test data: {str(e)}")
            raise
   
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
            return "I don't see any messages from you. How can I help with test data generation?", None
       
        # Check if this is a request to generate test data
        if self._is_generation_request(latest_user_message.content):
            # Extract test cases or test scripts from the conversation
            input_data = self._extract_input_data(messages)
           
            if input_data:
                try:
                    # Generate test data
                    test_data = await self.process(input_data)
                   
                    # Create a response that includes the generated test data
                    response = f"I've generated test data based on your input. Here's a summary:\n\n"
                   
                    # Add a summary of the test data
                    for i, (key, value) in enumerate(list(test_data.items())[:3], 1):  # Show first 3 entries
                        response += f"{i}. {key}: {len(value) if isinstance(value, list) else '1'} data entries\n"
                   
                    if len(test_data) > 3:
                        response += f"... and {len(test_data) - 3} more entries.\n"
                   
                    response += "\nYou can view all the test data in the artifacts section."
                   
                    return response, {"test_data": test_data}
                except Exception as e:
                    logger.error(f"Error generating test data in chat: {str(e)}")
                    return f"I encountered an error while generating test data: {str(e)}", None
            else:
                return "I'd be happy to generate test data for you. Could you please provide the test cases or test scripts you'd like me to work with?", None
       
        # Format the conversation for the LLM in a structured way
        formatted_messages = []
        for msg in messages[-10:]:  # Limit to last 10 messages for context
            formatted_messages.append(f"{msg.role.upper()}: {msg.content}")
       
        conversation = "\n".join(formatted_messages)
       
        # Create a prompt with guidance specific to test data generation
        prompt = f"""You are a Test Data Generator Agent that helps create synthetic test data for testing.
 
Previous conversation:
{conversation}
 
Respond to the user's latest message. Be helpful, concise, and professional.
If they ask about test data generation, explain your capabilities and what information you need.
If they ask about data generation strategies, provide accurate information.
If they ask about other testing topics, provide helpful guidance.
"""
       
        # Get response from LLM
        response = await self.llm.generate(prompt)
       
        return response, None
   
    def _extract_input_data(self, messages: List[ChatMessage]) -> Union[List[Dict[str, Any]], Dict[str, str], None]:
        """
        Extract test cases or test scripts from the conversation.
       
        Args:
            messages: List of chat messages
           
        Returns:
            Test cases, test scripts, or None if not found
        """
        # Look for test cases or test scripts in JSON format in the messages
        for msg in reversed(messages):
            if msg.role == "user":
                # Try to find JSON in the message
                try:
                    # Look for content between triple backticks
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', msg.content)
                    if json_match:
                        json_content = json_match.group(1)
                        data = json.loads(json_content)
                        if isinstance(data, list) and len(data) > 0:
                            return data  # Test cases
                        elif isinstance(data, dict):
                            if "test_cases" in data:
                                return data["test_cases"]  # Test cases in a wrapper
                            else:
                                return data  # Could be test scripts or other data
                except:
                    pass
               
                # Try to parse the entire message as JSON
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, list) and len(data) > 0:
                        return data  # Test cases
                    elif isinstance(data, dict):
                        if "test_cases" in data:
                            return data["test_cases"]  # Test cases in a wrapper
                        else:
                            return data  # Could be test scripts or other data
                except:
                    pass
       
        return None
   
    def _format_input_data(self, input_data: Union[List[Dict[str, Any]], Dict[str, str]]) -> str:
        """
        Format input data as a string for the prompt.
       
        Args:
            input_data: Test cases or test scripts
           
        Returns:
            Formatted string representation
        """
        if isinstance(input_data, list):
            # Format test cases
            result = "Test Cases:\n\n"
            for i, test_case in enumerate(input_data):
                # Handle both dictionary-like objects and TestCase objects
                if hasattr(test_case, 'get'):
                    title = test_case.get('title', 'Untitled')
                else:
                    # For TestCase objects or other objects without get method
                    title = getattr(test_case, 'title', 'Untitled')
               
                result += f"Test Case {i+1}: {title}\n"
               
                # Handle description
                if hasattr(test_case, 'get'):
                    description = test_case.get('description')
                else:
                    description = getattr(test_case, 'description', None)
               
                if description:
                    result += f"Description: {description}\n"
               
                # Handle preconditions
                preconditions = []
                if hasattr(test_case, 'get'):
                    preconditions = test_case.get('preconditions', [])
                else:
                    preconditions = getattr(test_case, 'preconditions', [])
               
                if preconditions:
                    result += "Preconditions:\n"
                    for pre in preconditions:
                        result += f"- {pre}\n"
               
                # Handle actions
                actions = []
                if hasattr(test_case, 'get'):
                    actions = test_case.get('actions', [])
                else:
                    actions = getattr(test_case, 'actions', [])
               
                if actions:
                    result += "Actions:\n"
                    for action in actions:
                        result += f"- {action}\n"
               
                # Handle expected results
                expected_results = []
                if hasattr(test_case, 'get'):
                    expected_results = test_case.get('expected_results', [])
                else:
                    expected_results = getattr(test_case, 'expected_results', [])
               
                if expected_results:
                    result += "Expected Results:\n"
                    for er in expected_results:
                        result += f"- {er}\n"
               
                result += "\n"
           
            return result
       
        elif isinstance(input_data, dict):
            # Format test scripts
            result = "Test Scripts:\n\n"
            for filename, content in input_data.items():
                result += f"File: {filename}\n"
                # Include a snippet of the content
                content_snippet = content[:500] + "..." if len(content) > 500 else content
                result += f"Content:\n{content_snippet}\n\n"
           
            return result
       
        else:
            return str(input_data)
   
    def export_data(self, test_data: Dict[str, Any], output_dir: str) -> List[str]:
        """
        Export test data to files.
       
        Args:
            test_data: Test data to export
            output_dir: Output directory
           
        Returns:
            List of created file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        created_files = []
       
        if self.output_format == "json":
            # Export as JSON
            json_path = os.path.join(output_dir, "test_data.json")
            with open(json_path, 'w') as f:
                json.dump(test_data, f, indent=2)
           
            created_files.append(json_path)
           
            # Export individual JSON files for each test case/group
            for key, value in test_data.items():
                key_path = os.path.join(output_dir, f"{key}.json")
                with open(key_path, 'w') as f:
                    json.dump(value, f, indent=2)
               
                created_files.append(key_path)
       
        elif self.output_format == "csv":
            # Export as CSV
            for key, value in test_data.items():
                if isinstance(value, list) and len(value) > 0:
                    # Convert to DataFrame
                    df = pd.DataFrame(value)
                   
                    # Save as CSV
                    csv_path = os.path.join(output_dir, f"{key}.csv")
                    df.to_csv(csv_path, index=False)
                   
                    created_files.append(csv_path)
       
        return created_files
   
    def get_name(self) -> str:
        """
        Get the name of the agent.
       
        Returns:
            Agent name as a string
        """
        return "test_data_generator"
   
    def get_description(self) -> str:
        """
        Get a description of what the agent does.
       
        Returns:
            Agent description as a string
        """
        return "Generates synthetic test data for test cases or test scripts."