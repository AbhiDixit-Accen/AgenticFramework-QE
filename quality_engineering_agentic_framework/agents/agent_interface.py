"""
Agent Interface Module

This module defines the base interface for all agents in the framework.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union

from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface
from quality_engineering_agentic_framework.web.api.models import ChatMessage


class AgentInterface(ABC):
    """Base interface for all agents."""
    
    def __init__(self, llm: LLMInterface, config: Dict[str, Any]):
        """
        Initialize the agent.
        
        Args:
            llm: LLM interface
            config: Agent configuration
        """
        self.llm = llm
        self.config = config
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """
        Process input data and generate output.
        
        Args:
            input_data: Input data
            
        Returns:
            Output data
        """
        pass
    
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
            return "I don't see any messages from you. How can I help?", None
        
        # Format the conversation for the LLM in a structured way
        formatted_messages = []
        for msg in messages:
            formatted_messages.append(f"{msg.role.upper()}: {msg.content}")
        
        conversation = "\n".join(formatted_messages)
        
        # Create a prompt with guidance
        prompt = f"""You are an AI assistant specialized in software testing and quality engineering.

Previous conversation:
{conversation}

Respond to the user's latest message. Be helpful, concise, and professional.
If they ask you to generate testing artifacts, explain what information you need from them.
"""
        
        # Get response from LLM
        response = await self.llm.generate(prompt)
        
        return response, None
    
    def _is_generation_request(self, message: str) -> bool:
        """
        Check if a message is a request to generate artifacts.
        
        Args:
            message: Message content
            
        Returns:
            True if the message is a generation request, False otherwise
        """
        generation_keywords = [
            "generate", "create", "make", "produce", "build", 
            "test case", "test script", "test data"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in generation_keywords)