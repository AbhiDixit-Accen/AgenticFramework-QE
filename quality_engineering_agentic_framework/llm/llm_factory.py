"""
LLM Factory Module

This module provides a factory for creating LLM instances based on configuration.
"""

from typing import Dict, Any

from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface
from quality_engineering_agentic_framework.llm.openai_llm import OpenAILLM
from quality_engineering_agentic_framework.llm.gemini_llm import GeminiLLM
from quality_engineering_agentic_framework.utils.logger import get_logger

logger = get_logger(__name__)


class LLMFactory:
    """Factory for creating LLM instances."""
    
    @staticmethod
    def create_llm(config: Dict[str, Any]) -> LLMInterface:
        """
        Create an LLM instance based on the provided configuration.
        
        Args:
            config: Dictionary containing LLM configuration
            
        Returns:
            An instance of a class implementing LLMInterface
            
        Raises:
            ValueError: If the provider is not supported
        """
        provider = config.get("provider", "").lower()
        
        if provider == "openai":
            return OpenAILLM(config)
        elif provider == "gemini":
            return GeminiLLM(config)
        else:
            supported_providers = ["openai", "gemini"]
            raise ValueError(f"Unsupported LLM provider: {provider}. Supported providers: {supported_providers}")