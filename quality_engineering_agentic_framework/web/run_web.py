"""
Run Web Module for Quality Engineering Agentic Framework

This module provides a function to run the web interface.
"""

import os
import subprocess
import threading
import time
import webbrowser
from typing import Optional

from quality_engineering_agentic_framework.utils.logger import get_logger

logger = get_logger(__name__)


def run_api_server(port: int = 8000) -> subprocess.Popen:
    """
    Run the FastAPI server in a subprocess.
    
    Args:
        port: Port to run the server on
        
    Returns:
        Subprocess object
    """
    logger.info(f"Starting API server on port {port}")
    
    # Get the path to the API module
    api_module_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "api",
        "endpoints.py"
    )
    
    # Start the server
    import sys
    process = subprocess.Popen(
        [sys.executable, api_module_path, str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for the server to start
    time.sleep(2)
    
    return process


def run_streamlit_app(port: int = 8501) -> subprocess.Popen:
    """
    Run the Streamlit app in a subprocess.
    
    Args:
        port: Port to run the app on
        
    Returns:
        Subprocess object
    """
    logger.info(f"Starting Streamlit app on port {port}")
    
    # Get the path to the UI module
    ui_module_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "ui",
        "app.py"
    )
    
    # Set environment variables
    env = os.environ.copy()
    env["API_URL"] = f"http://localhost:8080"
    
    # Start the app
    streamlit_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 "venv", "Scripts", "streamlit.exe")
    if not os.path.exists(streamlit_path):
        # Try to find streamlit in the Python scripts directory
        import sys
        streamlit_path = os.path.join(os.path.dirname(sys.executable), "Scripts", "streamlit.exe")
        if not os.path.exists(streamlit_path):
            # Fall back to using python -m streamlit
            process = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", ui_module_path, "--server.port", str(port)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            process = subprocess.Popen(
                [streamlit_path, "run", ui_module_path, "--server.port", str(port)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
    else:
        process = subprocess.Popen(
            [streamlit_path, "run", ui_module_path, "--server.port", str(port)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
    # Wait for the app to start
    time.sleep(2)
    
    return process


def run_web(api_port: int = 8000, ui_port: int = 8501, open_browser: bool = True) -> None:
    """
    Run the web interface.
    
    Args:
        api_port: Port to run the API server on
        ui_port: Port to run the UI server on
        open_browser: Whether to open the browser automatically
    """
    logger.info("Starting web interface")
    
    # Start the API server
    api_process = run_api_server(api_port)
    
    # Start the Streamlit app
    ui_process = run_streamlit_app(ui_port)
    
    # Open the browser
    if open_browser:
        webbrowser.open(f"http://localhost:{ui_port}")
    
    try:
        # Print the URL
        logger.info(f"Web interface running at http://localhost:{ui_port}")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Stopping web interface")
        
        # Stop the processes
        api_process.terminate()
        ui_process.terminate()


if __name__ == "__main__":
    run_web()