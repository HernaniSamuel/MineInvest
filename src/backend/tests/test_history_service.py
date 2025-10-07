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
from src.backend.models.asset import AssetORM
from src.backend.schemas.simulation import SimulationCreate
from src.backend.schemas.balance import BalanceOperationRequest
from src.backend.services.simulation_service import create_simulation_service
from src.backend.services.balance_service import handle_balance_service
from src.backend.services.history_service import get_simulation_history_service
from src.backend.schemas.enums import Operation


@pytest.fixture
def db_session():
    """Create in-memory SQLite  database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def sample_simulation(db_session):
    """Create a simple simulation for testing."""
    sim_data = SimulationCreate(
        name="Test Balance Simulation",
        start_date=date(2023, 1, 1),
        base_currency="BRL"
    )
    return create_simulation_service(db_session, sim_data)


def test_get_simulation_history(db_session, sample_simulation):
    """Test retrieving simulation history."""
    # Add operations
    req1 = BalanceOperationRequest(
        amount=Decimal("1000.00"),
        operation=Operation.ADD,
        category="contribution"
    )
    handle_balance_service(db_session, sample_simulation.id, req1)

    req2 = BalanceOperationRequest(
        amount=Decimal("200.00"),
        operation=Operation.REMOVE,
        category="withdrawal"
    )
    handle_balance_service(db_session, sample_simulation.id, req2)

    # Get history
    history = get_simulation_history_service(db_session, sample_simulation.id)

    assert history.simulation_id == sample_simulation.id
    assert len(history.months) == 1
    assert len(history.months[0].operations) == 2
    assert Decimal(history.months[0].total) == Decimal("800.00")
