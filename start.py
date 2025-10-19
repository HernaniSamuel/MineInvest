import subprocess
import sys
import time
from pathlib import Path

def start_backend():
    print("🚀 Starting Backend...")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.backend.main:app", "--reload", "--port", "8000"]
    )

def start_frontend():
    print("🎨 Starting Frontend...")
    frontend_dir = Path(__file__).parent / "src" / "frontend-react"
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    return subprocess.Popen([npm_cmd, "run", "dev"], cwd=frontend_dir)

if __name__ == "__main__":
    try:
        backend = start_backend()
        time.sleep(2)
        frontend = start_frontend()
        print("\n✅ Both servers running!")
        print("📡 Backend:  http://localhost:8000")
        print("🎨 Frontend: http://localhost:5173")
        print("\nPress Ctrl+C to stop\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend.terminate()
        frontend.terminate()
        sys.exit(0)