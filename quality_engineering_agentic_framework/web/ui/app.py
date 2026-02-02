"""
Streamlit UI for Quality Engineering Agentic Framework

This module provides a Streamlit-based UI for the framework.
"""

import os
import json
import yaml
import logging
import streamlit as st
import streamlit.components.v1 as components
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
import textwrap

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure the API URL
# Configure the API URL
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8080")
# API_URL = "https://agenticframework-qe-4.onrender.com"

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

if 'inspector_session_id' not in st.session_state:
    st.session_state.inspector_session_id = None
    st.session_state.show_inspector_popup = False
    st.session_state.captured_elements_count = 0
    st.session_state.inspector_elements = []
    st.session_state.inspector_script = ""
    st.session_state.inspector_error = ""
    st.session_state.imported_elements = []
    st.session_state.import_error = ""
    st.session_state.import_upload_nonce = 0

if 'import_upload_nonce' not in st.session_state:
    st.session_state.import_upload_nonce = 0

async def generate_test_cases(requirements, llm_provider, llm_model, llm_api_key, llm_temperature, llm_max_tokens, mode="requirement", selected_documents=None):
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
                },
                "selected_documents": selected_documents
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
                # Store product context if available
                if "product_context" in response_data:
                    st.session_state.product_context = response_data["product_context"]
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
                
            print(f"\n=== Returning validated results ===")
            return {
                "test_cases": validated_result,
                "product_context": response_data.get("product_context") if isinstance(response_data, dict) else None
            }
            
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


def ensure_inspector_session_id() -> str:
    """Ensure the inspector session ID exists and return it."""
    session_id = st.session_state.get("inspector_session_id")
    if not session_id:
        session_id = f"inspector_{uuid.uuid4().hex[:8]}"
        st.session_state.inspector_session_id = session_id
    return session_id


def start_new_inspector_session() -> None:
    """Begin a brand-new inspector session and reset counters."""
    st.session_state.inspector_session_id = f"inspector_{uuid.uuid4().hex[:8]}"
    st.session_state.captured_elements_count = 0
    st.session_state.inspector_elements = []
    st.session_state.inspector_error = ""


def fetch_inspector_script(force_refresh: bool = False) -> Optional[str]:
    """Fetch inspector JavaScript from the backend and cache it."""
    if st.session_state.get("inspector_script") and not force_refresh:
        return st.session_state.inspector_script
    try:
        response = requests.get(f"{API_URL}/api/inspect/script", timeout=15)
        response.raise_for_status()
        st.session_state.inspector_script = response.text
        st.session_state.inspector_error = ""
        return response.text
    except Exception as exc:
        st.session_state.inspector_error = f"Failed to load inspector script: {exc}"
        return None


def build_inspector_console_snippet(session_id: str, script_body: str, llm_config: Optional[Dict[str, Any]] = None) -> str:
    """Produce a copy-paste-ready snippet for the browser console."""
    api_literal = json.dumps(API_URL)
    session_literal = json.dumps(session_id)
    llm_literal = "null" if not llm_config else json.dumps(llm_config)
    indented_script = textwrap.indent(script_body.strip(), "      ")
    return (
        "(() => {\n"
        f"  window.QEAF_API_URL = {api_literal};\n"
        f"  window.QEAF_SESSION_ID = {session_literal};\n"
        f"  window.QEAF_LLM_CONFIG = {llm_literal};\n"
    "  window.QEAF_AUTO_ACTIVATE = true;\n"
        "  try {\n"
        "    if (window.QEAFInspector) {\n"
    "      console.info('QEAF Inspector already loaded. Re-activating...');\n"
    "      window.QEAFInspector.activate();\n"
        "    } else {\n"
        f"{indented_script}\n"
    "      if (window.QEAFInspector) {\n"
    "        window.QEAFInspector.activate();\n"
    "      }\n"
    "    }\n"
    "    console.info('Inspector ready to capture elements.');\n"
        "  } catch (error) {\n"
        "    console.error('Failed to initialize inspector', error);\n"
        "  }\n"
        "})();"
    )


def format_session_elements(session_payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format raw session payload into a table-friendly structure."""
    if not isinstance(session_payload, dict):
        return []
    elements = session_payload.get("elements", {}) or {}
    formatted: List[Dict[str, Any]] = []
    for element_id, info in elements.items():
        element_meta = info.get("element_data") or {}
        attrs = element_meta.get("attributes") if isinstance(element_meta, dict) else {}
        attrs = attrs if isinstance(attrs, dict) else {}
        selectors = info.get("selectors") or []
        primary_selector = ""
        selector_type = ""
        for block in selectors:
            if block.get("framework") == "playwright" and block.get("selectors"):
                selection = block["selectors"][0]
                primary_selector = selection.get("selector", "")
                selector_type = selection.get("type", "")
                break
        if not primary_selector and selectors:
            first_block = selectors[0].get("selectors") or []
            if first_block:
                primary_selector = first_block[0].get("selector", "")
                selector_type = first_block[0].get("type", "")
        inner_text = ""
        if isinstance(element_meta, dict):
            inner_text = (element_meta.get("innerText") or element_meta.get("textContent") or "").strip()
        identifier = ""
        if isinstance(element_meta, dict):
            identifier = element_meta.get("id") or attrs.get("data-testid", "")
        else:
            identifier = attrs.get("data-testid", "")
        formatted.append({
            "Element ID": element_id,
            "Tag": element_meta.get("tagName", "") if isinstance(element_meta, dict) else "",
            "ID / Test Attr": identifier,
            "Text": inner_text[:60],
            "Primary Selector": primary_selector,
            "Selector Type": selector_type,
            "Captured": info.get("captured_at"),
        })
    return sorted(formatted, key=lambda item: item.get("Captured") or "", reverse=True)


def parse_exported_inspector_file(raw_bytes: bytes) -> List[Dict[str, Any]]:
    """Convert exported inspector JSON into table rows."""
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"Invalid JSON: {exc}") from exc

    elements = payload.get("elements") or []
    source_session = payload.get("session_id", "import")
    formatted: List[Dict[str, Any]] = []

    for idx, record in enumerate(elements, 1):
        element_meta = record.get("element") or record.get("element_data") or {}
        selectors = record.get("selectors") or []

        selector_value = ""
        selector_type = ""
        if selectors:
            first_block = selectors[0]
            if isinstance(first_block, dict) and first_block.get("selectors"):
                sel_entry = first_block["selectors"][0]
                selector_value = sel_entry.get("selector", "")
                selector_type = sel_entry.get("type", "")
            elif isinstance(first_block, dict):
                selector_value = first_block.get("selector", "")
                selector_type = first_block.get("type", "")

        formatted.append({
            "Element ID": f"import_{idx}",
            "Tag": element_meta.get("tagName", ""),
            "ID / Test Attr": element_meta.get("id") or (element_meta.get("attributes", {}) or {}).get("data-testid", ""),
            "Text": (element_meta.get("innerText") or element_meta.get("textContent") or "").strip()[:60],
            "Primary Selector": selector_value,
            "Selector Type": selector_type,
            "Captured": record.get("capturedAt") or record.get("captured_at"),
            "Source Session": source_session,
        })

    return formatted


def clear_imported_inspector_data() -> None:
    """Reset imported inspector artifacts in session state."""
    st.session_state.imported_elements = []
    st.session_state.import_error = ""
    st.session_state.import_upload_nonce = st.session_state.get("import_upload_nonce", 0) + 1


def render_copy_button(copy_text: str, key: str) -> None:
    """Render a custom copy-to-clipboard button using Streamlit components."""
    safe_text = json.dumps(copy_text)
    components.html(
        f"""
        <div class="qeaf-copy-wrap">
            <button id="{key}" class="qeaf-copy-btn">Copy Snippet</button>
        </div>
        <script>
            (function() {{
                const button = document.getElementById('{key}');
                if (!button) {{
                    return;
                }}
                const original = button.textContent;
                button.addEventListener('click', async () => {{
                    try {{
                        await navigator.clipboard.writeText({safe_text});
                        button.textContent = 'Copied!';
                        button.classList.add('qeaf-copied');
                        setTimeout(() => {{
                            button.textContent = original;
                            button.classList.remove('qeaf-copied');
                        }}, 2000);
                    }} catch (err) {{
                        console.error('Failed to copy inspector snippet', err);
                        button.textContent = 'Copy failed';
                        setTimeout(() => {{
                            button.textContent = original;
                        }}, 2000);
                    }}
                }});
            }})();
        </script>
        <style>
            .qeaf-copy-wrap {{
                display: flex;
                justify-content: flex-end;
                margin-top: 0.5rem;
            }}
            .qeaf-copy-btn {{
                background-color: #0f62fe;
                color: white;
                border: none;
                padding: 0.35rem 0.9rem;
                border-radius: 0.35rem;
                font-size: 0.9rem;
                cursor: pointer;
            }}
            .qeaf-copy-btn.qeaf-copied {{
                background-color: #198038;
            }}
        </style>
        """,
        height=80,
    )


def refresh_elements() -> None:
    """Load captured elements for the current inspector session."""
    session_id = ensure_inspector_session_id()
    try:
        response = requests.get(f"{API_URL}/api/inspect/session/{session_id}", timeout=15)
        response.raise_for_status()
        payload = response.json()
        session_payload = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
        formatted = format_session_elements(session_payload)
        st.session_state.inspector_elements = formatted
        st.session_state.captured_elements_count = len(formatted)
        st.session_state.inspector_error = ""
    except Exception as exc:
        st.session_state.inspector_error = f"Failed to load captured elements: {exc}"


def render_inspector_popup() -> None:
    """Render the Streamlit dialog content for the inspector workflow."""
    session_id = ensure_inspector_session_id()
    inspector_code = fetch_inspector_script()

    def _safe_cast(value, caster, default):
        try:
            return caster(value)
        except (TypeError, ValueError):
            return default

    llm_config = {
        "provider": st.session_state.get("llm_provider", "openai"),
        "model": st.session_state.get("llm_model", "gpt-4"),
        "api_key": st.session_state.get("llm_api_key", ""),
        "temperature": _safe_cast(st.session_state.get("llm_temperature", 0.2), float, 0.2),
        "max_tokens": _safe_cast(st.session_state.get("llm_max_tokens", 2000), int, 2000),
    }

    top_cols = st.columns([3, 2, 1])
    with top_cols[0]:
        st.markdown(f'**Session ID:** `{session_id}`')
        st.caption("Use this ID when correlating captured selectors with generated scripts.")
    with top_cols[1]:
        st.metric("Captured Elements", st.session_state.captured_elements_count)
    with top_cols[2]:
        st.button("♻️ New Session ID", key="new_session_button", on_click=start_new_inspector_session)

    st.button("🔄 Refresh", key="refresh_elements_button", on_click=refresh_elements, use_container_width=True)

    st.markdown("### Step 1 · Copy Inspector Code")
    if inspector_code:
        snippet = build_inspector_console_snippet(session_id, inspector_code, llm_config)
        with st.container(border=True):
            st.markdown("#### Inspector Console Snippet")
            st.caption("Paste this block into your browser console; the inspector auto-activates once loaded.")
            with st.expander("Show / Hide Console Snippet", expanded=False):
                st.code(snippet, language="javascript")
                render_copy_button(snippet, key=f"copy_snippet_{session_id}")
    else:
        st.error("Unable to load inspector JavaScript. Ensure the backend /api/inspect/script endpoint is reachable.")

    with st.expander("Need a demo page?"):
        st.markdown(
            "1. Run `qeaf web` to start the backend and UI.\n"
            "2. Open `examples/inspector_demo.html` in your browser.\n"
            "3. Paste the code above into the browser console and press Enter."
        )

    st.markdown("### Step 2 · Capture & Review Elements")
    import_cols = st.columns([3, 1])
    upload_key = f"inspector_import_upload_{st.session_state.get('import_upload_nonce', 0)}"
    with import_cols[0]:
        uploaded_import = st.file_uploader(
            "Import exported inspector JSON",
            type=["json"],
            key=upload_key,
            help="Upload a JSON export from the browser inspector to review or merge it here.",
        )
    with import_cols[1]:
        st.button(
            "Clear Imported",
            key="clear_imported_button",
            use_container_width=True,
            on_click=clear_imported_inspector_data,
        )

    if uploaded_import is not None:
        try:
            imported_rows = parse_exported_inspector_file(uploaded_import.getvalue())
            st.session_state.imported_elements = imported_rows
            st.session_state.import_error = ""
            st.success(f"Imported {len(imported_rows)} elements from '{uploaded_import.name}'.")
        except ValueError as exc:
            st.session_state.import_error = str(exc)

    if st.session_state.import_error:
        st.error(st.session_state.import_error)

    imported_preview = st.session_state.get("imported_elements", [])
    if imported_preview:
        st.markdown("#### Imported Elements Preview")
        st.caption("Review imported data before merging it with live captures.")
        st.dataframe(pd.DataFrame(imported_preview), use_container_width=True)
        if st.button("Merge Imported Into Table", key="merge_imported_button", use_container_width=True):
            merged = imported_preview + st.session_state.get("inspector_elements", [])
            st.session_state.inspector_elements = merged
            st.session_state.captured_elements_count = len(merged)
            st.session_state.imported_elements = []
            st.success(f"Added {len(imported_preview)} imported elements to this session.")
        st.caption("Merging only affects the table below; it does not sync back to the browser session.")

    st.button(
        "🔍 Load Captured Elements",
        key="load_captured_elements_button",
        use_container_width=True,
        on_click=refresh_elements,
    )

    if st.session_state.inspector_error:
        st.error(st.session_state.inspector_error)

    elements = st.session_state.get("inspector_elements", [])
    if elements:
        st.dataframe(pd.DataFrame(elements), use_container_width=True)
    else:
        st.info("No elements captured yet. Activate the inspector in your browser, click elements, then refresh this list.")

    st.markdown("---")
    if st.button("✅ Close Inspector", use_container_width=True, key="close_inspector_button", type="primary"):
        st.session_state.show_inspector_popup = False
        st.rerun()


@st.dialog("🔍 Browser Element Inspector", width="large")
def inspector_dialog() -> None:
    """Wrapper to render the inspector dialog via Streamlit's modal API."""
    render_inspector_popup()

# Set page configuration
st.set_page_config(
    page_title="Quality Engineering Agentic Framework",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define API URL
# Define API URL
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8080")
# API_URL = "https://agenticframework-qe-4.onrender.com"

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
        
    if 'selected_documents' not in st.session_state:
        st.session_state.selected_documents = []
        
    # Debug flag - set to True to see debug info
    debug = False  # Disabled by default
    
    st.title("Quality Engineering Agentic Framework")
    
    # Sidebar for configuration
    with st.sidebar:
        
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
        
        if llm_api_key:
            st.session_state[f"{llm_provider}_api_key"] = llm_api_key
            st.session_state.llm_api_key = llm_api_key

        # Load API key from session state if available
        if f"{llm_provider}_api_key" in st.session_state:
            llm_api_key = st.session_state[f"{llm_provider}_api_key"]
            st.session_state.llm_api_key = llm_api_key
            
        # Pinned to bottom of sidebar
        st.markdown("---")
        st.caption("Version 2.0.0")
    
    # Main content - tabs
    tab_names = ["Knowledge Hub", "Test Case Generation", "Test Script Generation", "Test Data Generation"]
    
    # Create tabs and verify count
    try:
        tabs = st.tabs(tab_names)
        if len(tabs) != len(tab_names):
            st.error(f"Tab count mismatch. Expected {len(tab_names)} tabs, got {len(tabs)}.")
            st.stop()
        
        # Verify tab indices are within bounds
        if len(tabs) < 4:
            st.error(f"Not enough tabs created. Expected 4, got {len(tabs)}.")
            st.stop()
        
        # Define tab indices as constants for better maintainability
        TAB_KNOWLEDGE_HUB = 0
        TAB_TEST_CASE_GEN = 1
        TAB_TEST_SCRIPT_GEN = 2
        TAB_TEST_DATA_GEN = 3
        # TAB_CHAT_BOT = 4  # Commented out - tab removed
        # TAB_API_TEST_CASE_GEN = 5  # Commented out - tab removed
        
    except Exception as e:
        st.error(f"Error creating tabs: {str(e)}")
        st.stop()

    if st.session_state.get("show_inspector_popup"):
        inspector_dialog()
    
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
                        result = asyncio.run(generate_test_cases(
                            requirements=requirements_text,
                            llm_provider=llm_provider,
                            llm_model=llm_model,
                            llm_api_key=llm_api_key,
                            llm_temperature=llm_temperature,
                            llm_max_tokens=llm_max_tokens,
                            selected_documents=st.session_state.get('selected_documents', [])
                        ))
                        
                        if isinstance(result, dict):
                            test_cases = result.get("test_cases", [])
                            product_context = result.get("product_context")
                        else:
                            test_cases = result
                            product_context = None

                        if test_cases:  # Only update if we got results
                            # Store in session state
                            st.session_state.test_cases = test_cases
                            if product_context:
                                st.session_state.product_context = product_context
                            
                            # Show success message
                            st.success(f"✅ Generated {len(test_cases)} comprehensive test cases!")
                        
                    except Exception as e:
                        st.error(f"Error generating test cases: {str(e)}")
        
        # Display product context if available
        if 'product_context' in st.session_state and st.session_state.product_context:
            with st.expander("🔍 View Synthesized Product Knowledge (RAG Output)", expanded=False):
                st.info("The information below was synthesized from your product documentation to provide context for test generation.")
                st.markdown(st.session_state.product_context)
        
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
                        'test_data': {},
                        'rag_ref': ''
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
                            
                            # Handle RAG reference
                            if 'rag_ref' in tc and tc['rag_ref']:
                                safe_tc['rag_ref'] = str(tc['rag_ref'])
                        
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
                            
                            # RAG Reference (Proof it worked)
                            if safe_tc['rag_ref']:
                                st.info(f"💡 **RAG Reference:** {safe_tc['rag_ref']}")
                            
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
    
    # Knowledge Hub Tab
    with tabs[TAB_KNOWLEDGE_HUB]:
        st.header("📚 Knowledge Hub")
        st.write("Manage your requirement documents for the RAG (Retrieval-Augmented Generation) system")
        
        # session state for selected documents is initialized at startup
        
        # Helper function to clear vector DB
        def clear_vector_db():
            """Clear the vector database and cache"""
            from quality_engineering_agentic_framework.utils.rag.rag_system import DB_PATH
            import shutil
            
            if os.path.exists(DB_PATH):
                try:
                    shutil.rmtree(DB_PATH)
                    print(f"[Knowledge Hub] Cleared vector DB at {DB_PATH}")
                    return True
                except Exception as e:
                    print(f"[Requirements Hub] Failed to clear vector DB: {e}")
                    return False
            return True
        
        # Document List Section with Selection
        st.subheader("📄 Select Documents for Test Generation")
        st.info("Select which documents to use for generating test cases. The vector database will be rebuilt using only the selected documents.")
        
        try:
            from quality_engineering_agentic_framework.utils.rag.rag_system import DATA_PATH
            
            if os.path.exists(DATA_PATH):
                files = sorted([f for f in os.listdir(DATA_PATH) if os.path.isfile(os.path.join(DATA_PATH, f))])
                
                if not files:
                    st.warning("No requirement documents found. Add documents below to get started.")
                else:
                    # Select/Deselect All buttons
                    col_all, col_none, col_info = st.columns([1, 1, 3])
                    with col_all:
                        if st.button("✅ Select All"):
                            st.session_state.selected_documents = files.copy()
                            st.rerun()
                    with col_none:
                        if st.button("❌ Deselect All"):
                            st.session_state.selected_documents = []
                            st.rerun()
                    with col_info:
                        st.caption(f"{len(st.session_state.selected_documents)} of {len(files)} documents selected")
                    
                    st.divider()
                    
                    # Display documents with checkboxes and delete buttons
                    for filename in files:
                        file_path = os.path.join(DATA_PATH, filename)
                        file_stats = os.stat(file_path)
                        
                        col1, col2, col3, col4 = st.columns([0.5, 3, 1.5, 1])
                        
                        with col1:
                            is_selected = filename in st.session_state.selected_documents
                            if st.checkbox(f"Select {filename}", value=is_selected, key=f"select_{filename}", label_visibility="collapsed"):
                                if filename not in st.session_state.selected_documents:
                                    st.session_state.selected_documents.append(filename)
                                    st.rerun()
                            else:
                                if filename in st.session_state.selected_documents:
                                    st.session_state.selected_documents.remove(filename)
                                    st.rerun()
                        
                        with col2:
                            icon = "✅" if is_selected else "📄"
                            st.write(f"{icon} **{filename}**")
                        
                        with col3:
                            st.caption(f"{file_stats.st_size:,} bytes")
                        
                        with col4:
                            if st.button("🗑️", key=f"del_{filename}", help="Delete document"):
                                try:
                                    os.remove(file_path)
                                    if filename in st.session_state.selected_documents:
                                        st.session_state.selected_documents.remove(filename)
                                    st.success(f"Deleted {filename}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to delete: {str(e)}")
            else:
                st.warning(f"Requirements directory not found: {DATA_PATH}")
        except Exception as e:
            st.error(f"Error loading documents: {str(e)}")
        
        st.divider()
        
        # Upload Document Section
        st.subheader("📤 Upload Requirement Document")
        upload_file = st.file_uploader("Choose a file to upload", type=["txt", "md", "pdf", "docx"], key="upload_req_file")
        
        if upload_file is not None:
            col_upload, col_cancel = st.columns([1, 3])
            with col_upload:
                if st.button("Upload & Select", key="upload_btn"):
                    try:
                        from quality_engineering_agentic_framework.utils.rag.rag_system import DATA_PATH
                        
                        file_path = os.path.join(DATA_PATH, upload_file.name)
                        os.makedirs(DATA_PATH, exist_ok=True)
                        
                        with open(file_path, 'wb') as f:
                            f.write(upload_file.getvalue())
                        
                        # Automatically select the uploaded file
                        if upload_file.name not in st.session_state.selected_documents:
                            st.session_state.selected_documents.append(upload_file.name)
                        
                        # Clear vector DB to force rebuild
                        clear_vector_db()
                        
                        st.success(f"✅ Uploaded and selected '{upload_file.name}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error uploading file: {str(e)}")
        
        st.divider()
        
        # Create New Document Section
        with st.expander("✍️ Create New Document from Text"):
            new_doc_name = st.text_input("Document Filename", placeholder="e.g., login_requirements.md", key="new_doc_name")
            new_doc_content = st.text_area("Document Content", height=200, placeholder="Enter your requirements here...", key="new_doc_content")
            
            if st.button("Create & Select Document", key="create_doc_btn"):
                if not new_doc_name or not new_doc_content:
                    st.error("Please provide both filename and content.")
                else:
                    try:
                        from quality_engineering_agentic_framework.utils.rag.rag_system import DATA_PATH
                        
                        # Ensure filename has extension
                        if not new_doc_name.endswith(('.txt', '.md')):
                            new_doc_name += '.md'
                        
                        file_path = os.path.join(DATA_PATH, new_doc_name)
                        os.makedirs(DATA_PATH, exist_ok=True)
                        
                        with open(file_path, 'w') as f:
                            f.write(new_doc_content)
                        
                        # Automatically select the new document
                        if new_doc_name not in st.session_state.selected_documents:
                            st.session_state.selected_documents.append(new_doc_name)
                        
                        # Clear vector DB to force rebuild
                        clear_vector_db()
                        
                        st.success(f"✅ Created and selected '{new_doc_name}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating document: {str(e)}")
        
        st.divider()
        
        # Information Section
        with st.expander("ℹ️ How It Works"):
            st.markdown("""
            ### Document Selection & Vector Database
            
            1. **Select Documents**: Check the boxes next to documents you want to use
            2. **Automatic Rebuild**: The vector database is cleared and will be rebuilt using ONLY selected documents
            3. **Upload/Create**: New documents are automatically selected and trigger a rebuild
            4. **Delete**: Removing a document clears the vector DB for a fresh rebuild
            
            ### Test Case Generation
            
            - Only **selected documents** are indexed in the vector database
            - When you enter requirements (e.g., "test performance"), the system searches only the selected documents
            - This gives you precise control over which documentation influences test generation
            
            ### Tips
            
            - Select documents relevant to your current testing scope
            - Deselect documents to exclude them from test generation
            - The vector DB rebuilds automatically on the next test generation
            """)
    
    # Test Script Generation Tab
    with tabs[TAB_TEST_SCRIPT_GEN]:
        header_col, inspector_col = st.columns([3, 1])
        with header_col:
            st.header("Test Script Generation")
        with inspector_col:
            if st.button("🔍 Inspector", key="open_inspector_button", use_container_width=True):
                ensure_inspector_session_id()
                st.session_state.inspector_error = ""
                st.session_state.show_inspector_popup = True
                inspector_dialog()
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
    
    # API Test Case Generation Tab - COMMENTED OUT
    # with tabs[TAB_API_TEST_CASE_GEN]:
    #     st.header("🚧 API Test Case Generation")
    #     st.info("This feature is currently disabled. Please check back later.")
    #     st.write("Generate test cases for your APIs by providing the details below.")
    #     st.warning("⚠️ This tab is temporarily disabled for maintenance.")

    # Chat Bot Tab - COMMENTED OUT
    # with tabs[TAB_CHAT_BOT]:
    #     st.header("🚧 Chat Bot")
    #     st.info("This feature is currently disabled. Please check back later.")
    #     st.write("Have a conversation with our simple AI assistant.")
    #     st.warning("⚠️ This tab is temporarily disabled for maintenance.")

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
    # Apply nest_asyncio to allow nested event loops (useful for Streamlit)
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except Exception as e:
        # Just log warning, don't crash if it fails (e.g. incompatible loop type)
        print(f"Warning: Could not apply nest_asyncio: {e}")
    
    # Start the Streamlit app
    main()
