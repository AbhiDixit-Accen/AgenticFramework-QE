"""
Agent Chat Module for Quality Engineering Agentic Framework

This module provides a clean, reliable implementation of the Agent Chat functionality.
"""

import streamlit as st
import requests
import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

def render_agent_chat(API_URL: str, llm_provider: str, llm_model: str, llm_api_key: str, 
                     llm_temperature: float, llm_max_tokens: int):
    """
    Render the Agent Chat UI.
    
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
    col1, col2 = st.columns([2, 1])
    
    with col1:
        agent_type = st.selectbox(
            "Select Agent to Chat With",
            options=["Test Case Generation Agent", "Test Script Generation Agent", "Test Data Generation Agent"],
            index=0,
        )
    
    with col2:
        if st.button("Clear Chat History"):
            st.session_state.chat_messages = []
            st.rerun()
    
    # Display chat history
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            # Display artifacts if present
            if "artifacts" in message and message["artifacts"] and message["artifacts"].get("type") == "test_cases":
                test_cases = message["artifacts"]["test_cases"]
                with st.expander("View Test Cases"):
                    for i, tc in enumerate(test_cases, 1):
                        with st.expander(f"Test Case {i}: {tc.get('title', 'Untitled')}"):
                            if tc.get('description'):
                                st.write(f"**Description:** {tc['description']}")
                            
                            if tc.get('preconditions'):
                                st.write("**Preconditions:**")
                                for precond in tc['preconditions']:
                                    st.write(f"• {precond}")
                            
                            if tc.get('actions'):
                                st.write("**Actions:**")
                                for action in tc['actions']:
                                    st.write(f"• {action}")
                            
                            if tc.get('expected_results'):
                                st.write("**Expected Results:**")
                                for result in tc['expected_results']:
                                    st.write(f"• {result}")
                    
                    # Download button
                    json_str = json.dumps(test_cases, indent=2)
                    st.download_button(
                        label="Download Test Cases (JSON)",
                        data=json_str,
                        file_name="test_cases.json",
                        mime="application/json",
                    )
    
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
                    # Special handling for Test Case Generation Agent
                    if agent_type == "Test Case Generation Agent":
                        # Simple test case generator that doesn't rely on imports
                        def generate_test_cases(requirements):
                            # Extract keywords
                            words = requirements.lower().split()
                            keywords = []
                            for word in words:
                                if len(word) > 3 and word not in ["test", "case", "generate", "create", "please", "would", "could", "should"]:
                                    keywords.append(word)
                            
                            # Create base test case
                            test_cases = [
                                {
                                    "title": f"Test {requirements[:40]}{'...' if len(requirements) > 40 else ''}",
                                    "description": requirements,
                                    "preconditions": [
                                        "System is available and accessible",
                                        "User has necessary permissions",
                                        "Test data is prepared"
                                    ],
                                    "actions": [
                                        "1. Set up the test environment",
                                        "2. Prepare test data",
                                        "3. Execute the test",
                                        "4. Verify results"
                                    ],
                                    "expected_results": [
                                        "The system behaves as expected",
                                        "All requirements are satisfied",
                                        "No errors are encountered"
                                    ]
                                }
                            ]
                            
                            # Add keyword-specific test cases
                            for keyword in keywords[:3]:  # Limit to 3 additional test cases
                                test_cases.append({
                                    "title": f"Test {keyword.capitalize()} Functionality",
                                    "description": f"Verify {keyword} functionality works correctly",
                                    "preconditions": [
                                        "System is available",
                                        f"User has access to {keyword} functionality"
                                    ],
                                    "actions": [
                                        f"1. Navigate to {keyword} feature",
                                        f"2. Perform actions related to {keyword}",
                                        "3. Validate the results"
                                    ],
                                    "expected_results": [
                                        f"The {keyword} functionality works correctly",
                                        "No errors are encountered"
                                    ]
                                })
                            
                            return test_cases
                        
                        # Generate test cases
                        test_cases = generate_test_cases(user_input)
                        
                        # Create response
                        assistant_response = f"I've generated {len(test_cases)} test cases based on your requirements. Here's a summary:\n\n"
                        
                        # Add summary
                        for i, tc in enumerate(test_cases[:3], 1):
                            assistant_response += f"{i}. {tc['title']}\n"
                        
                        if len(test_cases) > 3:
                            assistant_response += f"... and {len(test_cases) - 3} more test cases.\n"
                        
                        # Display response
                        st.write(assistant_response)
                        
                        # Display test cases
                        with st.expander("View Generated Test Cases"):
                            for i, tc in enumerate(test_cases, 1):
                                with st.expander(f"Test Case {i}: {tc.get('title', 'Untitled')}"):
                                    if tc.get('description'):
                                        st.write(f"**Description:** {tc['description']}")
                                    
                                    if tc.get('preconditions'):
                                        st.write("**Preconditions:**")
                                        for precond in tc['preconditions']:
                                            st.write(f"• {precond}")
                                    
                                    if tc.get('actions'):
                                        st.write("**Actions:**")
                                        for action in tc['actions']:
                                            st.write(f"• {action}")
                                    
                                    if tc.get('expected_results'):
                                        st.write("**Expected Results:**")
                                        for result in tc['expected_results']:
                                            st.write(f"• {result}")
                            
                            # Download button
                            json_str = json.dumps(test_cases, indent=2)
                            st.download_button(
                                label="Download Test Cases (JSON)",
                                data=json_str,
                                file_name="test_cases.json",
                                mime="application/json",
                            )
                        
                        # Add to chat history
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": assistant_response,
                            "artifacts": {"type": "test_cases", "test_cases": test_cases}
                        })
                    
                    # For other agents, use the API
                    else:
                        # Map agent types to API values
                        agent_type_map = {
                            "Test Case Generation Agent": "test_case",
                            "Test Script Generation Agent": "test_script",
                            "Test Data Generation Agent": "test_data"
                        }
                        
                        # Prepare request
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
                                "max_tokens": int(llm_max_tokens),
                            },
                            "agent_type": agent_type_map[agent_type],
                            "session_id": st.session_state.chat_session_id
                        }
                        
                        # Call API
                        response = requests.post(f"{API_URL}/api/chat", json=request_data)
                        
                        if response.status_code == 200:
                            response_data = response.json()
                            assistant_response = response_data["message"]["content"]
                            st.write(assistant_response)
                            
                            # Create message to add to chat history
                            assistant_message = {
                                "role": "assistant",
                                "content": assistant_response
                            }
                            
                            # Add artifacts if present
                            if "artifacts" in response_data and response_data["artifacts"]:
                                assistant_message["artifacts"] = response_data["artifacts"]
                            
                            # Add to chat history
                            st.session_state.chat_messages.append(assistant_message)
                        else:
                            error_message = f"Error: {response.status_code} - {response.text}"
                            st.error(error_message)
                            st.session_state.chat_messages.append({
                                "role": "assistant",
                                "content": f"I encountered an error: {error_message}"
                            })
                
                except Exception as e:
                    error_message = f"Error: {str(e)}"
                    st.error(error_message)
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": f"I encountered an error: {error_message}"
                    })
