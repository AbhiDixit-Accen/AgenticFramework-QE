"""
Run the simplified Streamlit app for Quality Engineering Agentic Framework
"""

import sys
import os
import subprocess

if __name__ == '__main__':
    # Find the Python executable path
    python_exe = sys.executable
    
    # Run the streamlit app using the Python module approach
    subprocess.run([
        python_exe, 
        "-m", "streamlit", 
        "run", 
        os.path.join('quality_engineering_agentic_framework', 'web', 'ui', 'simple_app.py')
    ])