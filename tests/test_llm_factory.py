"""
Tests for the LLM Factory.
"""

import pytest
from unittest.mock import patch

from quality_engineering_agentic_framework.llm.llm_factory import LLMFactory
from quality_engineering_agentic_framework.llm.openai_llm import OpenAILLM
from quality_engineering_agentic_framework.llm.gemini_llm import GeminiLLM


class TestLLMFactory:
    """Test cases for the LLM Factory."""
    
    @patch('quality_engineering_agentic_framework.llm.openai_llm.OpenAILLM')
    def test_create_llm_returns_openai_instance(self, mock_openai_llm):
        """Test that create_llm returns an OpenAI LLM instance when provider is 'openai'."""
        # Arrange
        config = {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test_key"
        }
        mock_openai_llm.return_value = "openai_instance"
        
        # Act
        result = LLMFactory.create_llm(config)
        
        # Assert
        mock_openai_llm.assert_called_once_with(config)
        assert result == "openai_instance"
    
    @patch('quality_engineering_agentic_framework.llm.gemini_llm.GeminiLLM')
    def test_create_llm_returns_gemini_instance(self, mock_gemini_llm):
        """Test that create_llm returns a Gemini LLM instance when provider is 'gemini'."""
        # Arrange
        config = {
            "provider": "gemini",
            "model": "gemini-pro",
            "api_key": "test_key"
        }
        mock_gemini_llm.return_value = "gemini_instance"
        
        # Act
        result = LLMFactory.create_llm(config)
        
        # Assert
        mock_gemini_llm.assert_called_once_with(config)
        assert result == "gemini_instance"
    
    def test_create_llm_raises_error_for_unsupported_provider(self):
        """Test that create_llm raises an error for unsupported providers."""
        # Arrange
        config = {
            "provider": "unsupported",
            "api_key": "test_key"
        }
        
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            LLMFactory.create_llm(config)
        
        assert "Unsupported LLM provider" in str(excinfo.value)
    
    def test_create_llm_handles_case_insensitive_provider(self):
        """Test that create_llm handles case-insensitive provider names."""
        # Arrange
        config = {
            "provider": "OpEnAi",  # Mixed case
            "model": "gpt-4",
            "api_key": "test_key"
        }
        
        # Act & Assert
        with patch('quality_engineering_agentic_framework.llm.openai_llm.OpenAILLM') as mock_openai_llm:
            mock_openai_llm.return_value = "openai_instance"
            result = LLMFactory.create_llm(config)
            mock_openai_llm.assert_called_once_with(config)
            assert result == "openai_instance"