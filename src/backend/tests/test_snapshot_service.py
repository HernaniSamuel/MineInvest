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


# tests/test_snapshot_service.py
import pytest
from datetime import date
from decimal import Decimal

from src.backend.services.snapshot_service import (
    create_monthly_snapshot,
    restore_from_snapshot,
    get_snapshot_info
)
from src.backend.services.balance_service import handle_balance_service
from src.backend.schemas.balance import BalanceOperationRequest
from src.backend.schemas.enums import Operation
from src.backend.models.holding import HoldingORM
from src.backend.models.monthly_snapshot import MonthlySnapshotORM


import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.backend.models.base import Base
from src.backend.models.simulation import SimulationORM
from src.backend.models.history_month import HistoryMonthORM
from src.backend.models.asset import AssetORM
from src.backend.schemas.simulation import SimulationCreate

from src.backend.services.simulation_service import (
    create_simulation_service,
    list_simulations_service,
    SimulationAlreadyExistsError,
    delete_simulation_service,
    SimulationNotFoundError
)


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
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
        name="Test Simulation",
        start_date=date(2023, 1, 1),
        base_currency="BRL"
    )
    return create_simulation_service(db_session, sim_data)



def test_create_snapshot(db_session, sample_simulation):
    """Test creating a snapshot."""
    # Add balance
    req = BalanceOperationRequest(
        amount=Decimal("1000.00"),
        operation=Operation.ADD,
        category="contribution"
    )
    handle_balance_service(db_session, sample_simulation.id, req)

    # Create snapshot
    snapshot = create_monthly_snapshot(db_session, sample_simulation.id)

    assert snapshot.simulation_id == sample_simulation.id
    assert Decimal(snapshot.balance) == Decimal("1000.00")
    assert snapshot.month_date == sample_simulation.current_date


def test_create_snapshot_with_holdings(db_session, sample_simulation):
    """Test snapshot captures holdings."""
    # Create holding
    holding = HoldingORM(
        simulation_id=sample_simulation.id,
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        quantity="10.5",
        purchase_price="100.00",
        weight="100",
        current_price="105.00",
        market_value="1102.50"
    )
    db_session.add(holding)
    db_session.commit()

    # Create snapshot
    snapshot = create_monthly_snapshot(db_session, sample_simulation.id)

    assert len(snapshot.holdings_snapshot) == 1
    assert snapshot.holdings_snapshot[0]["ticker"] == "AAPL"
    assert snapshot.holdings_snapshot[0]["quantity"] == "10.5"


def test_only_one_snapshot_kept(db_session, sample_simulation):
    """Test that only the most recent snapshot is kept."""
    # Create first snapshot
    create_monthly_snapshot(db_session, sample_simulation.id)

    count1 = db_session.query(MonthlySnapshotORM).filter(
        MonthlySnapshotORM.simulation_id == sample_simulation.id
    ).count()
    assert count1 == 1

    # Create second snapshot
    create_monthly_snapshot(db_session, sample_simulation.id)

    count2 = db_session.query(MonthlySnapshotORM).filter(
        MonthlySnapshotORM.simulation_id == sample_simulation.id
    ).count()
    assert count2 == 1  # Still only 1


def test_restore_from_snapshot(db_session, sample_simulation):
    """Test restoring from snapshot."""
    # Initial state: 1000 balance
    req1 = BalanceOperationRequest(
        amount=Decimal("1000.00"),
        operation=Operation.ADD,
        category="contribution"
    )
    handle_balance_service(db_session, sample_simulation.id, req1)

    # Create snapshot
    create_monthly_snapshot(db_session, sample_simulation.id)

    # Make changes: withdraw 500
    req2 = BalanceOperationRequest(
        amount=Decimal("500.00"),
        operation=Operation.REMOVE,
        category="withdrawal"
    )
    handle_balance_service(db_session, sample_simulation.id, req2)

    # Balance should be 500 now
    db_session.refresh(sample_simulation)
    assert Decimal(sample_simulation.balance) == Decimal("500.00")

    # Restore
    restored_sim = restore_from_snapshot(db_session, sample_simulation.id)

    # Should be back to 1000
    assert Decimal(restored_sim.balance) == Decimal("1000.00")


def test_restore_keeps_dividends(db_session, sample_simulation):
    """Test that restore keeps dividend operations."""
    # Initial: 1000 balance
    req1 = BalanceOperationRequest(
        amount=Decimal("1000.00"),
        operation=Operation.ADD,
        category="contribution"
    )
    handle_balance_service(db_session, sample_simulation.id, req1)

    # Snapshot
    create_monthly_snapshot(db_session, sample_simulation.id)

    # Add dividend (should be kept)
    req2 = BalanceOperationRequest(
        amount=Decimal("50.00"),
        operation=Operation.ADD,
        category="dividend",
        ticker="AAPL"
    )
    handle_balance_service(db_session, sample_simulation.id, req2)

    # Add withdrawal (should be removed)
    req3 = BalanceOperationRequest(
        amount=Decimal("200.00"),
        operation=Operation.REMOVE,
        category="withdrawal"
    )
    handle_balance_service(db_session, sample_simulation.id, req3)

    # Restore
    restored_sim = restore_from_snapshot(db_session, sample_simulation.id)

    # Should have: snapshot balance (1000) + dividend (50) = 1050
    # ✅ Compare as Decimal to handle precision
    assert Decimal(restored_sim.balance) == Decimal("1050.00")


def test_restore_fails_without_snapshot(db_session, sample_simulation):
    """Test restore fails when no snapshot exists."""
    with pytest.raises(ValueError) as exc:
        restore_from_snapshot(db_session, sample_simulation.id)

    assert "No snapshot exists" in str(exc.value)


def test_get_snapshot_info(db_session, sample_simulation):
    """Test getting snapshot information."""
    # No snapshot initially
    info = get_snapshot_info(db_session, sample_simulation.id)
    assert info is None

    # Create snapshot
    create_monthly_snapshot(db_session, sample_simulation.id)

    # Get info
    info = get_snapshot_info(db_session, sample_simulation.id)
    assert info["exists"] is True
    assert info["can_restore"] is True