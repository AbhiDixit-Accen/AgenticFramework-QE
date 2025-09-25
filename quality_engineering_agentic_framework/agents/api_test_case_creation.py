"""
API Test Case Creation Agent

This agent generates comprehensive API test cases given API details, similar to Postman's Postbot.
"""

import os
import json
from typing import Dict, Any, List, Optional

from quality_engineering_agentic_framework.agents.agent_interface import AgentInterface
from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface
from quality_engineering_agentic_framework.utils.logger import get_logger

logger = get_logger(__name__)

class APITestCaseCreationAgent(AgentInterface):
    """
    Agent that generates API test cases from API details (URL, endpoints, etc).
    """
    def __init__(self, llm: LLMInterface, config: Dict[str, Any]):
        super().__init__(llm, config)
        self.prompt_template = self._default_prompt_template()

    def _default_prompt_template(self) -> str:
        """
        Returns the default prompt template for API test case generation.
        """
        return (

    "You are an expert Java API test automation engineer.\n"
    "Generate complete executable Java test code using RestAssured and TestNG frameworks.\n"
    "\n"
    "API Information:\n"
    "Base URL: {base_url}\n"
    "Endpoint: {endpoint}\n"
    "Method: {method}\n"
    "Headers: {headers}\n"
    "Query Parameters: {params}\n"
    "Request Body: {body}\n"
    "Authentication: {auth}\n"
    "\n"
    "Requirements:\n"
    "- Generate 5-6 complete test methods\n"
    "- Include positive and negative test scenarios\n"
    "- Test authentication failures\n"
    "- Test missing parameters\n"
    "- Test invalid data\n"
    "- Use proper RestAssured syntax\n"
    "- Include TestNG annotations\n"
    "- Add meaningful assertions\n"
    "\n"
    "Output Instructions:\n"
    "Generate ONLY executable Java code with proper imports.\n"
    "Create a complete test class with setup method and multiple test methods.\n"
    "Use actual values from the API specification above.\n"
    "Include proper status code and response validations.\n"
    "Make each test method complete and runnable.\n"
    "\n"
    "Return only the Java code without explanations or markdown formatting.\n"
)
        
    async def process(self, api_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate API test cases from API details.
        Args:
            api_details: Dict with keys: base_url, endpoint, method, headers, params, body, auth
        Returns:
            List of structured API test cases
        """
        prompt = self.prompt_template.format(
            base_url=api_details.get("base_url", ""),
            endpoint=api_details.get("endpoint", ""),
            method=api_details.get("method", "GET"),
            headers=json.dumps(api_details.get("headers", {})),
            params=json.dumps(api_details.get("params", {})),
            body=json.dumps(api_details.get("body", {})),
            auth=json.dumps(api_details.get("auth", {})),
        )
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
                            "method": {"type": "string"},
                            "endpoint": {"type": "string"},
                            "headers": {"type": "object"},
                            "params": {"type": "object"},
                            "body": {"type": ["object", "string", "null"]},
                            "expected_status": {"type": "integer"},
                            "expected_response": {"type": ["object", "string", "null"]},
                            "notes": {"type": "string"}
                        },
                        "required": ["title", "description", "method", "endpoint", "expected_status", "expected_response"]
                    }
                }
            },
            "required": ["test_cases"]
        }
        system_message = (
            "You are an expert API test case generator. Generate as many unique, non-redundant API test cases as possible, "
            "covering all combinations, edge cases, security, authentication, and error scenarios. "
            "Return your output as valid JSON according to the provided schema."
        )
        try:
            response = await self.llm.generate_with_json_output(
                prompt=prompt,
                json_schema=json_schema,
                system_message=system_message
            )
            # Defensive: handle both dict and raw string
            if isinstance(response, dict):
                test_cases = response.get("test_cases", [])
                logger.info(f"Generated {len(test_cases)} API test cases")
                return test_cases
            else:
                logger.error(f"LLM did not return JSON. Raw output: {response}")
                raise ValueError("LLM did not return valid JSON output. Please check your LLM prompt and schema.")
        except Exception as e:
            logger.error(f"Error generating API test cases: {str(e)}")
            raise

# Example usage (to be called by UI or API layer):
# agent = APITestCaseCreationAgent(llm, {})
# api_details = {"base_url": "https://api.example.com", "endpoint": "/users", "method": "POST", ...}
# test_cases = await agent.process(api_details)
