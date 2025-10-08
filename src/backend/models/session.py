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


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.backend.models.base import Base

from src.backend.models.simulation import SimulationORM
from src.backend.models.holding import HoldingORM
from src.backend.models.history_month import HistoryMonthORM
from src.backend.models.asset import AssetORM
from src.backend.models.ipca_cache import IPCACacheORM
from src.backend.models.monthly_snapshot import MonthlySnapshotORM


engine = create_engine('sqlite:///simulation.db')
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
