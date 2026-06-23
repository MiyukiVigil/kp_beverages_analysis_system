import os
import sys
import subprocess
import time
import webbrowser

def resolve_path(path):
    if getattr(sys, "frozen", False):
        return os.path.abspath(os.path.join(sys._MEIPASS, path))
    return os.path.abspath(os.path.join(os.getcwd(), path))

if __name__ == "__main__":
    # 1. Start the Streamlit server as a separate process
    # This avoids the "main thread" signal error entirely
    cmd = [sys.executable, "-m", "streamlit", "run", resolve_path("app.py"), "--server.headless=true"]
    process = subprocess.Popen(cmd)
    
    # 2. Wait for the server to spin up
    time.sleep(3)
    
    # 3. Open the browser (most Linux/Windows systems will respect this)
    webbrowser.open("http://localhost:8501")
    
    # 4. Keep the runner alive until the server process stops
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()