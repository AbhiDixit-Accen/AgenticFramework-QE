"""
Tests for the Test Case Generation agent.
"""

import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from quality_engineering_agentic_framework.agents.requirement_interpreter import TestCaseGenerationAgent
from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface


class TestTestCaseGenerationAgent:
    """Test cases for the Test Case Generation agent."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        mock = MagicMock(spec=LLMInterface)
        mock.generate_with_json_output = AsyncMock()
        mock.get_provider_name.return_value = "mock_provider"
        return mock
    
    @pytest.fixture
    def agent_config(self):
        """Create a test configuration for the agent."""
        return {
            "output_format": "gherkin",
            "prompt_template": None  # Use default template
        }
    
    @pytest.fixture
    def sample_requirement(self):
        """Sample requirement for testing."""
        return """
        Feature: User Login
        
        As a user
        I want to be able to log in to the system
        So that I can access my account
        
        Requirements:
        1. Users should be able to log in with email and password
        2. System should validate credentials
        3. Users should be redirected to dashboard after successful login
        """
    
    @pytest.fixture
    def sample_test_cases(self):
        """Sample test cases output."""
        return {
            "test_cases": [
                {
                    "title": "Successful login with valid credentials",
                    "description": "Verify that users can log in with valid credentials",
                    "preconditions": ["User has a valid account", "User is on the login page"],
                    "actions": ["Enter valid email", "Enter valid password", "Click login button"],
                    "expected_results": ["User is redirected to dashboard", "Success message is displayed"],
                    "test_data": {"email": "user@example.com", "password": "validPassword123"}
                },
                {
                    "title": "Failed login with invalid password",
                    "description": "Verify that login fails with invalid password",
                    "preconditions": ["User has a valid account", "User is on the login page"],
                    "actions": ["Enter valid email", "Enter invalid password", "Click login button"],
                    "expected_results": ["User remains on login page", "Error message is displayed"],
                    "test_data": {"email": "user@example.com", "password": "invalidPassword"}
                }
            ]
        }
    
    async def test_process_returns_test_cases(self, mock_llm, agent_config, sample_requirement, sample_test_cases):
        """Test that process method returns test cases."""
        # Arrange
        mock_llm.generate_with_json_output.return_value = sample_test_cases
        agent = TestCaseGenerationAgent(mock_llm, agent_config)
        
        # Act
        result = await agent.process(sample_requirement)
        
        # Assert
        assert len(result) == 2
        assert result[0]["title"] == "Successful login with valid credentials"
        assert result[1]["title"] == "Failed login with invalid password"
        mock_llm.generate_with_json_output.assert_called_once()
    
    def test_get_name_returns_correct_value(self, mock_llm, agent_config):
        """Test that get_name returns the correct value."""
        # Arrange
        agent = TestCaseGenerationAgent(mock_llm, agent_config)
        
        # Act
        result = agent.get_name()
        
        # Assert
        assert result == "test_case_generation"
    
    def test_get_description_returns_non_empty_string(self, mock_llm, agent_config):
        """Test that get_description returns a non-empty string."""
        # Arrange
        agent = TestCaseGenerationAgent(mock_llm, agent_config)
        
        # Act
        result = agent.get_description()
        
        # Assert
        assert isinstance(result, str)
        assert len(result) > 0