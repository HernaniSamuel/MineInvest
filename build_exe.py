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


import os
import platform
import subprocess

NAME = "mineinvest"
ICON_PATH = "assets/icon.ico"
SEP = ";" if platform.system() == "Windows" else ":"

# 1️⃣ Build frontend
print("🧩 Building frontend...")
npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
subprocess.run([npm_cmd, "run", "build"], cwd="src/frontend-react", check=True)

# 2️⃣ Build executável
print("⚙️  Building executable...")
cmd = [
    "pyinstaller",
    "--noconfirm",
    "--onefile",
    f"--name={NAME}",
    f"--icon={ICON_PATH}",
    f"--add-data=src/frontend-react/dist{SEP}frontend-react/dist",
    "app_entry.py",
]
subprocess.run(cmd, check=True)

print(f"\n✅ Build completo! Executável disponível em dist/{NAME}.exe")
