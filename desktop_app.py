import subprocess
import time
import os
import sys
import threading
import socket
import multiprocessing
import traceback

# Setup logging to a file so we can see what's happening in the frozen app
log_file = os.path.expanduser("~/qeaf_app.log")

class LoggerWriter:
    def __init__(self, filename):
        self.filename = filename

    def write(self, message):
        if message.strip():
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(self.filename, "a") as f:
                f.write(f"[{timestamp}] {message.strip()}\n")
    
    def flush(self):
        pass

sys.stdout = LoggerWriter(log_file)
sys.stderr = LoggerWriter(log_file)

def log(message):
    print(message)

log("--- Starting QEAF Desktop App ---")
log(f"Executable: {sys.executable}")
log(f"Frozen: {getattr(sys, 'frozen', False)}")
log(f"Args: {sys.argv}")

# Determine root directory
if getattr(sys, 'frozen', False):
    # If the app is frozen, the resources are in sys._MEIPASS
    root_dir = sys._MEIPASS
else:
    root_dir = os.path.dirname(os.path.abspath(__file__))

log(f"Root dir: {root_dir}")
sys.path.insert(0, root_dir)

try:
    from quality_engineering_agentic_framework.web.api.endpoints import start_api_server
    log("Successfully imported start_api_server")
except Exception as e:
    log(f"FAILED to import start_api_server: {e}")
    log(traceback.format_exc())

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_backend(port):
    log(f"Starting backend server on port {port}...")
    try:
        start_api_server(port)
    except Exception as e:
        log(f"Backend server error: {e}")
        log(traceback.format_exc())

def start_frontend(port, backend_port):
    log(f"Starting frontend UI on port {port}...")
    ui_dir = os.path.join(root_dir, "quality_engineering_agentic_framework", "web", "ui")
    
    env = os.environ.copy()
    env["API_URL"] = f"http://127.0.0.1:{backend_port}"
    env["PYTHONPATH"] = root_dir + os.pathsep + env.get("PYTHONPATH", "")
    
    log(f"UI Dir: {ui_dir}")
    
    def run_streamlit():
        try:
            import streamlit.web.cli as stcli
            import sys
            
            # Prepare arguments for streamlit
            sys.argv = [
                "streamlit", "run", os.path.join(ui_dir, "app.py"),
                "--server.port", str(port),
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false",
                "--global.developmentMode", "false"
            ]
            log(f"Running Streamlit with args: {sys.argv}")
            stcli.main()
        except Exception as e:
            log(f"FAILED to run Streamlit in thread: {e}")
            log(traceback.format_exc())

    # Run Streamlit in a daemon thread
    threading.Thread(target=run_streamlit, daemon=True).start()
    log("Streamlit thread started")

def main():
    try:
        # Monkeypatch signal globally to prevent 'signal only works in main thread' errors
        try:
            import signal
            signal.signal = lambda sig, handler: None
            log("Applied global signal monkeypatch")
        except Exception as e:
            log(f"Failed to apply signal monkeypatch: {e}")

        multiprocessing.freeze_support()
        
        import webview
        log("Successfully imported webview")

        backend_port = 8080
        frontend_port = 8501
        
        if is_port_in_use(backend_port) or is_port_in_use(frontend_port):
            log("Standard ports in use, finding alternatives...")
            while is_port_in_use(backend_port): backend_port += 1
            while is_port_in_use(frontend_port): frontend_port += 1

        log(f"Backend port: {backend_port}, Frontend port: {frontend_port}")

        # 1. Start Backend in a daemon thread
        backend_thread = threading.Thread(target=start_backend, args=(backend_port,))
        backend_thread.daemon = True
        backend_thread.start()
        
        log("Waiting for backend...")
        # Wait up to 10 seconds for backend
        for _ in range(10):
            if is_port_in_use(backend_port):
                log("Backend is UP")
                break
            time.sleep(1)
        
        # 2. Start Frontend
        start_frontend(frontend_port, backend_port)
        
        log("Waiting for UI to initialize...")
        # Wait up to 20 seconds for UI
        ui_ready = False
        for i in range(20):
            if is_port_in_use(frontend_port):
                log(f"UI port {frontend_port} is active after {i} seconds")
                ui_ready = True
                break
            time.sleep(1)
            if i % 5 == 0: log(f"Still waiting for UI... ({i}s)")
        
        if not ui_ready:
            log("WARNING: UI port never became active. Proceeding anyway...")
        else:
            # Give it another couple of seconds to actually serve the content
            time.sleep(2)
        
        log("Launching native window...")
        window = webview.create_window(
            "Quality Engineering Agentic Framework", 
            f"http://localhost:{frontend_port}", 
            width=1200, 
            height=800
        )
        webview.start(debug=True)
        
    except Exception as e:
        log(f"CRITICAL ERROR in main: {e}")
        log(traceback.format_exc())
    finally:
        log("--- Stopping Application ---")
        sys.exit(0)

if __name__ == "__main__":
    main()
