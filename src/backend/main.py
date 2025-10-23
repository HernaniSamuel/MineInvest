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

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.backend.routes import simulation, trading, holding, time, assets, exchange

app = FastAPI(
    title="MineInvest API",
    description="Investment simulation platform with historical data",
    version="1.0.0"
)

# ============================================
# 🧭 Corrigir path do build React (funciona dentro do .exe)
# ============================================
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)  # caminho temporário do executável extraído
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_BUILD_DIR = BASE_DIR / "frontend-react" / "dist"

print(f"\n🔍 Procurando frontend em: {FRONTEND_BUILD_DIR}")
print(f"   Existe? {FRONTEND_BUILD_DIR.exists()}")

# ============================================
# 🔌 CORS + Rotas
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = "/api"
app.include_router(simulation.router, prefix=prefix)
app.include_router(trading.router, prefix=prefix)
app.include_router(holding.router, prefix=prefix)
app.include_router(time.router, prefix=prefix)
app.include_router(assets.router, prefix=prefix)
app.include_router(exchange.router, prefix=prefix)

# ============================================
# 🎨 Servindo frontend buildado
# ============================================
if FRONTEND_BUILD_DIR.exists():
    index_html = FRONTEND_BUILD_DIR / "index.html"
    if index_html.exists():
        print(f"   ✅ index.html encontrado!")

        # Servir assets
        assets_dir = FRONTEND_BUILD_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            if full_path.startswith("api/"):
                return {"error": "API endpoint not found"}
            file_path = FRONTEND_BUILD_DIR / full_path
            return FileResponse(file_path) if file_path.is_file() else FileResponse(index_html)
    else:
        print(f"   ❌ index.html não encontrado dentro de {FRONTEND_BUILD_DIR}")
else:
    print(f"   ⚠️ Diretório do frontend não encontrado (verifique o build e o parâmetro --add-data no PyInstaller)")

    @app.get("/")
    def read_root():
        return {
            "message": "MineInvest API",
            "status": "running",
            "mode": "API-only",
            "warning": f"Frontend build directory not found at {FRONTEND_BUILD_DIR}"
        }
