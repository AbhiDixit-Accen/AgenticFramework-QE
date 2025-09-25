"""
Chat UI Module for Quality Engineering Agentic Framework

This module provides a simpler chat UI implementation.
"""

import streamlit as st
import requests
import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

def render_chat_ui(API_URL: str, llm_provider: str, llm_model: str, llm_api_key: str, 
                   llm_temperature: float, llm_max_tokens: int):
    """
    Render the chat UI.
    
    Args:
        API_URL: API URL
        llm_provider: LLM provider
        llm_model: LLM model
        llm_api_key: LLM API key
        llm_temperature: LLM temperature
        llm_max_tokens: LLM max tokens
    """
    st.header("Chat with Agents")
    st.write("Have a conversation with the testing agents to get help with your testing needs.")
    
    # Initialize chat session state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = str(uuid.uuid4())
    
    # Agent selection
    agent_type = st.selectbox(
        "Select Agent to Chat With",
        options=["Test Case Generation Agent", "Test Script Generation Agent", "Test Data Generation Agent"],
        index=0,
    )
    
    if st.button("Clear Chat History"):
        st.session_state.chat_messages = []
        st.rerun()
    
    # Map selection to agent type
    agent_type_map = {
        "Test Case Generation Agent": "test_case",
        "Test Script Generation Agent": "test_script",
        "Test Data Generation Agent": "test_data"
    }
    
    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to chat history
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_input)
        
        # Get response from agent
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Prepare request with proper structure
                    request_data = {
                        "messages": [
                            {
                                "role": msg["role"],
                                "content": msg["content"]
                            }
                            for msg in st.session_state.chat_messages
                        ],
                        "llm_config": {
                            "provider": llm_provider,
                            "model": llm_model,
                            "api_key": llm_api_key,
                            "temperature": float(llm_temperature),
                            "max_tokens": int(llm_max_tokens)
                        },
                        "agent_type": agent_type_map[agent_type],
                        "session_id": st.session_state.chat_session_id
                    }
                    
                    # Call API
                    response = requests.post(
                        f"{API_URL}/api/chat",
                        json=request_data,
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        assistant_response = response_data["message"]["content"]
                        st.write(assistant_response)
                        
                        # Add assistant message to chat history
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": assistant_response
                        })
                        
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")