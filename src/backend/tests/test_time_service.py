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
from src.backend.models.base import Base
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from src.backend.services.time_service import advance_month_service, can_advance_month
from src.backend.models.holding import HoldingORM
from src.backend.models.asset import AssetORM
from src.backend.schemas.balance import BalanceOperationRequest
from src.backend.schemas.enums import Operation
from src.backend.services.balance_service import handle_balance_service


#aaaaah all imports to stop failing
from src.backend.services.snapshot_service import (
    create_monthly_snapshot,
    restore_from_snapshot,
    get_snapshot_info
)
from src.backend.models.monthly_snapshot import MonthlySnapshotORM

from src.backend.models.simulation import SimulationORM
from src.backend.models.history_month import HistoryMonthORM
from src.backend.schemas.simulation import SimulationCreate

from src.backend.services.simulation_service import (
    create_simulation_service,
    list_simulations_service,
    SimulationAlreadyExistsError,
    delete_simulation_service,
    SimulationNotFoundError
)

@pytest.fixture
def sample_simulation(db_session):
    """Create a simple simulation for testing."""
    sim_data = SimulationCreate(
        name="Test Simulation",
        start_date=date(2023, 1, 1),
        base_currency="BRL"
    )
    return create_simulation_service(db_session, sim_data)

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
def simulation_with_holdings(db_session, sample_simulation):
    """Create simulation with balance and holdings."""
    # Add balance
    req = BalanceOperationRequest(
        amount=Decimal("10000.00"),
        operation=Operation.ADD,
        category="contribution"
    )
    handle_balance_service(db_session, sample_simulation.id, req)

    # Create asset with dividend
    asset = AssetORM(
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        start_date=date(2020, 1, 1),
        simulation_ids=[sample_simulation.id],
        monthly_data=[
            {
                "date": "2023-01-01",
                "open": "150.00",
                "high": "155.00",
                "low": "148.00",
                "close": "152.00",
                "dividends": "0.24",  # Dividend this month
                "splits": None
            },
            {
                "date": "2023-02-01",
                "open": "152.00",
                "high": "160.00",
                "low": "151.00",
                "close": "158.00",
                "dividends": None,
                "splits": None
            }
        ]
    )
    db_session.add(asset)

    # Create holding
    holding = HoldingORM(
        simulation_id=sample_simulation.id,
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        quantity="10.0",
        purchase_price="150.00",
        weight="100",
        current_price="152.00",
        market_value="1520.00"
    )
    db_session.add(holding)
    db_session.commit()

    return sample_simulation


def test_advance_month_basic(db_session, simulation_with_holdings):
    """Test basic month advancement."""
    sim = simulation_with_holdings
    initial_date = sim.current_date

    # Advance
    report = advance_month_service(db_session, sim.id)

    # Check date advanced
    assert report.previous_date == initial_date
    assert report.new_date == date(2023, 2, 1)

    # Verify in DB
    db_session.refresh(sim)
    assert sim.current_date == date(2023, 2, 1)


def test_advance_month_pays_dividends(db_session, simulation_with_holdings):
    """Test that dividends are paid during advancement."""
    sim = simulation_with_holdings
    initial_balance = Decimal(sim.balance)

    # Advance (should pay 10 shares * 0.24 = 2.40 dividend)
    report = advance_month_service(db_session, sim.id)

    # Check dividends paid
    assert len(report.dividends_received) == 1
    assert report.dividends_received[0]["ticker"] == "AAPL"
    assert Decimal(report.dividends_received[0]["total"]) == Decimal("2.40")
    assert report.total_dividends == Decimal("2.40")

    # Check balance increased
    assert report.new_balance == initial_balance + Decimal("2.40")


def test_advance_month_updates_prices(db_session, simulation_with_holdings):
    """Test that prices are updated during advancement."""
    # Advance
    report = advance_month_service(db_session, simulation_with_holdings.id)

    # Check price updates
    assert len(report.price_updates) == 1
    price_update = report.price_updates[0]

    assert price_update["ticker"] == "AAPL"
    assert Decimal(price_update["old_price"]) == Decimal("152.00")
    assert Decimal(price_update["new_price"]) == Decimal("158.00")
    assert Decimal(price_update["change"]) == Decimal("6.00")


def test_advance_month_creates_snapshot(db_session, simulation_with_holdings):
    """Test that snapshot is created before advancing."""
    from src.backend.models.monthly_snapshot import MonthlySnapshotORM

    # No snapshot initially
    snapshot_before = db_session.query(MonthlySnapshotORM).filter(
        MonthlySnapshotORM.simulation_id == simulation_with_holdings.id
    ).first()
    assert snapshot_before is None

    # Advance
    advance_month_service(db_session, simulation_with_holdings.id)

    # Snapshot should exist
    snapshot_after = db_session.query(MonthlySnapshotORM).filter(
        MonthlySnapshotORM.simulation_id == simulation_with_holdings.id
    ).first()
    assert snapshot_after is not None
    assert snapshot_after.month_date == date(2023, 1, 1)  # Snapshot of previous month


def test_can_advance_month(db_session, simulation_with_holdings):
    """Test checking if month can be advanced."""
    result = can_advance_month(db_session, simulation_with_holdings.id)

    assert result["can_advance"] is True
    assert result["next_month"] == "2023-02-01"
    assert result["holdings_count"] == 1


def test_cannot_advance_beyond_present(db_session, sample_simulation):
    """Test that cannot advance beyond current real date."""
    # Set simulation to current month
    sample_simulation.current_date = date.today().replace(day=1)
    db_session.commit()

    result = can_advance_month(db_session, sample_simulation.id)

    assert result["can_advance"] is False
    assert "current month" in result["reason"]


def test_advance_multiple_months(db_session, simulation_with_holdings):
    """Test advancing multiple months in sequence."""
    sim = simulation_with_holdings

    # Advance first month
    report1 = advance_month_service(db_session, sim.id)
    assert report1.new_date == date(2023, 2, 1)

    # Note: Would need more monthly_data in asset to advance again
    # This tests the basic flow