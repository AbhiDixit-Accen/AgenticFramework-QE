"""
OpenAI LLM Implementation

This module implements the LLMInterface for OpenAI's models.
"""

import json
import logging
from typing import Dict, List, Optional, Any

import openai
from openai import AsyncOpenAI

from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface
from quality_engineering_agentic_framework.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAILLM(LLMInterface):
    """Implementation of LLMInterface for OpenAI."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the OpenAI LLM with configuration.
        
        Args:
            config: Dictionary containing configuration parameters
        """
        self.config = config
        self.model = config.get("model", "gpt-4")
        self.temperature = config.get("temperature", 0.2)
        self.max_tokens = config.get("max_tokens", 2000)
        
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info(f"Initialized OpenAI LLM with model: {self.model}")
    
    async def generate(self, 
                      prompt: str, 
                      system_message: Optional[str] = None,
                      temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None) -> str:
        """
        Generate text based on the prompt using OpenAI.
        
        Args:
            prompt: The prompt to send to the LLM
            system_message: Optional system message to guide the LLM
            temperature: Optional temperature parameter to override config
            max_tokens: Optional max tokens parameter to override config
            
        Returns:
            Generated text response
        """
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Error generating text with OpenAI: {str(e)}")
            raise
    
    async def generate_with_json_output(self, 
                                       prompt: str, 
                                       json_schema: Dict[str, Any],
                                       system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a response in JSON format according to the provided schema using OpenAI.
        
        Args:
            prompt: The prompt to send to the LLM
            json_schema: JSON schema that defines the expected output structure
            system_message: Optional system message to guide the LLM
            
        Returns:
            Generated response as a dictionary conforming to the schema
        """
        if not system_message:
            system_message = "You are a helpful assistant that responds in JSON format."
        
        system_message += f"\nYou must respond with a JSON object that conforms to this schema: {json.dumps(json_schema)}"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        
        except Exception as e:
            logger.error(f"Error generating JSON with OpenAI: {str(e)}")
            raise
    
    def get_provider_name(self) -> str:
        """
        Get the name of the LLM provider.
        
        Returns:
            Provider name as a string
        """
        return "openai"