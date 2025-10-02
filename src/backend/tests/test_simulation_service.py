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


import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.backend.models.base import Base
from src.backend.models.simulation import SimulationORM
from src.backend.models.holding import HoldingORM
from src.backend.models.history_month import HistoryMonthORM
from src.backend.schemas.simulation import SimulationCreate

from src.backend.services.simulation_service import (
    create_simulation_service,
    list_simulations_service,
    SimulationAlreadyExistsError
)


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


def test_create_simulation_duplicate_name_fails(db_session):
    """Test that duplicate names raise error"""
    sim_data = SimulationCreate(
        name="Duplicate Test",
        start_date=date(2023, 1, 1),
        base_currency="BRL"
    )

    # Create first simulation
    create_simulation_service(db_session, sim_data)

    # Attempt to create duplicate
    with pytest.raises(SimulationAlreadyExistsError):
        create_simulation_service(db_session, sim_data)


def test_list_simulations_service(db_session):
    """Test listing simulations"""
    # Create multiple simulations
    for i in range(3):
        sim_data = SimulationCreate(
            name=f"Simulation {i}",
            start_date=date(2023, 1, 1),
            base_currency="BRL"
        )
        create_simulation_service(db_session, sim_data)

    results = list_simulations_service(db_session)

    assert len(results) == 3
    # Should be ordered by ID descending (newest first)
    assert results[0].name == "Simulation 2"