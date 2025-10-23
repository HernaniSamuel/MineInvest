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


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from src.backend.routes import simulation, trading, holding, time, assets, exchange

app = FastAPI(
    title="MineInvest API",
    description="Investment simulation platform with historical data",
    version="1.0.0"
)

# CORS settings - allow everything!
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Register routers with /api prefix
prefix = "/api"
app.include_router(simulation.router, prefix=prefix)
app.include_router(trading.router, prefix=prefix)
app.include_router(holding.router, prefix=prefix)
app.include_router(time.router, prefix=prefix)
app.include_router(assets.router, prefix=prefix)
app.include_router(exchange.router, prefix=prefix)

# ============================================
# 🎨 FRONTEND SERVING
# ============================================

FRONTEND_BUILD_DIR = Path(__file__).parent.parent / "frontend-react" / "dist"

print(f"\n🔍 Procurando frontend em: {FRONTEND_BUILD_DIR}")
print(f"   Existe? {FRONTEND_BUILD_DIR.exists()}")

if FRONTEND_BUILD_DIR.exists():
    # Verifica se tem index.html
    index_html = FRONTEND_BUILD_DIR / "index.html"
    if index_html.exists():
        print(f"   ✅ index.html encontrado!")

        # Serve arquivos estáticos (JS, CSS, images)
        assets_dir = FRONTEND_BUILD_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
            print(f"   ✅ Assets montados em /assets")


        # Rota catch-all para servir o index.html
        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            """
            Serve o frontend React para rotas que não são da API
            """
            # Se começa com api/, não serve frontend
            if full_path.startswith("api/"):
                return {"error": "API endpoint not found"}

            # Se é um arquivo que existe, serve ele
            file_path = FRONTEND_BUILD_DIR / full_path
            if file_path.is_file():
                return FileResponse(file_path)

            # Caso contrário, serve index.html (React Router)
            return FileResponse(FRONTEND_BUILD_DIR / "index.html")


        print(f"\n✅ Frontend configurado com sucesso!")
        print(f"   🌐 Frontend: http://127.0.0.1:8000/")
        print(f"   🔌 API: http://127.0.0.1:8000/api/")
    else:
        print(f"   ❌ index.html não encontrado em {FRONTEND_BUILD_DIR}")
        print(f"   Execute: cd src/frontend-react && npm run build")


        @app.get("/")
        def read_root():
            return {
                "message": "MineInvest API",
                "status": "running",
                "warning": "Frontend index.html not found. Run 'npm run build' in src/frontend-react/"
            }
else:
    print(f"   ❌ Diretório não encontrado!")
    print(f"\n📋 Para criar o build:")
    print(f"   cd src/frontend-react")
    print(f"   npm run build")


    @app.get("/")
    def read_root():
        return {
            "message": "MineInvest API",
            "status": "running",
            "mode": "API-only",
            "warning": "Frontend build directory not found at src/frontend-react/dist/"
        }

print("\n" + "=" * 60 + "\n")