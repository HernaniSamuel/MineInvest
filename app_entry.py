import threading
import webbrowser
import time
import uvicorn
from src.backend.main import app

def open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    threading.Thread(target=open_browser).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)
