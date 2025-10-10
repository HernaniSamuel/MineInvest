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
from src.backend.routes import simulation, trading, holding, time

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
    ],
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

@app.get("/")
def read_root():
    return {"message": "MineInvest API", "status": "running"}

# Register routers
app.include_router(simulation.router)
app.include_router(trading.router)
app.include_router(holding.router)
app.include_router(time.router)