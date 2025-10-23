# Copyright 2025 Hernani Samuel Diniz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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