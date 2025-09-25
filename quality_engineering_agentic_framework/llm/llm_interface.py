"""
LLM Interface Module

This module defines the abstract interface for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class LLMInterface(ABC):
    """Abstract interface for LLM providers."""
    
    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LLM with configuration.
        
        Args:
            config: Dictionary containing configuration parameters
        """
        pass
    
    @abstractmethod
    async def generate(self, 
                      prompt: str, 
                      system_message: Optional[str] = None,
                      temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None) -> str:
        """
        Generate text based on the prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            system_message: Optional system message to guide the LLM
            temperature: Optional temperature parameter to override config
            max_tokens: Optional max tokens parameter to override config
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    async def generate_with_json_output(self, 
                                       prompt: str, 
                                       json_schema: Dict[str, Any],
                                       system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a response in JSON format according to the provided schema.
        
        Args:
            prompt: The prompt to send to the LLM
            json_schema: JSON schema that defines the expected output structure
            system_message: Optional system message to guide the LLM
            
        Returns:
            Generated response as a dictionary conforming to the schema
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the LLM provider.
        
        Returns:
            Provider name as a string
        """
        pass