import os
import time
import streamlit as st

# Import the existing Streamlit app's main function
from quality_engineering_agentic_framework.web.ui import app as main_app_module

st.set_page_config(
    page_title="Quality Engineering Agentic Framework",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load shared CSS from file
shared_css_path = os.path.join(os.path.dirname(__file__), "shared_styles.css")
with open(shared_css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Default placeholder image
IMAGE_URL = os.environ.get(
    "LOGIN_IMAGE_URL",
    "quality_engineering_agentic_framework/web/ui/img/Image of.png",
)

# Initialize session flags
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "remember" not in st.session_state:
    st.session_state.remember = False

# If authenticated, render the main app and show a logout button
if st.session_state.authenticated:
    with st.sidebar:
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
    # Call the existing app's main function
    main_app_module.main()
else:
    # Split-screen login UI
    left, right = st.columns([1,1], gap="large")
    with left:
      import pathlib
      img_path = pathlib.Path(__file__).parent / "img" / "Image of.png"
      if img_path.exists():
        with open(img_path, "rb") as img_file:
          img_bytes = img_file.read()
        import base64
        img_base64 = base64.b64encode(img_bytes).decode()
        st.markdown(
          f"""
          <div style='display: flex; justify-content: center; align-items: center; height: 100%;'>
            <img src='data:image/png;base64,{img_base64}' style='max-width: 80%; height: auto; display: block; margin: auto;' />
          </div>
          """,
          unsafe_allow_html=True
        )
      else:
        st.warning(f"Image not found: {img_path}")
    
    with right:
        st.markdown(
            """
            <h1 style='text-align: center; color: #A100F2; font-size: 32px; font-weight: 700; margin-bottom: 8px;'>USER LOGIN</h1>
            <p style='text-align: center; color: #666; font-size: 14px; margin-bottom: 32px;'>Enter your credentials to continue</p>
            """,
            unsafe_allow_html=True
        )
        
        with st.form(key="login_form"):
            identifier = st.text_input("Email or Phone / Username", value="", placeholder="Admin")
            password = st.text_input("Password", value="", type="password", placeholder="Password", label_visibility="visible")
            # Show password toggle removed
            remember = st.checkbox("Remember me", value=False)
            
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            
            submit_button = st.form_submit_button("Login", type="primary", width='stretch')
            
            if submit_button:
                # Simple credential check
                if identifier.strip() == "Admin" and password == "Password":
                    st.session_state.authenticated = True
                    st.session_state.remember = remember
                    st.success("Login successful")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Invalid credentials")
