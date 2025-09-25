"""
Simplified Streamlit UI for Quality Engineering Agentic Framework

This module provides a simplified Streamlit-based UI for the framework.
"""

import os
import json
import streamlit as st
import requests
from typing import Dict, List, Any, Optional
import uuid

# Set page configuration
st.set_page_config(
    page_title="Quality Engineering Agentic Framework",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define API URL
API_URL = os.environ.get("API_URL", "http://localhost:8080")

# Initialize session state
if 'test_cases' not in st.session_state:
    st.session_state.test_cases = []

if 'test_scripts' not in st.session_state:
    st.session_state.test_scripts = {}

if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []

if 'chat_session_id' not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

st.title("Quality Engineering Agentic Framework")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # LLM Configuration
    st.subheader("LLM Configuration")
    llm_provider = st.selectbox(
        "LLM Provider",
        options=["openai", "gemini"],
        index=0,
    )
    
    if llm_provider == "openai":
        llm_model = st.selectbox(
            "Model",
            options=["gpt-4", "gpt-3.5-turbo"],
            index=0,
        )
    else:
        llm_model = st.selectbox(
            "Model",
            options=["gemini-pro", "gemini-ultra"],
            index=0,
        )
    
    llm_api_key = st.text_input(
        "API Key",
        type="password",
        help="Enter your API key for the selected provider",
    )
    
    llm_temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        step=0.1,
        help="Higher values make output more random, lower values more deterministic",
    )
    
    llm_max_tokens = st.number_input(
        "Max Tokens",
        min_value=100,
        max_value=8000,
        value=2000,
        step=100,
        help="Maximum number of tokens to generate",
    )
    
    # Save API key to session state
    if llm_api_key:
        st.session_state[f"{llm_provider}_api_key"] = llm_api_key
    
    # Load API key from session state if available
    if f"{llm_provider}_api_key" in st.session_state:
        llm_api_key = st.session_state[f"{llm_provider}_api_key"]

# Main content - tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "Test Case Generation", 
    "Test Script Generation", 
    "Test Data Generation",
    "Agent Chat"
])

# Test Case Generation Tab
with tab1:
    st.header("Test Case Generation")
    st.write("Convert requirements into structured test cases")
    
    # Input method selection
    input_method = st.radio(
        "Input Method",
        options=["Text", "File Upload"],
        horizontal=True,
    )
    
    requirements_text = ""
    
    if input_method == "Text":
        requirements_text = st.text_area(
            "Requirements",
            height=200,
            placeholder="Enter your requirements here...",
        )
    else:
        uploaded_file = st.file_uploader(
            "Upload Requirements File",
            type=["txt", "md"],
        )
        
        if uploaded_file is not None:
            requirements_text = uploaded_file.getvalue().decode()
            st.text_area(
                "File Contents",
                value=requirements_text,
                height=200,
            )
    
    # Generate button
    if st.button("Generate Test Cases", key="generate_test_cases"):
        if not requirements_text:
            st.error("Please enter requirements or upload a file")
        elif not llm_api_key:
            st.error("Please enter an API key")
        else:
            with st.spinner("Generating test cases..."):
                try:
                    # Create a simple request
                    request_data = {
                        "requirements": requirements_text,
                        "llm_config": {
                            "provider": llm_provider,
                            "model": llm_model,
                            "api_key": llm_api_key,
                            "temperature": 0.2,
                            "max_tokens": 2000
                        },
                        "agent_config": {
                            "output_format": "gherkin"
                        }
                    }
                    
                    # Call API
                    response = requests.post(
                        f"{API_URL}/api/test-case-generation",
                        json=request_data
                    )
                    
                    if response.status_code == 200:
                        test_cases = response.json()["test_cases"]
                        
                        # Store in session state
                        st.session_state.test_cases = test_cases
                        
                        # Display test cases
                        st.success(f"Generated {len(test_cases)} test cases")
                        
                        # Format as JSON for display
                        json_str = json.dumps(test_cases, indent=2)
                        st.code(json_str, language="json")
                        
                        # Download button
                        st.download_button(
                            label="Download Test Cases (JSON)",
                            data=json_str,
                            file_name="test_cases.json",
                            mime="application/json",
                        )
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Test Script Generation Tab
with tab2:
    st.header("Test Script Generation")
    st.write("Convert test cases into executable Selenium test scripts")
    
    # Test case input section
    st.subheader("Test Case Input")
    
    # Initialize test_cases
    test_cases = []
    
    # Check if we have test cases from previous step
    if "test_cases" in st.session_state and len(st.session_state.test_cases) > 0:
        test_cases = st.session_state.test_cases
        st.success(f"Found {len(test_cases)} test cases from previous step")
        
        # Show preview
        with st.expander("Preview Test Cases"):
            st.json(test_cases)
    else:
        st.warning("No test cases found from previous step.")
    
    # Always show file upload option
    st.write("Or upload test cases from a file:")
    uploaded_file = st.file_uploader(
        "Upload Test Cases File",
        type=["json"],
        key="test_script_file_uploader"
    )
    
    if uploaded_file is not None:
        try:
            test_cases = json.loads(uploaded_file.getvalue().decode())
            st.success(f"Loaded {len(test_cases)} test cases from file")
            
            # Show preview
            with st.expander("Preview Test Cases"):
                st.json(test_cases)
        except Exception as e:
            st.error(f"Error loading test cases: {str(e)}")
    
    # Generate button
    st.subheader("Generate Test Scripts")
    if len(test_cases) > 0:
        st.write(f"Ready to generate test scripts for {len(test_cases)} test cases")
        
        generate_button = st.button("Generate Test Scripts", key="generate_test_scripts")
        
        if generate_button:
            if not llm_api_key:
                st.error("Please enter an API key")
            else:
                with st.spinner("Generating test scripts..."):
                    try:
                        # Prepare request
                        request_data = {
                            "test_cases": test_cases,
                            "llm_config": {
                                "provider": llm_provider,
                                "model": llm_model,
                                "api_key": llm_api_key,
                                "temperature": float(llm_temperature),
                                "max_tokens": int(llm_max_tokens),
                            },
                            "agent_config": {
                                "framework": "pytest",
                                "browser": "chrome"
                            }
                        }
                        
                        # Call API
                        response = requests.post(
                            f"{API_URL}/api/test-script-generation",
                            json=request_data,
                        )
                        
                        if response.status_code == 200:
                            test_scripts = response.json()["test_scripts"]
                            
                            # Store in session state
                            st.session_state.test_scripts = test_scripts
                            
                            # Display test scripts
                            st.success(f"Generated {len(test_scripts)} test script files")
                            
                            # Create tabs for each script
                            script_tabs = st.tabs(list(test_scripts.keys()))
                            
                            for i, (filename, content) in enumerate(test_scripts.items()):
                                with script_tabs[i]:
                                    # Display with syntax highlighting
                                    st.code(content, language="python")
                                    
                                    # Download button for individual file
                                    st.download_button(
                                        label=f"Download {filename}",
                                        data=content,
                                        file_name=filename,
                                        mime="text/plain",
                                    )
                        else:
                            st.error(f"Error: {response.status_code} - {response.text}")
                    
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    else:
        st.error("No test cases available. Please generate test cases in the previous tab or upload a file.")

# Test Data Generation Tab
with tab3:
    st.header("Test Data Generation")
    st.write("Generate synthetic test data for test cases")
    
    # Test data input section
    st.subheader("Test Data Input")
    
    # Initialize input_data
    input_data = None
    
    # Check for test cases from previous steps
    has_test_cases = "test_cases" in st.session_state and len(st.session_state.test_cases) > 0
    has_test_scripts = "test_scripts" in st.session_state and len(st.session_state.test_scripts) > 0
    
    # Create tabs for different input methods
    data_input_tabs = st.tabs(["Test Cases", "Test Scripts", "File Upload"])
    
    # Test Cases tab
    with data_input_tabs[0]:
        if has_test_cases:
            input_data_cases = st.session_state.test_cases
            st.success(f"Found {len(input_data_cases)} test cases from previous step")
            
            # Show preview
            with st.expander("Preview Test Cases"):
                st.json(input_data_cases)
            
            # Use button
            if st.button("Use These Test Cases", key="use_test_cases"):
                input_data = input_data_cases
                st.session_state.selected_input_data = input_data
                st.success("Test cases selected for data generation")
                st.experimental_rerun()
        else:
            st.warning("No test cases found from previous step. Please generate test cases first.")
    
    # Test Scripts tab
    with data_input_tabs[1]:
        if has_test_scripts:
            input_data_scripts = st.session_state.test_scripts
            st.success(f"Found {len(input_data_scripts)} test scripts from previous step")
            
            # Show preview
            with st.expander("Preview Test Scripts"):
                for filename, content in input_data_scripts.items():
                    st.text(filename)
                    st.code(content[:500] + "..." if len(content) > 500 else content, language="python")
            
            # Use button
            if st.button("Use These Test Scripts", key="use_test_scripts"):
                input_data = input_data_scripts
                st.session_state.selected_input_data = input_data
                st.success("Test scripts selected for data generation")
                st.experimental_rerun()
        else:
            st.warning("No test scripts found from previous step. Please generate test scripts first.")
    
    # File Upload tab
    with data_input_tabs[2]:
        st.write("Upload a JSON file with test cases or a Python file with test scripts:")
        uploaded_file = st.file_uploader(
            "Upload Input File",
            type=["json", "py"],
            key="test_data_file_uploader"
        )
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".json"):
                    file_data = json.loads(uploaded_file.getvalue().decode())
                    st.success(f"Loaded JSON data from file")
                else:
                    file_data = {uploaded_file.name: uploaded_file.getvalue().decode()}
                    st.success(f"Loaded Python file")
                
                # Show preview
                with st.expander("Preview Input Data"):
                    st.write(file_data)
                
                # Use button
                if st.button("Use This File", key="use_uploaded_file"):
                    input_data = file_data
                    st.session_state.selected_input_data = input_data
                    st.success("File data selected for data generation")
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"Error loading input data: {str(e)}")
    
    # Check if we have selected input data in session state
    if "selected_input_data" in st.session_state:
        input_data = st.session_state.selected_input_data
        
        # Generate button section
        st.subheader("Generate Test Data")
        
        if isinstance(input_data, list):
            st.write(f"Ready to generate test data for {len(input_data)} test cases")
        elif isinstance(input_data, dict):
            st.write(f"Ready to generate test data for {len(input_data)} test scripts")
        else:
            st.write("Ready to generate test data")
            
        generate_button = st.button("Generate Test Data", key="generate_test_data")
        
        if generate_button:
            if not llm_api_key:
                st.error("Please enter an API key")
            else:
                with st.spinner("Generating test data..."):
                    try:
                        # Prepare request
                        request_data = {
                            "input_data": input_data,
                            "llm_config": {
                                "provider": llm_provider,
                                "model": llm_model,
                                "api_key": llm_api_key,
                                "temperature": float(llm_temperature),
                                "max_tokens": int(llm_max_tokens),
                            },
                            "agent_config": {
                                "output_format": "json",
                                "data_variations": 5,
                                "include_edge_cases": True
                            }
                        }
                        
                        # Call API
                        response = requests.post(
                            f"{API_URL}/api/test-data-generation",
                            json=request_data,
                        )
                        
                        if response.status_code == 200:
                            test_data = response.json()["test_data"]
                            
                            # Store in session state
                            st.session_state.test_data = test_data
                            
                            # Display test data
                            st.success("Generated test data")
                            
                            # Format as JSON for display
                            json_str = json.dumps(test_data, indent=2)
                            st.code(json_str, language="json")
                            
                            # Download button
                            st.download_button(
                                label="Download Test Data (JSON)",
                                data=json_str,
                                file_name="test_data.json",
                                mime="application/json",
                            )
                        else:
                            st.error(f"Error: {response.status_code} - {response.text}")
                    
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

# Agent Chat Tab
with tab4:
    st.header("Chat with Agents")
    st.write("Have a conversation with the testing agents to get help with your testing needs.")
    
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