"""
Chat Bot module for Quality Engineering Agentic Framework

This module provides a Chat Bot UI implementation.
"""

import streamlit as st
import requests
import json
import uuid
from typing import Dict, List, Any, Optional

def render_chat_bot(API_URL: str, llm_provider: str, llm_model: str, llm_api_key: str, 
                  llm_temperature: float, llm_max_tokens: int):
    """
    Render the Chat Bot UI.
    
    Args:
        API_URL: API URL
        llm_provider: LLM provider
        llm_model: LLM model
        llm_api_key: LLM API key
        llm_temperature: LLM temperature
        llm_max_tokens: LLM max tokens
    """
    st.header("Chat Bot")
    st.write("Have a natural conversation with our AI assistant.")
    
    # Initialize chat session state
    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = []
    
    if "chatbot_session_id" not in st.session_state:
        st.session_state.chatbot_session_id = str(uuid.uuid4())
    
    # Chat bot configuration
    with st.expander("Chat Bot Configuration"):
        bot_personality = st.selectbox(
            "Bot Personality",
            options=["Helpful Assistant", "Technical Expert", "Friendly Guide", "Creative Partner"],
            index=0,
        )
        
        chat_context = st.text_area(
            "Initial Context (optional)",
            placeholder="Add any specific context or instructions for the chat bot...",
            height=100
        )
        
        if st.button("Clear Chat History", key="clear_chatbot_history"):
            st.session_state.chatbot_messages = []
            st.rerun()
    
    # Display chat history
    for message in st.session_state.chatbot_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to chat history
        st.session_state.chatbot_messages.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_input)
        
        # Get response from chat bot
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Simple fallback chatbot implementation that works offline
                    def generate_chatbot_response(message, personality):
                        # Base response
                        greeting_phrases = ["Hello", "Hi", "Hey", "Greetings"]
                        goodbye_phrases = ["bye", "goodbye", "see you", "farewell"]
                        thank_phrases = ["thank you", "thanks", "appreciate it", "grateful"]
                        
                        # Simple keyword detection
                        message_lower = message.lower()
                        
                        # Check for greetings
                        for phrase in greeting_phrases:
                            if phrase.lower() in message_lower:
                                return f"Hello there! I'm your {personality} AI assistant. How can I help you today?"
                        
                        # Check for goodbyes
                        for phrase in goodbye_phrases:
                            if phrase in message_lower:
                                return f"Goodbye! It was nice chatting with you. Feel free to come back anytime you need assistance!"
                        
                        # Check for thanks
                        for phrase in thank_phrases:
                            if phrase in message_lower:
                                return "You're welcome! I'm always happy to help. Is there anything else you'd like to discuss?"
                        
                        # Personality-based responses
                        if personality == "Helpful Assistant":
                            return f"I understand you're asking about '{message}'. As your helpful assistant, I'm here to provide clear and useful information. What specific aspects would you like me to elaborate on?"
                        
                        elif personality == "Technical Expert":
                            return f"Regarding '{message}', from a technical perspective, this involves several important considerations. Would you like me to provide a detailed technical analysis?"
                        
                        elif personality == "Friendly Guide":
                            return f"That's an interesting topic! '{message}' is something I'd be happy to explore with you in a friendly conversation. What aspects are you most curious about?"
                        
                        elif personality == "Creative Partner":
                            return f"'{message}' opens up so many creative possibilities! I can help brainstorm ideas, develop concepts, or explore innovative approaches. How would you like to proceed creatively?"
                        
                        else:
                            return f"I've received your message about '{message}'. How would you like me to help you with this?"
                    
                    try:
                        # First try API if available
                        request_data = {
                            "messages": [
                                {
                                    "role": msg["role"],
                                    "content": msg["content"]
                                }
                                for msg in st.session_state.chatbot_messages
                            ],
                            "llm_config": {
                                "provider": llm_provider,
                                "model": llm_model,
                                "api_key": llm_api_key,
                                "temperature": float(llm_temperature),
                                "max_tokens": int(llm_max_tokens),
                            },
                            "context": chat_context,
                            "personality": bot_personality,
                            "session_id": st.session_state.chatbot_session_id
                        }
                        
                        # Try API call with timeout
                        response = requests.post(
                            f"{API_URL}/api/chat", 
                            json=request_data,
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            response_data = response.json()
                            assistant_response = response_data["response"]
                        else:
                            # If API fails, use fallback
                            raise Exception(f"API error: {response.status_code}")
                            
                    except Exception as api_error:
                        # Use local fallback if API is unavailable
                        st.info("Using offline chat mode as API is unavailable.")
                        assistant_response = generate_chatbot_response(user_input, bot_personality)
                    
                    # Display the response
                    st.write(assistant_response)
                    
                    # Add to chat history
                    st.session_state.chatbot_messages.append({
                        "role": "assistant",
                        "content": assistant_response
                    })
                    
                except Exception as e:
                    error_message = f"Error: {str(e)}"
                    st.error(error_message)
                    st.session_state.chatbot_messages.append({
                        "role": "assistant",
                        "content": f"I encountered an error: {error_message}"
                    })
