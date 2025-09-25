"""
Google Gemini LLM Implementation

This module implements the LLMInterface for Google's Gemini models.
"""

import json
import logging
from typing import Dict, List, Optional, Any

import google.generativeai as genai

from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface
from quality_engineering_agentic_framework.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiLLM(LLMInterface):
    """Implementation of LLMInterface for Google Gemini."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Gemini LLM with configuration.
        
        Args:
            config: Dictionary containing configuration parameters
        """
        self.config = config
        self.model = config.get("model", "gemini-pro")
        self.temperature = config.get("temperature", 0.2)
        self.max_tokens = config.get("max_tokens", 2000)
        
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("Google API key is required")
        
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(self.model)
        logger.info(f"Initialized Google Gemini LLM with model: {self.model}")
    
    async def generate(self, 
                      prompt: str, 
                      system_message: Optional[str] = None,
                      temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None) -> str:
        """
        Generate text based on the prompt using Gemini.
        
        Args:
            prompt: The prompt to send to the LLM
            system_message: Optional system message to guide the LLM
            temperature: Optional temperature parameter to override config
            max_tokens: Optional max tokens parameter to override config
            
        Returns:
            Generated text response
        """
        generation_config = {
            "temperature": temperature if temperature is not None else self.temperature,
            "max_output_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        
        full_prompt = prompt
        if system_message:
            full_prompt = f"{system_message}\n\n{prompt}"
        
        try:
            response = await self.model_instance.generate_content_async(
                full_prompt,
                generation_config=generation_config
            )
            
            return response.text
        
        except Exception as e:
            logger.error(f"Error generating text with Gemini: {str(e)}")
            raise
    
    async def generate_with_json_output(self, 
                                       prompt: str, 
                                       json_schema: Dict[str, Any],
                                       system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a response in JSON format according to the provided schema using Gemini.
        
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
            response = await self.model_instance.generate_content_async(
                [system_message, prompt],
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens,
                }
            )
            
            # Extract JSON from the response
            content = response.text
            # Find JSON content (assuming it's properly formatted)
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If the response isn't valid JSON, try to extract JSON part
                import re
                json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                else:
                    raise ValueError("Could not extract valid JSON from Gemini response")
        
        except Exception as e:
            logger.error(f"Error generating JSON with Gemini: {str(e)}")
            raise
    
    def get_provider_name(self) -> str:
        """
        Get the name of the LLM provider.
        
        Returns:
            Provider name as a string
        """
        return "gemini"