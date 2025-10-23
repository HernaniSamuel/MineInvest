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
