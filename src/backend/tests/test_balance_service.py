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


def test_contribution_without_ticker(db_session, sample_simulation):
    """Test contribution doesn't require ticker."""
    request = BalanceOperationRequest(
        amount=Decimal("1000.50"),
        operation=Operation.ADD,
        category="contribution"
    )

    result = handle_balance_service(db_session, sample_simulation.id, request)
    assert Decimal(result.balance) == Decimal("1000.50")


def test_dividend_with_high_precision(db_session, sample_simulation):
    """Test dividend allows more than 2 decimal places."""
    request = BalanceOperationRequest(
        amount=Decimal("0.012345678"),
        operation=Operation.ADD,
        category="dividend",
        ticker="PETR4"
    )

    result = handle_balance_service(db_session, sample_simulation.id, request)

    # Convert string to Decimal for comparison
    assert Decimal(result.balance) == Decimal("0.012345678")

    # Verify history logged correctly
    history = db_session.query(HistoryMonthORM).filter(
        HistoryMonthORM.simulation_id == sample_simulation.id
    ).first()

    assert history.operations[0]["ticker"] == "PETR4"
    assert Decimal(history.operations[0]["amount"]) == Decimal("0.012345678")

def test_dividend_requires_ticker(db_session, sample_simulation):
    """Test dividend without ticker fails validation."""
    with pytest.raises(ValueError) as exc_info:
        BalanceOperationRequest(
            amount=Decimal("0.50"),
            operation=Operation.ADD,
            category="dividend"
            # Missing ticker
        )

    assert "requires a ticker" in str(exc_info.value)


def test_purchase_requires_ticker(db_session, sample_simulation):
    """Test purchase without ticker fails validation."""
    with pytest.raises(ValueError) as exc_info:
        BalanceOperationRequest(
            amount=Decimal("1000.00"),
            operation=Operation.REMOVE,
            category="purchase"
            # Missing ticker
        )

    assert "requires a ticker" in str(exc_info.value)


def test_contribution_rejects_ticker(db_session, sample_simulation):
    """Test contribution with ticker fails validation."""
    with pytest.raises(ValueError) as exc_info:
        BalanceOperationRequest(
            amount=Decimal("1000.00"),
            operation=Operation.ADD,
            category="contribution",
            ticker="PETR4" # Should not have ticker
        )

    assert "should not have a ticker" in str(exc_info.value)


def test_contribution_rejects_excessive_decimals(db_session, sample_simulation):
    """Test non-dividend categories reject >2 decimals."""
    with pytest.raises(ValueError) as exc_info:
        BalanceOperationRequest(
            amount=Decimal("1000.123"),
            operation=Operation.ADD,
            category="contribution",
        )

    assert "exactly 2 decimal places" in str(exc_info.value)


def test_history_month_creation(db_session, sample_simulation):
    """Test HistoryMonth is created automatically."""
    request = BalanceOperationRequest(
        amount=Decimal("500.00"),
        operation=Operation.ADD,
        category="contribution",
    )

    handle_balance_service(db_session, sample_simulation.id, request)

    # Check if history was created
    history = db_session.query(HistoryMonthORM).filter(
        HistoryMonthORM.simulation_id == sample_simulation.id,
        HistoryMonthORM.month_date == sample_simulation.current_date
    ).first()

    assert history is not None
    assert len(history.operations) == 1
    assert Decimal(history.total) == Decimal("500.00")


def test_multiple_operations_same_month(db_session, sample_simulation):
    """Test multiple operations accumulate in same HistoryMonth."""
    requests = [
        BalanceOperationRequest(
            amount=Decimal("1000.00"),
            operation=Operation.ADD,
            category="contribution"
        ),
        BalanceOperationRequest(
            amount=Decimal("0.05"),
            operation=Operation.ADD,
            category="dividend",
            ticker="PETR4"
        ),
        BalanceOperationRequest(
            amount=Decimal("200.00"),
            operation=Operation.REMOVE,
            category="withdrawal"
        ),
    ]

    for req in requests:
        handle_balance_service(db_session, sample_simulation.id, req)

    # Should have one HistoryMonth with 3 operations
    history = db_session.query(HistoryMonthORM).filter(
        HistoryMonthORM.simulation_id == sample_simulation.id
    ).first()

    assert len(history.operations) == 3
    assert Decimal(history.total) == Decimal("800.05") # 1000 + 0.05 - 200


def test_invalid_category(db_session, sample_simulation):
    """Test invalid category is rejected."""
    with pytest.raises(ValueError) as exc_info:
        BalanceOperationRequest(
            amount=Decimal("100.00"),
            operation=Operation.ADD,
            category="invalid_category"
        )

    assert "Invalid category" in str(exc_info.value)

