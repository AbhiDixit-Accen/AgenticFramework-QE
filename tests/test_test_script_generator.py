"""
Tests for the Test Script Generator agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from quality_engineering_agentic_framework.agents.test_script_generator import TestScriptGenerator
from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface


class TestScriptGeneratorUnit:
    """Test cases for the Test Script Generator agent."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        mock = MagicMock(spec=LLMInterface)
        mock.generate = AsyncMock(return_value="```python:test_file.py\ndef test_dummy(): pass\n```")
        return mock

    @pytest.fixture
    def agent_config(self):
        """Create a test configuration for the agent."""
        return {
            "language": "python",
            "framework": "pytest",
            "browser": "chrome"
        }

    @pytest.mark.asyncio
    async def test_process_handles_string_and_dict_actions(self, mock_llm, agent_config):
        """Test that process method handles both string and dictionary actions."""
        # Arrange
        agent = TestScriptGenerator(mock_llm, agent_config)
        
        test_cases = [
            {
                "title": "Mixed actions test",
                "description": "A test case with both string and dict actions",
                "preconditions": ["User is logged in"],
                "actions": [
                    "Navigate to home page",  # String action
                    {"action": "Click button", "locator": {"id": "submit-btn"}},  # Dict action
                    {"action": "Enter text", "value": "test data"}  # Dict action without locator
                ],
                "expected_results": ["Success"]
            }
        ]
        
        # Act
        result = await agent.process(test_cases)
        
        # Assert
        assert "test_file.py" in result
        mock_llm.generate.assert_called_once()
        
        # Verify the prompt content contains the processed actions
        prompt = mock_llm.generate.call_args[1]["prompt"]
        assert "Navigate to home page" in prompt
        assert "Click button" in prompt
        assert "id: submit-btn" in prompt
        assert "Enter text" in prompt
        assert "Value: test data" in prompt

    @pytest.mark.asyncio
    async def test_process_handles_locator_as_string_in_dict(self, mock_llm, agent_config):
        """Test that process method handles locator field when it is a string."""
        # Arrange
        agent = TestScriptGenerator(mock_llm, agent_config)
        
        test_cases = [
            {
                "title": "String locator test",
                "actions": [
                    {"action": "Click", "locator": "#some-id"}
                ]
            }
        ]
        
        # Act
        await agent.process(test_cases)
        
        # Assert
        prompt = mock_llm.generate.call_args[1]["prompt"]
        assert "Locator: #some-id" in prompt
