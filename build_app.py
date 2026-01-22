import os
import subprocess
import sys
import shutil

def build():
    print("Starting build process...")
    
    # 1. Install dependencies if not present
    deps = ["pyinstaller", "pywebview", "streamlit", "fastapi", "uvicorn"]
    if sys.platform == "darwin":
        deps.append("pyobjc")
        
    for dep in deps:
        try:
            if dep == "pyinstaller": import PyInstaller
            elif dep == "pywebview": import webview
            elif dep == "streamlit": import streamlit
            elif dep == "fastapi": import fastapi
            elif dep == "uvicorn": import uvicorn
            elif dep == "pyobjc": import objc
        except ImportError:
            print(f"Installing {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])

    # 2. Define data files to include
    # Streamlit files, config, templates, etc.
    datas = [
        ("quality_engineering_agentic_framework/web/ui", "quality_engineering_agentic_framework/web/ui"),
        ("quality_engineering_agentic_framework/utils/rag/data", "quality_engineering_agentic_framework/utils/rag/data"),
        ("config", "config"),
        ("requirements.txt", "."),
    ]
    
    data_args = []
    for src, dst in datas:
        data_args.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

    # 3. Define the command
    # On macOS, windowed + onefile is deprecated/problematic
    mode_arg = "--onedir" if sys.platform == "darwin" else "--onefile"
    
    cmd = [
        "pyinstaller",
        "--noconfirm",
        mode_arg,
        "--windowed",  # Windowed mode for native app feel
        "--name", "QEAF-Desktop",
        "--collect-all", "webview",
        "--collect-all", "streamlit",
        "--collect-all", "fastapi",
        "--collect-all", "uvicorn",
        "--collect-all", "chromadb",
        "--collect-all", "posthog",
        "--collect-all", "onnxruntime",
        "--collect-all", "tiktoken",
        "--collect-all", "tiktoken_ext",
        "--hidden-import", "clr",
        "--hidden-import", "chromadb.telemetry.product.posthog",
        *data_args,
        "desktop_app.py"
    ]
    
    # Platform specific hidden imports
    if sys.platform == "darwin":
        cmd.insert(cmd.index("desktop_app.py"), "--hidden-import")
        cmd.insert(cmd.index("desktop_app.py"), "objc")
    elif sys.platform == "win32":
        # pythonnet is often required for clr on windows
        try:
            import clr
        except ImportError:
            print("Installing pythonnet for Windows support...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pythonnet"])
    
    print(f"Running command: {' '.join(cmd)}")
    
    # 4. Run PyInstaller
    try:
        subprocess.check_call(cmd)
        print("\nBuild successful! Executable can be found in the 'dist' folder.")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {e}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    build()
