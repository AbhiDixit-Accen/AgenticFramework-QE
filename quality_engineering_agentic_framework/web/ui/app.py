"""
Streamlit UI for Quality Engineering Agentic Framework

This module provides a Streamlit-based UI for the framework.
"""

import os
import json
import yaml
import logging
import streamlit as st
from typing import Dict, List, Any, Optional, Union
import tempfile
from datetime import datetime
import uuid
import nest_asyncio
import asyncio
import requests
import random
import string
import pandas as pd
from io import StringIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure the API URL
#API_URL = "http://127.0.0.1:8080"
#API_URL = "https://agenticframework-qe-4.onrender.com"
API_URL = "http://16.171.147.102:8080"

# Initialize session state
if 'generate_data' not in st.session_state:
    st.session_state.generate_data = False
    st.session_state.test_data = None
    st.session_state.data_format = "JSON"
    st.session_state.data_size = 10
    st.session_state.llm_provider = "openai"  # Default values, will be overridden
    st.session_state.llm_model = "gpt-3.5-turbo"
    st.session_state.llm_api_key = ""
    st.session_state.llm_temperature = 0.7
    st.session_state.llm_max_tokens = 1000

async def generate_test_cases(requirements, llm_provider, llm_model, llm_api_key, llm_temperature, llm_max_tokens, mode="requirement"):
    """Generate test cases by calling the correct backend API based on mode."""
    print("\n=== Starting generate_test_cases ===")
    print(f"Requirements: {requirements[:100]}...")
    try:
        # Route based on mode
        if mode == "api":
            # API-based test case generation
            api_details = requirements
            if isinstance(requirements, str):
                # For demo, treat requirements as base_url (should be replaced by actual UI fields)
                api_details = {
                    "base_url": requirements,
                    "endpoint": "/demo-endpoint",
                    "method": "GET",
                    "headers": {},
                    "params": {},
                    "body": {},
                    "auth": {}
                }
            request_data = {
                "api_details": api_details,
                "llm_config": {
                    "provider": llm_provider,
                    "model": llm_model,
                    "api_key": llm_api_key,
                    "temperature": float(llm_temperature),
                    "max_tokens": int(llm_max_tokens)
                }
            }
            api_url = f"{API_URL}/api/api-test-case-generation"
        else:
            # Requirement-based test case generation
            request_data = {
                "requirements": requirements,
                "llm_config": {
                    "provider": llm_provider,
                    "model": llm_model,
                    "api_key": llm_api_key,
                    "temperature": float(llm_temperature),
                    "max_tokens": int(llm_max_tokens)
                }
            }
            api_url = f"{API_URL}/api/test-case-generation"

        
        print("\n=== Sending request to API ===")
        print(f"URL: {api_url}")
        print(f"Request data: {json.dumps(request_data, indent=2)}")
        
        # Make the API call
        response = requests.post(
            api_url,
            json=request_data,
            timeout=60
        )
        
        print("\n=== Received response ===")
        print(f"Status code: {response.status_code}")
        print(f"Response text: {response.text[:500]}")
        
        # Get response data safely
        try:
            response_data = response.json()
            print("\n=== Parsed JSON response ===")
            print(f"Type: {type(response_data)}")
            print(f"Content: {json.dumps(response_data, indent=2)[:500]}")
            
            # Handle response format
            if isinstance(response_data, dict) and "test_cases" in response_data:
                result = response_data["test_cases"]
            elif isinstance(response_data, list):
                result = response_data
            elif isinstance(response_data, dict):
                result = [response_data]
            else:
                result = []
            
            # Ensure all items in result are properly formatted dictionaries
            validated_result = []
            for idx, item in enumerate(result, 1):
                try:
                    # Handle string items
                    if isinstance(item, str):
                        validated_result.append({
                            "title": f"Test Case {idx}",
                            "description": item,
                            "preconditions": [],
                            "actions": [],
                            "expected_results": [],
                            "test_data": {}
                        })
                    # Handle dictionary items
                    elif isinstance(item, dict):
                        # Ensure all required fields exist
                        if not isinstance(item.get('title'), str):
                            item['title'] = f"Test Case {idx}"
                        if not isinstance(item.get('description'), str):
                            item['description'] = ''
                        if not isinstance(item.get('preconditions'), (list, tuple)):
                            item['preconditions'] = []
                        if not isinstance(item.get('actions'), (list, tuple)) and not isinstance(item.get('steps'), (list, tuple)):
                            item['actions'] = []
                        if not isinstance(item.get('expected_results'), (list, tuple)):
                            item['expected_results'] = []
                        if 'test_data' not in item or not isinstance(item['test_data'], dict):
                            item['test_data'] = {}
                        
                        # Convert steps to actions if needed
                        if 'steps' in item and 'actions' not in item:
                            item['actions'] = item.pop('steps')
                            
                        validated_result.append(item)
                    # Handle any other type
                    else:
                        validated_result.append({
                            "title": f"Test Case {idx}",
                            "description": str(item),
                            "preconditions": [],
                            "actions": [],
                            "expected_results": [],
                            "test_data": {}
                        })
                except Exception as e:
                    print(f"Error processing test case {idx}: {str(e)}")
                    print(f"Problematic item: {item}")
                    # Add a placeholder for the failed test case
                    validated_result.append({
                        "title": f"Test Case {idx} (Error)",
                        "description": f"Error processing this test case: {str(e)}",
                        "preconditions": [],
                        "actions": [],
                        "expected_results": [],
                        "test_data": {}
                    })
                
            print(f"\n=== Returning validated test cases ===")
            print(f"Type: {type(validated_result)}")
            print(f"Count: {len(validated_result)}")
            return validated_result
            
        except json.JSONDecodeError as e:
            print(f"\n!!! Failed to parse JSON: {str(e)}")
            print(f"Response text: {response.text[:500]}")
            return []
            
    except Exception as e:
        print(f"\n!!! Error in generate_test_cases: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return []

# Set page configuration
st.set_page_config(
    page_title="Quality Engineering Agentic Framework",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define API URL
#API_URL = "http://127.0.0.1:8080"  # Using 127.0.0.1 instead of localhost for consistency
API_URL = "https://agenticframework-qe-4.onrender.com"

def generate_sample_data(data_format: str, size: int, fields: List[Dict[str, str]]) -> Union[dict, str]:
    """Generate sample test data in the specified format.
    
    Args:
        data_format: Output format (json, csv, sql)
        size: Number of records to generate
        fields: List of field definitions with name and type
        
    Returns:
        Generated data in the specified format
    """
    data = []
    
    # Generate data for each field
    for i in range(size):
        record = {}
        for field in fields:
            field_name = field['name']
            field_type = field['type']
            
            if field_type == 'string':
                value = f"sample_{''.join(random.choices(string.ascii_lowercase, k=5))}_{i}"
            elif field_type == 'number':
                value = random.randint(1, 1000)
            elif field_type == 'boolean':
                value = random.choice([True, False])
            elif field_type == 'date':
                value = f"2023-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            else:
                value = f"value_{i}"
                
            record[field_name] = value
        data.append(record)
    
    # Convert to requested format
    if data_format == 'json':
        return {"test_data": data}
    elif data_format == 'csv':
        df = pd.DataFrame(data)
        return df.to_csv(index=False)
    elif data_format == 'sql':
        if not data:
            return ""
        columns = ", ".join(f'`{col}`' for col in data[0].keys())
        values = []
        for record in data:
            val_list = []
            for v in record.values():
                if isinstance(v, str):
                    val_list.append(f"'{v}'")
                elif isinstance(v, bool):
                    val_list.append('1' if v else '0')
                else:
                    val_list.append(str(v))
            values.append(f"({', '.join(val_list)})")
        return f"INSERT INTO test_data ({columns}) VALUES\n" + ",\n".join(values) + ";"
    
    return {"error": f"Unsupported format: {data_format}"}

def extract_fields_from_test_cases(test_cases: List[dict]) -> List[Dict[str, str]]:
    """Extract field definitions from test cases."""
    fields = []
    
    # Always include these standard fields
    standard_fields = [
        ("test_case_id", "string"),
        ("test_case_title", "string"),
        ("execution_status", "string"),
        ("execution_time", "number"),
        ("tester_name", "string"),
        ("environment", "string"),
        ("browser", "string"),
        ("os", "string"),
        ("test_data_id", "number"),
        ("execution_date", "date"),
        ("is_automated", "boolean"),
        ("defect_found", "boolean"),
        ("defect_id", "string"),
        ("comments", "string"),
        ("screenshot_path", "string"),
        ("test_duration_seconds", "number"),
        ("test_priority", "string"),
        ("test_execution_notes", "string")
    ]
    
    # Add standard fields
    fields.extend([{"name": name, "type": typ} for name, typ in standard_fields])
    
    # Add dynamic fields based on test case content
    for i, tc in enumerate(test_cases[:5]):  # Limit to first 5 test cases to avoid too many fields
        # Add fields from test case title
        title = tc.get('title', '').lower()
        if 'login' in title:
            fields.append({"name": "username", "type": "string"})
            fields.append({"name": "password", "type": "string"})
            fields.append({"name": "login_successful", "type": "boolean"})
        
        if 'search' in title:
            fields.append({"name": "search_term", "type": "string"})
            fields.append({"name": "search_results_count", "type": "number"})
        
        # Add fields from actions
        for action in tc.get('actions', []):
            if 'click' in action.lower():
                fields.append({"name": "element_clicked", "type": "string"})
            if 'enter' in action.lower():
                fields.append({"name": "text_entered", "type": "string"})
    
    # Remove duplicates while preserving order
    seen = set()
    unique_fields = []
    for field in fields:
        field_tuple = (field['name'], field['type'])
        if field_tuple not in seen:
            seen.add(field_tuple)
            unique_fields.append(field)
    
    return unique_fields

def main():
    """Main function for the Streamlit app."""
    # Initialize session state with proper structure
    if 'test_cases' not in st.session_state:
        st.session_state.test_cases = []
    
    if 'test_scripts' not in st.session_state:
        st.session_state.test_scripts = {}
        
    # Debug flag - set to True to see debug info
    debug = False  # Disabled by default
    
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
                "OpenAI Model",
                options=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                index=0,
            )
        else:
            llm_model = st.selectbox(
                "Gemini Model",
                options=["gemini-pro"],
                index=0,
            )
        
        llm_api_key = st.text_input(
            f"{llm_provider.capitalize()} API Key",
            type="password",
            placeholder=f"Enter your {llm_provider} API key",
        )
        
        llm_temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.01,
        )
        
        llm_max_tokens = st.number_input(
            "Max Tokens",
            min_value=1,
            max_value=4000,
            value=2000,
            step=100,
        )
        
        # Display version in sidebar
        st.divider()
        st.markdown("### Version 1.0")
        
        if llm_api_key:
            st.session_state[f"{llm_provider}_api_key"] = llm_api_key
        
        # Load API key from session state if available
        if f"{llm_provider}_api_key" in st.session_state:
            llm_api_key = st.session_state[f"{llm_provider}_api_key"]
    
    # Main content - tabs
    tab_names = ["Test Case Generation", "Test Script Generation", "Test Data Generation"]
    
    # Create tabs and verify count
    try:
        tabs = st.tabs(tab_names)
        if len(tabs) != len(tab_names):
            st.error(f"Tab count mismatch. Expected {len(tab_names)} tabs, got {len(tabs)}.")
            st.stop()
        
        # Verify tab indices are within bounds
        if len(tabs) < 3:
            st.error(f"Not enough tabs created. Expected 3, got {len(tabs)}.")
            st.stop()
        
        # Define tab indices as constants for better maintainability
        TAB_TEST_CASE_GEN = 0
        TAB_TEST_SCRIPT_GEN = 1
        TAB_TEST_DATA_GEN = 2
        
    except Exception as e:
        st.error(f"Error creating tabs: {str(e)}")
        st.stop()
    
    # Test Case Generation Tab
    with tabs[TAB_TEST_CASE_GEN]:
        st.header("Test Case Generation")
        st.write("Convert requirements into structured test cases")
        
        # Input method selection
        input_method = st.radio("Input Method", options=["Text", "File Upload"], horizontal=True)
        
        requirements_text = ""
        if input_method == "Text":
            requirements_text = st.text_area("Requirements", height=200)
        else:
            uploaded_file = st.file_uploader("Upload requirements document", type=["txt", "md"])
            if uploaded_file is not None:
                # For txt and md files
                requirements_text = uploaded_file.getvalue().decode("utf-8")
        
        # Output format selection (simplified)
        output_format = "JSON"  # Default to JSON for simplicity
        
        # Generate button with API call
        if st.button("Generate Test Cases"):
            if not requirements_text or not requirements_text.strip():
                st.error("Please enter some requirements first.")
            elif not llm_api_key:
                st.error("Please enter your API key in the sidebar.")
            else:
                with st.spinner("Generating comprehensive test cases... (this may take a moment)"):
                    try:
                        # Generate test cases using the API
                        test_cases = asyncio.run(generate_test_cases(
                            requirements=requirements_text,
                            llm_provider=llm_provider,
                            llm_model=llm_model,
                            llm_api_key=llm_api_key,
                            llm_temperature=llm_temperature,
                            llm_max_tokens=llm_max_tokens
                        ))
                        
                        if test_cases:  # Only update if we got results
                            # Store in session state
                            st.session_state.test_cases = test_cases
                            
                            # Show success message
                            st.success(f"✅ Generated {len(test_cases)} comprehensive test cases!")
                        
                    except Exception as e:
                        st.error(f"Error generating test cases: {str(e)}")
        
        # Display test cases if available
        if 'test_cases' in st.session_state and st.session_state.test_cases:
            try:
                test_cases = st.session_state.test_cases
                print(f"\n=== Displaying test cases ===")
                print(f"Test cases type: {type(test_cases)}")
                print(f"Test cases content: {test_cases}")
                
                if not test_cases:
                    st.warning("No test cases were generated.")
                    return
                    
                st.subheader("Generated Test Cases")
                
                # Ensure test_cases is a list
                if not isinstance(test_cases, list):
                    test_cases = [test_cases]
                
                # Display each test case with robust error handling
                print(f"\n=== Processing {len(test_cases)} test cases ===")
                for i, tc in enumerate(test_cases, 1):
                    print(f"\nProcessing test case {i}:")
                    print(f"Type: {type(tc)}")
                    print(f"Content: {tc}")
                    
                    # Initialize a clean test case dictionary
                    safe_tc = {
                        'title': f'Test Case {i}',
                        'description': '',
                        'preconditions': [],
                        'actions': [],
                        'expected_results': [],
                        'test_data': {}
                    }
                    
                    # Safely copy values from the original test case
                    try:
                        if isinstance(tc, dict):
                            # Handle title
                            if 'title' in tc and tc['title']:
                                safe_tc['title'] = str(tc['title'])
                            
                            # Handle description
                            if 'description' in tc and tc['description']:
                                safe_tc['description'] = str(tc['description'])
                            
                            # Handle preconditions
                            if 'preconditions' in tc and isinstance(tc['preconditions'], (list, tuple)):
                                safe_tc['preconditions'] = [str(p) for p in tc['preconditions'] if p]
                            
                            # Handle actions/steps
                            if 'actions' in tc and isinstance(tc['actions'], (list, tuple)):
                                safe_tc['actions'] = [str(a) for a in tc['actions'] if a]
                            elif 'steps' in tc and isinstance(tc['steps'], (list, tuple)):
                                safe_tc['actions'] = [str(s) for s in tc['steps'] if s]
                            
                            # Handle expected results
                            if 'expected_results' in tc and isinstance(tc['expected_results'], (list, tuple)):
                                safe_tc['expected_results'] = [str(r) for r in tc['expected_results'] if r]
                            
                            # Handle test data
                            if 'test_data' in tc and isinstance(tc['test_data'], dict):
                                safe_tc['test_data'] = {str(k): v for k, v in tc['test_data'].items()}
                        
                        elif isinstance(tc, str):
                            safe_tc['description'] = tc
                        else:
                            safe_tc['description'] = str(tc)
                        
                        # Display the test case
                        with st.expander(f"{i}. {safe_tc['title']}"):
                            # Description
                            if safe_tc['description']:
                                st.write("**Description:**", safe_tc['description'])
                            
                            # Preconditions
                            if safe_tc['preconditions']:
                                st.write("**Preconditions:**")
                                for j, pre in enumerate(safe_tc['preconditions'], 1):
                                    st.write(f"{j}. {pre}")
                            
                            # Actions
                            if safe_tc['actions']:
                                st.write("**Steps:**")
                                for j, action in enumerate(safe_tc['actions'], 1):
                                    st.write(f"{j}. {action}")
                            
                            # Expected Results
                            if safe_tc['expected_results']:
                                st.write("**Expected Results:**")
                                for j, result in enumerate(safe_tc['expected_results'], 1):
                                    st.write(f"{j}. {result}")
                            
                            # Test Data
                            if safe_tc['test_data']:
                                st.write("**Test Data:**")
                                st.json(safe_tc['test_data'])
                        
                    except Exception as e:
                        # If anything goes wrong, show a simplified error view
                        error_msg = f"Error displaying test case {i}: {str(e)}"
                        error_type = type(e).__name__
                        
                        print(f"\n!!! {error_msg}")
                        print(f"Error type: {error_type}")
                        print(f"Test case data type: {type(tc)}")
                        print(f"Test case data: {tc}")
                        
                        import traceback
                        print("\nTraceback:")
                        traceback.print_exc()
                        
                        with st.expander(f"{i}. Error displaying test case ({error_type})"):
                            st.error(f"{error_type}: {str(e)}")
                            st.write("\n**Test case data type:**", type(tc).__name__)
                            st.write("\n**Test case data:**")
                            st.json(tc) if isinstance(tc, (dict, list)) else st.code(str(tc))
            
            except Exception as e:
                st.error(f"Error processing test cases: {str(e)}")
                print(f"\n!!! Error in test case display:")
                print(f"Error: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # Download generated test cases
            if 'test_cases' in st.session_state and st.session_state.test_cases:
                col1, col2 = st.columns(2)
                
                with col1:
                    json_data = json.dumps(st.session_state.test_cases, indent=2)
                    st.download_button(
                        label="Download as JSON",
                        data=json_data,
                        file_name=f"test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            
            with col2:
                # CSV download
                import csv
                import io
                
                def generate_csv_data(test_cases):
                    output = io.StringIO()
                    writer = csv.writer(output)
                    
                    # Write header
                    writer.writerow(["ID", "Title", "Description", "Preconditions", "Actions", "Expected Results"])
                    
                    # Write test cases
                    for i, tc in enumerate(test_cases, 1):
                        if not isinstance(tc, dict):
                            continue
                            
                        # Helper function to safely get list values
                        def safe_get_list(data, key):
                            val = data.get(key, [])
                            if isinstance(val, str):
                                return [val]
                            return val if isinstance(val, list) else []
                        
                        writer.writerow([
                            i,
                            tc.get('title', ''),
                            tc.get('description', ''),
                            '; '.join(safe_get_list(tc, 'preconditions')),
                            '; '.join(safe_get_list(tc, 'actions')),
                            '; '.join(safe_get_list(tc, 'expected_results'))
                        ])
                    
                    return output.getvalue()
                
                try:
                    if test_cases and isinstance(test_cases, list):
                        csv_data = generate_csv_data(test_cases)
                        st.download_button(
                            label="Download as CSV",
                            data=csv_data,
                            file_name=f"test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                except Exception as e:
                    st.error(f"Error generating CSV: {str(e)}")
    
    # Test Script Generation Tab
    with tabs[TAB_TEST_SCRIPT_GEN]:
        st.header("Test Script Generation")
        st.write("Convert test cases into executable test scripts")
        
        # Create sub-tabs for Integrated and Standalone solutions
        sub_tab1, sub_tab2 = st.tabs(["🔗 Integrated Solution", "📁 Standalone Solution"])
        
        # Integrated Solution Sub-tab
        with sub_tab1:
            st.subheader("Integrated Solution")
            st.info("Generate test scripts from test cases created in the Test Case Generation tab")
            
            # Check if we have test cases from generation
            if 'test_cases' not in st.session_state or not st.session_state.test_cases:
                st.warning("⚠️ No test cases available. Please generate test cases first in the 'Test Case Generation' tab.")
            else:
                # Display available test cases
                st.subheader("Available Test Cases")
                
                # Show test cases
                for i, tc in enumerate(st.session_state.test_cases, 1):
                    if isinstance(tc, dict):
                        # If it's a dictionary, try to get the title
                        title = tc.get('title', f"Test Case {i}")
                        st.write(f"{i}. {title}")
                    else:
                        # If it's a simple value, just show it
                        st.write(f"{i}. {str(tc)}")
                
                st.markdown("---")
                
                # Show test script configuration
                st.subheader("Test Script Configuration")
                
                # Language selection
                language = st.selectbox(
                    "Programming Language",
                    options=["Python", "JavaScript", "Java", "C#"],
                    index=0,
                    key="integrated_language"
                )
                
                # Framework selection
                framework_options = {
                    "Python": ["pytest", "unittest", "robot"],
                    "JavaScript": ["jest", "mocha", "cypress"],
                    "Java": ["JUnit", "TestNG", "Cucumber"],
                    "C#": ["NUnit", "xUnit", "MSTest"],
                }
                
                framework = st.selectbox(
                    "Test Framework",
                    options=framework_options[language],
                    index=0,
                    key="integrated_framework"
                )
                
                # Generate button
                if st.button("Generate Test Scripts", key="generate_integrated_scripts"):
                    with st.spinner("Generating test scripts..."):
                        # Prepare request with properly formatted test cases
                        formatted_test_cases = []
                        for tc in st.session_state.test_cases:
                            formatted_tc = {
                                "title": tc.get("title", "Untitled Test Case"),
                                "description": tc.get("description", ""),
                                "preconditions": tc.get("preconditions", []),
                                "actions": tc.get("actions", []),
                                "expected_results": tc.get("expected_results", []),
                                "test_data": {}
                            }
                            formatted_test_cases.append(formatted_tc)
                        
                        # Ensure consistent case for language and framework
                        language_lower = language.lower()
                        framework_lower = framework.lower()
                        
                        # Map UI framework names to backend expected values if needed
                        framework_mapping = {
                            'java': {
                                'junit': 'junit',
                                'testng': 'testng',
                                'cucumber': 'cucumber'
                            },
                            'javascript': {
                                'jest': 'jest',
                                'mocha': 'mocha',
                                'cypress': 'cypress'
                            },
                            'c#': {
                                'nunit': 'nunit',
                                'xunit': 'xunit',
                                'mstest': 'mstest'
                            },
                            'python': {
                                'pytest': 'pytest',
                                'unittest': 'unittest',
                                'robot': 'robot'
                            }
                        }
                        
                        # Get the mapped framework or use the original if not found
                        mapped_framework = framework_mapping.get(language_lower, {}).get(framework_lower, framework_lower)
                        
                        request_data = {
                            "test_cases": formatted_test_cases,
                            "llm_config": {
                                "provider": llm_provider,
                                "model": llm_model,
                                "api_key": llm_api_key,
                                "temperature": float(llm_temperature),
                                "max_tokens": int(llm_max_tokens),
                            },
                            "agent_config": {
                                "language": language_lower,
                                "framework": mapped_framework,
                                "browser": "chrome"
                            }
                        }
                        
                        # Call API with better error handling
                        try:
                            response = requests.post(
                                f"{API_URL}/api/test-script-generation",
                                json=request_data,
                                timeout=30  # 30 seconds timeout
                            )
                            response.raise_for_status()  # Will raise an HTTPError for bad responses
                            response_data = response.json()
                            
                            if "test_scripts" not in response_data:
                                raise ValueError("Invalid response format: 'test_scripts' key not found")
                                
                            test_scripts = response_data["test_scripts"]
                            
                            # Store test scripts in session state
                            st.session_state.test_scripts = test_scripts
                            
                            # Display success message
                            st.success(f"Successfully generated {len(test_scripts)} test scripts!")
                            
                            # Display each test script in an expander
                            for filename, content in test_scripts.items():
                                with st.expander(f"📄 {filename}", expanded=True):
                                    # Determine language for syntax highlighting
                                    file_ext = filename.split('.')[-1].lower()
                                    lang_map = {
                                        'py': 'python',
                                        'java': 'java',
                                        'js': 'javascript',
                                        'cs': 'csharp',
                                        'feature': 'gherkin',
                                        'xml': 'xml',
                                        'json': 'json',
                                        'md': 'markdown',
                                        'txt': 'text'
                                    }
                                    lang = lang_map.get(file_ext, 'text')
                                    st.code(content, language=lang)
                                    
                                    # Download button for individual script
                                    st.download_button(
                                        label=f"⬇️ Download {filename}",
                                        data=content,
                                        file_name=filename,
                                        mime="text/plain",
                                        key=f"dl_integrated_{filename}"
                                    )
                            
                            # Create a zip file with all scripts
                            with tempfile.TemporaryDirectory() as temp_dir:
                                # Write scripts to temp directory
                                for filename, content in test_scripts.items():
                                    file_path = os.path.join(temp_dir, filename)
                                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                                    with open(file_path, "w", encoding="utf-8") as f:
                                        f.write(content)
                                
                                # Create zip file
                                import shutil
                                zip_path = os.path.join(temp_dir, "test_scripts.zip")
                                shutil.make_archive(os.path.join(temp_dir, "test_scripts"), "zip", temp_dir)
                                
                                # Read zip file
                                with open(zip_path, "rb") as f:
                                    zip_data = f.read()
                                
                                # Download button for zip file
                                st.download_button(
                                    label="📦 Download All Scripts (ZIP)",
                                    data=zip_data,
                                    file_name="test_scripts.zip",
                                    mime="application/zip",
                                    key="download_integrated_zip"
                                )
                            
                        except requests.exceptions.RequestException as e:
                            st.error(f"❌ Failed to connect to the API: {str(e)}")
                        except ValueError as e:
                            st.error(f"❌ Invalid response from server: {str(e)}")
                            if 'response_data' in locals():
                                st.json(response_data)  # Show the actual response for debugging
                        except Exception as e:
                            st.error(f"❌ An unexpected error occurred: {str(e)}")
        
        # Standalone Solution Sub-tab
        with sub_tab2:
            st.subheader("Standalone Solution")
            st.info("Upload an Excel file containing your test cases to generate test scripts")
            
            # Upload File section
            st.subheader("Upload File")
            st.write("Upload your test script files here")
            uploaded_file = st.file_uploader("Browse Excel file", type=[".xlsx", ".xls"], key="standalone_excel_uploader")
            
            # Check if file is uploaded
            if uploaded_file is not None:
                try:
                    # Create uploadedTestCases directory if it doesn't exist
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    upload_dir = os.path.join(base_dir, 'uploadedTestCases')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Save the uploaded file
                    file_path = os.path.join(upload_dir, uploaded_file.name)
                    with open(file_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Verify file was saved
                    if not os.path.exists(file_path):
                        st.error(f"Failed to save file to: {file_path}")
                    else:
                        st.success(f"✅ File successfully uploaded: {uploaded_file.name}")
                    
                    # Read the Excel file
                    df = pd.read_excel(file_path)
                    
                    # Drop unwanted unnamed columns
                    df['title'] = df['title'].fillna("Untitled Test Case")
                    for col in ['preconditions', 'actions', 'expected_results']:
                        df[col] = df[col].apply(lambda x: [i.strip() for i in str(x).split(',')] if pd.notna(x) else [])
                    
                    
                    # Display the uploaded test cases
                    st.subheader("Uploaded Test Cases")
                    st.dataframe(df, use_container_width=True)
                    
                    # Store the test cases in a temporary session variable for standalone
                    st.session_state.standalone_test_cases = df.to_dict('records')
                    
                    st.markdown("---")
                    
                    # Show test script configuration
                    st.subheader("Test Script Configuration")
                    
                    # Language selection
                    language_standalone = st.selectbox(
                        "Programming Language",
                        options=["Python", "JavaScript", "Java", "C#"],
                        index=0,
                        key="standalone_language"
                    )
                    
                    # Framework selection
                    framework_options_standalone = {
                        "Python": ["pytest", "unittest", "robot"],
                        "JavaScript": ["jest", "mocha", "cypress"],
                        "Java": ["JUnit", "TestNG", "Cucumber"],
                        "C#": ["NUnit", "xUnit", "MSTest"],
                    }
                    
                    framework_standalone = st.selectbox(
                        "Test Framework",
                        options=framework_options_standalone[language_standalone],
                        index=0,
                        key="standalone_framework"
                    )
                    
                    # Generate button
                    if st.button("Generate Test Scripts", key="generate_standalone_scripts"):
                        with st.spinner("Generating test scripts..."):
                            # Prepare request with properly formatted test cases
                            formatted_test_cases = []
                            for tc in st.session_state.standalone_test_cases:
                                formatted_tc = {
                                    "title": tc.get("title", tc.get(list(tc.keys())[0]) if tc else "Untitled Test Case"),
                                    "description": tc.get("description", ""),
                                    "preconditions": tc.get("preconditions", []),
                                    "actions": tc.get("actions", []),
                                    "expected_results": tc.get("expected_results", []),
                                    "test_data": {}
                                }
                                formatted_test_cases.append(formatted_tc)
                            
                            # Ensure consistent case for language and framework
                            language_lower = language_standalone.lower()
                            framework_lower = framework_standalone.lower()
                            
                            # Map UI framework names to backend expected values if needed
                            framework_mapping = {
                                'java': {
                                    'junit': 'junit',
                                    'testng': 'testng',
                                    'cucumber': 'cucumber'
                                },
                                'javascript': {
                                    'jest': 'jest',
                                    'mocha': 'mocha',
                                    'cypress': 'cypress'
                                },
                                'c#': {
                                    'nunit': 'nunit',
                                    'xunit': 'xunit',
                                    'mstest': 'mstest'
                                },
                                'python': {
                                    'pytest': 'pytest',
                                    'unittest': 'unittest',
                                    'robot': 'robot'
                                }
                            }
                            
                            # Get the mapped framework or use the original if not found
                            mapped_framework = framework_mapping.get(language_lower, {}).get(framework_lower, framework_lower)
                            
                            request_data = {
                                "test_cases": formatted_test_cases,
                                "llm_config": {
                                    "provider": llm_provider,
                                    "model": llm_model,
                                    "api_key": llm_api_key,
                                    "temperature": float(llm_temperature),
                                    "max_tokens": int(llm_max_tokens),
                                },
                                "agent_config": {
                                    "language": language_lower,
                                    "framework": mapped_framework,
                                    "browser": "chrome"
                                }
                            }
                            
                            # Call API with better error handling
                            try:
                                response = requests.post(
                                    f"{API_URL}/api/test-script-generation",
                                    json=request_data,
                                    timeout=30  # 30 seconds timeout
                                )
                                response.raise_for_status()  # Will raise an HTTPError for bad responses
                                response_data = response.json()
                                
                                if "test_scripts" not in response_data:
                                    raise ValueError("Invalid response format: 'test_scripts' key not found")
                                    
                                test_scripts = response_data["test_scripts"]
                                
                                # Store test scripts in session state
                                st.session_state.standalone_test_scripts = test_scripts
                                
                                # Display success message
                                st.success(f"Successfully generated {len(test_scripts)} test scripts!")
                                
                                # Display each test script in an expander
                                for filename, content in test_scripts.items():
                                    with st.expander(f"📄 {filename}", expanded=True):
                                        # Determine language for syntax highlighting
                                        file_ext = filename.split('.')[-1].lower()
                                        lang_map = {
                                            'py': 'python',
                                            'java': 'java',
                                            'js': 'javascript',
                                            'cs': 'csharp',
                                            'feature': 'gherkin',
                                            'xml': 'xml',
                                            'json': 'json',
                                            'md': 'markdown',
                                            'txt': 'text'
                                        }
                                        lang = lang_map.get(file_ext, 'text')
                                        st.code(content, language=lang)
                                        
                                        # Download button for individual script
                                        st.download_button(
                                            label=f"⬇️ Download {filename}",
                                            data=content,
                                            file_name=filename,
                                            mime="text/plain",
                                            key=f"dl_standalone_{filename}"
                                        )
                                
                                # Create a zip file with all scripts
                                with tempfile.TemporaryDirectory() as temp_dir:
                                    # Write scripts to temp directory
                                    for filename, content in test_scripts.items():
                                        file_path = os.path.join(temp_dir, filename)
                                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                                        with open(file_path, "w", encoding="utf-8") as f:
                                            f.write(content)
                                    
                                    # Create zip file
                                    import shutil
                                    zip_path = os.path.join(temp_dir, "test_scripts.zip")
                                    shutil.make_archive(os.path.join(temp_dir, "test_scripts"), "zip", temp_dir)
                                    
                                    # Read zip file
                                    with open(zip_path, "rb") as f:
                                        zip_data = f.read()
                                    
                                    # Download button for zip file
                                    st.download_button(
                                        label="📦 Download All Scripts (ZIP)",
                                        data=zip_data,
                                        file_name="test_scripts.zip",
                                        mime="application/zip",
                                        key="download_standalone_zip"
                                    )
                                
                            except requests.exceptions.RequestException as e:
                                st.error(f"❌ Failed to connect to the API: {str(e)}")
                            except ValueError as e:
                                st.error(f"❌ Invalid response from server: {str(e)}")
                                if 'response_data' in locals():
                                    st.json(response_data)  # Show the actual response for debugging
                            except Exception as e:
                                st.error(f"❌ An unexpected error occurred: {str(e)}")
                    
                except Exception as e:
                    st.error(f"Error reading Excel file: {str(e)}")
            else:
                st.warning("⚠️ Please upload an Excel file to continue")
    
    # Test Data Generation Tab
    with tabs[TAB_TEST_DATA_GEN]:
        st.header("Test Data Generation")
        st.write("Generate test data for your test cases")
        
        # Get LLM settings from the sidebar
        llm_provider = st.session_state.get('llm_provider', 'openai')
        llm_model = st.session_state.get('llm_model', 'gpt-3.5-turbo')
        
        # Get API key using the provider-specific key (e.g., 'openai_api_key')
        llm_api_key = st.session_state.get(f"{llm_provider}_api_key", '')
        if not llm_api_key and f"{llm_provider}_api_key" in st.session_state:
            llm_api_key = st.session_state[f"{llm_provider}_api_key"]
            
        llm_temperature = float(st.session_state.get('llm_temperature', 0.7))
        llm_max_tokens = int(st.session_state.get('llm_max_tokens', 1000))
        
        # Debug info
        if debug:
            st.info("Debug mode is ON.")
        
        # ---- New controls and action for generating test data ----
        st.subheader("Configuration")
        input_source = st.radio(
            "Input Source",
            options=["Test Cases", "Test Scripts"],
            index=0,
            horizontal=True,
        )
        data_format = st.selectbox("Output Format", ["JSON", "CSV", "SQL"], index=0)
        record_count = st.number_input("Records per dataset", min_value=1, max_value=1000, value=10, step=1)
        include_edge_cases = st.checkbox("Include edge cases", value=True)
        
        # Generate button
        if st.button("Generate Test Data", key="generate_test_data_btn"):
            # Validate prerequisites
            if input_source == "Test Cases" and not st.session_state.get('test_cases'):
                st.error("No test cases available. Please generate test cases first.")
                st.stop()
            if input_source == "Test Scripts" and not st.session_state.get('test_scripts'):
                st.error("No test scripts available. Please generate test scripts first.")
                st.stop()
            if not llm_api_key:
                st.error("Please enter your API key in the sidebar.")
                st.stop()
            
            # Prepare input_data based on source
            if input_source == "Test Cases":
                input_data = st.session_state.test_cases
            else:
                input_data = st.session_state.test_scripts  # dict mapping filenames to contents
            
            request_payload = {
                "input_data": input_data,
                "llm_config": {
                    "provider": llm_provider,
                    "model": llm_model,
                    "api_key": llm_api_key,
                    "temperature": float(llm_temperature),
                    "max_tokens": int(llm_max_tokens),
                },
                "agent_config": {
                    "output_format": data_format.lower(),
                    "data_variations": int(record_count),
                    "include_edge_cases": bool(include_edge_cases),
                }
            }
            
            with st.spinner("Generating test data..."):
                try:
                    resp = requests.post(
                        f"{API_URL}/api/test-data-generation",
                        json=request_payload,
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    test_data = data.get("test_data", {})
                    
                    if not isinstance(test_data, dict) or not test_data:
                        st.warning("The API returned no test data.")
                    else:
                        st.session_state.generate_data = True
                        st.session_state.test_data = test_data
                        st.session_state.data_format = data_format
                        st.success(f"Generated {len(test_data)} dataset(s) of test data.")
                except requests.exceptions.RequestException as e:
                    st.error(f"Failed to connect to the API: {e}")
                except ValueError as e:
                    st.error(f"Invalid response from the API: {e}")
        
        # Display generated test data if available
        if st.session_state.get('generate_data') and st.session_state.test_data:
            for dataset_name, dataset in st.session_state.test_data.items():
                st.subheader(f"Dataset: {dataset_name}")
                # Display based on format
                if st.session_state.data_format == "JSON":
                    st.json(dataset)
                elif st.session_state.data_format == "CSV":
                    st.code(dataset, language="text")
                elif st.session_state.data_format == "SQL":
                    st.code(dataset, language="sql")
                    
                    # Prepare download data
                    file_extension = st.session_state.data_format.lower()
                    download_data = json.dumps(dataset, indent=2) if isinstance(dataset, (dict, list)) else str(dataset)
                    
                    # Download button
                    st.download_button(
                        label=f"Download {dataset_name}",
                        data=download_data,
                        file_name=f"{dataset_name}.{file_extension}",
                        mime=f"application/{file_extension}",
                        key=f"download_{dataset_name}"
                    )
    
    # # API Test Case Generation Tab (COMMENTED OUT - NOT VISIBLE TO END USER)
    # with tabs[TAB_API_TEST_CASE_GEN]:
    #     st.header("API Test Case Generation")
    #     st.write("Generate test cases for your APIs by providing the details below.")
    #
    #     with st.form("api_test_case_form"):
    #         base_url = st.text_input("API Base URL", help="e.g. https://api.example.com")
    #         endpoint = st.text_input("Endpoint Path", help="e.g. /v1/resource")
    #         method = st.selectbox("HTTP Method", ["GET", "POST", "PUT", "DELETE", "PATCH"])
    #         headers = st.text_area("Headers (JSON)", value="{}", help='e.g. {"Authorization": "Bearer ..."}')
    #         params = st.text_area("Query Parameters (JSON)", value="{}", help='e.g. {"page": 1}')
    #         body = st.text_area("Request Body (JSON)", value="{}", help='For POST/PUT/PATCH, e.g. {"name": "foo"}')
    #         auth = st.text_area("Authentication Info (JSON)", value="{}", help='e.g. {"type": "basic", "username": "...", "password": "..."}')
    #
    #         submitted = st.form_submit_button("Generate API Test Cases")
    #
    #     if submitted:
        #         # Validate JSON fields
    #         def safe_json_loads(s, field):
    #             try:
    #                 return json.loads(s) if s.strip() else {}
    #             except Exception as e:
    #                 st.error(f"Invalid JSON in {field}: {e}")
    #                 return None
    #
    #         headers_json = safe_json_loads(headers, "Headers")
    #         params_json = safe_json_loads(params, "Query Parameters")
    #         body_json = safe_json_loads(body, "Request Body")
    #         auth_json = safe_json_loads(auth, "Authentication Info")
    #
    #         if None in (headers_json, params_json, body_json, auth_json):
    #             st.stop()
    #
    #         if not base_url.strip() or not endpoint.strip():
    #             st.error("Base URL and Endpoint Path are required.")
    #             st.stop()
    #
    #         api_details = {
    #             "base_url": base_url.strip(),
    #             "endpoint": endpoint.strip(),
    #             "method": method,
    #             "headers": headers_json,
    #             "params": params_json,
    #             "body": body_json,
    #             "auth": auth_json,
    #         }
    #
    #         # Validate LLM config fields
    #         if not all([llm_provider, llm_model, llm_api_key, llm_temperature, llm_max_tokens]):
    #             st.error("All LLM configuration fields are required.")
    #             st.stop()
    #
    #         # Prepare request for backend
    #         request_data = {
    #             "api_details": api_details,
    #             "llm_config": {
    #                 "provider": llm_provider,
    #                 "model": llm_model,
    #                 "api_key": llm_api_key,
    #                 "temperature": float(llm_temperature),
    #                 "max_tokens": int(llm_max_tokens),
    #             },
    #         }
    #
    #
    #         with st.spinner("Generating API test cases..."):
    #             try:
    #                 response = requests.post(
    #                     f"{API_URL}/api/api-test-case-generation",
    #                     json=request_data,
    #                     timeout=30,
    #                 )
    #                 response.raise_for_status()
    #                 data = response.json()
    #                 test_cases = data.get("test_cases", [])
    #                 if test_cases:
    #                     st.success(f"Generated {len(test_cases)} API test cases!")
    #                     for i, tc in enumerate(test_cases, 1):
    #                         with st.expander(f"{i}. {tc.get('title', 'Untitled Test Case')}"):
    #                             st.json(tc)
    #                 else:
    #                     st.warning("No test cases generated.")
    #             except Exception as e:
    #                 st.error(f"Error generating API test cases: {e}")

    # # Chat Bot Tab (COMMENTED OUT - NOT VISIBLE TO END USER)
    # with tabs[TAB_CHAT_BOT]:
    #     st.header("Chat Bot")
    #     st.write("Have a conversation with our simple AI assistant")
    #     
    #     # Initialize chat history if not already present
    #     if "chat_history" not in st.session_state:
    #         st.session_state.chat_history = []
    #     
    #     # Display chat history
    #     for message in st.session_state.chat_history:
    #         with st.chat_message(message["role"]):
    #             st.write(message["content"])
    #     
    #     # Chat input area
    #     user_input = st.chat_input("Type your message here...", key="chat_input")
    #     
    #     # Process message when user sends input
    #     if user_input:
    #         # Add user message to chat history
    #         st.session_state.chat_history.append({"role": "user", "content": user_input})
    #         
    #         with st.chat_message("assistant"):
    #             with st.spinner("Thinking..."):
    #                 try:
    #                     # Check if this is a test case generation request
    #                     if "generate test case" in user_input.lower() or "create test case" in user_input.lower() or "test case" in user_input.lower():
    #                         # Generate test cases using the extract_fields_from_test_cases function
    #                         test_cases = extract_fields_from_test_cases(user_input)
    #                         
    #                         # Store test cases in session state for use in the Test Case Generation tab
    #                         st.session_state.test_cases = test_cases
    #                         
    #                         # Create a response with the generated test cases
    #                         bot_response = f"I've generated {len(test_cases)} test cases based on your requirements. Here's a summary:\n\n"
    #                         for i, tc in enumerate(test_cases, 1):
    #                             bot_response += f"{i}. {tc.get('name', 'Unnamed Test Case')}\n"
    #                         
    #                         # Add a note about where to find the full test cases
    #                         bot_response += "\nYou can view and download the full test cases in the 'Test Case Generation' tab."
    #                         
    #                     else:
    #                         # Prepare request data for regular chat
    #                         request_data = {
    #                             "message": user_input,
    #                             "history": [msg for msg in st.session_state.chat_history if msg["role"] != "user"],
    #                             "llm_config": {
    #                                 "provider": llm_provider,
    #                                 "model": llm_model,
    #                                 "api_key": llm_api_key,
    #                                 "temperature": float(llm_temperature),
    #                                 "max_tokens": int(llm_max_tokens),
    #                             },
    #                             "system_prompt": "You are a helpful assistant who provides clear and concise responses.",
    #                             "chat_model": "Basic"
    #                         }
    #                         
    #                         # Make the API request
    #                         response = requests.post(
    #                             f"{API_URL}/api/chat",
    #                             json=request_data,
    #                             timeout=10  # 10 seconds timeout
    #                         )
    #                         
    #                         if response.status_code == 200:
    #                             response_data = response.json()
    #                             bot_response = response_data.get("response", "I don't have a response for that.")
    #                         else:
    #                             # Fall back to a generic response if the API fails
    #                             bot_response = "I'm having trouble connecting to the chat service. Please try again later."
    #                     
    #                     # Display the bot's response
    #                     st.write(bot_response)
    #                     
    #                     # Add bot's response to chat history
    #                     st.session_state.chat_history.append({"role": "assistant", "content": bot_response})
    #                     
    #                     # Rerun to update the UI
    #                     st.rerun()
    #                     
    #                 except Exception as e:
    #                     # Handle any unexpected errors
    #                     error_msg = f"Error processing your request: {str(e)}"
    #                     logger.error(error_msg)
    #                     st.error(error_msg)
    #                     st.session_state.chat_history.append({"role": "assistant", "content": error_msg})

def load_prompt_template(template_name: str) -> Optional[str]:
    """Load a prompt template from the API."""
    try:
        response = requests.get(f"{API_URL}/api/prompt-templates?name={template_name}")
        
        if response.status_code == 200:
            templates = response.json().get("templates", [])
            for template in templates:
                if template.get("name") == template_name:
                    return template.get("content", "")
        
        return None
    except Exception as e:
        st.error(f"Error loading prompt template: {str(e)}")
        return None


def save_prompt_template(template_name: str, content: str) -> bool:
    """Save a prompt template via the API."""
    try:
        request_data = {
            "name": template_name,
            "content": content
        }
        
        response = requests.post(f"{API_URL}/api/prompt-templates", json=request_data)
        
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error saving prompt template: {str(e)}")
        return False


if __name__ == "__main__":
    # Install uvloop for better async performance if available
    try:
        import uvloop  # type: ignore
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass  # uvloop not available, use default asyncio
    
    # Create an event loop and run the async code
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run the Streamlit app with async support
    nest_asyncio.apply()
    
    # Start the Streamlit app
    main()
