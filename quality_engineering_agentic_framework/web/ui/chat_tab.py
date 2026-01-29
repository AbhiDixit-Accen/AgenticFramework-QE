"""
Chat Tab Module for Quality Engineering Agentic Framework

This module provides the chat tab UI for the Streamlit app.
"""

import streamlit as st
import requests
import uuid
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the project root to sys.path to help with imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Try to import the necessary functions, with fallbacks
AGENT_AVAILABLE = False
try:
    from quality_engineering_agentic_framework.agents.requirement_interpreter import (
        generate_test_cases_from_requirements,
        generate_test_cases_for_ui
    )
    AGENT_AVAILABLE = True
except ImportError as e:
    print(f"Primary import failed: {e}")
    # We'll implement our own test case generation as a fallback

# Define a fallback test case generation function that doesn't depend on imports
def fallback_generate_test_cases(requirements_text, llm_config, api_url=None):
    """
    Fallback test case generation function that works without the main module.
    First tries to use the API, then falls back to a simple test case generator.
    
    Args:
        requirements_text (str): The requirements text to generate test cases from
        llm_config (dict): LLM configuration
        api_url (str): API URL for remote generation
        
    Returns:
        list: List of test case dictionaries
    """
    # First try to use the API
    if api_url:
        try:
            # Try to use the test case generation API endpoint
            request_data = {
                "requirements": requirements_text,
                "llm_config": llm_config
            }
            
            response = requests.post(
                f"{api_url}/api/test-case-generation",
                json=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if "test_cases" in response_data and response_data["test_cases"]:
                    print("Successfully generated test cases using API")
                    return response_data
        except Exception as api_error:
            print(f"API fallback failed: {api_error}")
    
    # If we're here, both the import and the API failed
    # Generate a simple test case structure directly
    print("Using simple test case generator")
    
    # Extract key phrases from requirements text
    key_words = requirements_text.lower().split()
    key_phrases = []
    
    for word in key_words:
        if len(word) > 3 and word not in ["test", "case", "generate", "please", "would", "could", "should", "with", "that", "this", "from", "have", "what", "when", "where", "which", "will", "your", "cases"]:
            key_phrases.append(word)
    
    # Create test cases
    test_cases = [
        {
            "title": f"Verify {requirements_text[:50]}{'...' if len(requirements_text) > 50 else ''}",
            "description": requirements_text,
            "preconditions": [
                "System is available and accessible",
                "User has appropriate permissions",
                "Required test data is available"
            ],
            "actions": [
                "1. Initialize the test environment",
                "2. Set up test data",
                "3. Execute the test scenario",
                "4. Verify the results"
            ],
            "expected_results": [
                "Test passes successfully",
                "System behaves as expected",
                "No errors or unexpected behavior is observed"
            ]
        }
    ]
    
    # If we have specific key phrases, add more detailed test cases
    if key_phrases:
        for phrase in key_phrases[:3]:  # Limit to 3 more test cases
            test_cases.append({
                "title": f"Test {phrase.capitalize()} Functionality",
                "description": f"Verify the {phrase} functionality works as expected",
                "preconditions": [
                    "System is available",
                    f"User has access to {phrase} feature"
                ],
                "actions": [
                    f"1. Navigate to {phrase} feature",
                    f"2. Perform actions related to {phrase}",
                    "3. Validate the results"
                ],
                "expected_results": [
                    f"The {phrase} functionality works correctly",
                    "No errors are encountered"
                ]
            })
    
    return test_cases

def render_chat_tab(API_URL: str, llm_provider: str, llm_model: str, llm_api_key: str, 
                   llm_temperature: float, llm_max_tokens: int):
    """
    Render the chat tab UI.
    """
    st.header("Chat with Agents")
    st.write("Have a conversation with the testing agents to get help with your testing needs.")
    
    # Initialize chat session state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = str(uuid.uuid4())
    
    # Prominent Agent and Script configuration
    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        agent_type = st.selectbox(
            "Active Agent",
            options=["Universal QE Assistant", "Test Case Generation Agent", "Test Script Generation Agent", "Test Data Generation Agent"],
            index=0,
        )
    with col_b:
        lang_options = ["Python", "Java", "JavaScript", "TypeScript", "C#"]
        target_lang = st.selectbox("Script Language", options=lang_options, index=0)
    with col_c:
        framework_map = {
            "Python": ["pytest", "unittest", "robot", "playwright"],
            "Java": ["junit", "testng", "cucumber", "playwright", "selenide"],
            "JavaScript": ["jest", "mocha", "cypress", "playwright"],
            "TypeScript": ["jest", "mocha", "cypress", "playwright", "webdriverio"],
            "C#": ["nunit", "xunit", "mstest", "playwright"]
        }
        target_framework = st.selectbox("Script Framework", options=framework_map[target_lang], index=0)

    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.chat_messages = []
        st.rerun()
    
    # Display chat history in a scrollable container
    chat_container = st.container(height=500, border=True)
    with chat_container:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
                # Display artifacts if any
                if "artifacts" in msg and msg["artifacts"]:
                    # Handle Test Cases
                    if msg["artifacts"].get("type") == "test_cases" and "test_cases" in msg["artifacts"]:
                        test_cases = msg["artifacts"]["test_cases"]
                        if msg["artifacts"].get("product_context"):
                            with st.expander("🔍 Synthesized Product Knowledge"):
                                st.markdown(msg["artifacts"]["product_context"])
                                
                        with st.expander("View Test Cases", expanded=False):
                            for i, tc in enumerate(test_cases, 1):
                                with st.expander(f"Test Case {i}: {tc.get('title', 'Untitled')}"):
                                    st.write(f"**Description:** {tc.get('description', 'N/A')}")
                                    if tc.get('preconditions'):
                                        st.write("**Preconditions:**")
                                        for pre in tc['preconditions']: st.write(f"- {pre}")
                                    if tc.get('actions'):
                                        st.write("**Steps:**")
                                        for step in tc['actions']: st.write(f"- {step}")
                                    if tc.get('expected_results'):
                                        st.write("**Expected:**")
                                        for res in tc['expected_results']: st.write(f"- {res}")
                            
                            st.download_button(
                                label="Download JSON",
                                data=json.dumps(test_cases, indent=2),
                                file_name="test_cases.json",
                                mime="application/json",
                                key=f"dl_tc_{uuid.uuid4()}"
                            )
                    
                    # Handle Test Scripts
                    elif msg["artifacts"].get("type") == "test_scripts" and "test_scripts" in msg["artifacts"]:
                        scripts = msg["artifacts"]["test_scripts"]
                        with st.expander("📂 View Generated Scripts", expanded=True):
                            for filename, code in scripts.items():
                                st.markdown(f"**`{filename}`**")
                                st.code(code, language=filename.split('.')[-1])
                            
                            full_code = "\n\n".join([f"# {f}\n{c}" for f, c in scripts.items()])
                            st.download_button(
                                label="Download All Scripts",
                                data=full_code,
                                file_name="automation_scripts.txt",
                                key=f"dl_script_{uuid.uuid4()}"
                            )

    # Chat input
    user_input = st.chat_input("Ask me to generate, refine, or automate tests...")
    
    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with chat_container:
            with st.chat_message("user"):
                st.write(user_input)
        
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    try:
                        agent_type_map = {
                            "Universal QE Assistant": "universal",
                            "Test Case Generation Agent": "test_case",
                            "Test Script Generation Agent": "test_script", 
                            "Test Data Generation Agent": "test_data"
                        }
                        
                        request_data = {
                            "messages": [
                                {"role": m["role"], "content": m["content"]} 
                                for m in st.session_state.chat_messages
                            ],
                            "llm_config": {
                                "provider": llm_provider,
                                "model": llm_model,
                                "api_key": llm_api_key,
                                "temperature": float(llm_temperature),
                                "max_tokens": int(llm_max_tokens),
                            },
                            "agent_type": agent_type_map[agent_type],
                            "session_id": st.session_state.chat_session_id,
                            "test_cases": st.session_state.get("chat_test_cases", []),
                            "agent_config": {
                                "language": target_lang,
                                "framework": target_framework
                            }
                        }
                        
                        response = requests.post(f"{API_URL}/api/chat", json=request_data)
                        
                        if response.status_code == 200:
                            data = response.json()
                            content = data["message"]["content"]
                            st.write(content)
                            
                            msg = {"role": "assistant", "content": content}
                            if "artifacts" in data and data["artifacts"]:
                                msg["artifacts"] = data["artifacts"]
                                # Update chat-specific test cases
                                if data["artifacts"].get("type") == "test_cases":
                                    st.session_state.chat_test_cases = data["artifacts"]["test_cases"]
                            
                            st.session_state.chat_messages.append(msg)
                            st.rerun()
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Connection Error: {str(e)}")
