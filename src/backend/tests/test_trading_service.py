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
from unittest.mock import patch, MagicMock

from src.backend.schemas.trading import PurchaseRequest, SellRequest
from src.backend.services.trading_service import (
    purchase_asset_service,
    sell_asset_service
)
from src.backend.services.exceptions import (
    InsufficientFundsError,
    InsufficientPositionError,
    AssetNotFoundError
)
from src.backend.services.asset_cache import AssetData

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.models.base import Base

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
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
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


@pytest.fixture
def mock_asset():
    """Mock asset data."""
    return AssetData(
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        start_date=date(2000, 1, 1),
        monthly_data=[
            {
                "date": "2023-01-01",
                "open": "100.00",
                "high": "105.00",
                "low": "99.00",
                "close": "102.50",
                "dividends": None,
                "splits": None
            }
        ]
    )


def test_purchase_asset_success(db_session, sample_simulation, mock_asset):
    """Test successful asset purchase."""
    # Add balance first
    from src.backend.schemas.balance import BalanceOperationRequest
    from src.backend.schemas.enums import Operation
    from src.backend.services.balance_service import handle_balance_service

    balance_req = BalanceOperationRequest(
        amount=Decimal("1000.00"),
        operation=Operation.ADD,
        category="contribution"
    )
    handle_balance_service(db_session, sample_simulation.id, balance_req)

    # Mock asset search
    with patch('src.backend.services.asset_service.AssetService.search_asset', return_value=mock_asset):
        with patch('src.backend.services.asset_service.AssetService.get_price_at_date', return_value=Decimal("102.50")):
            with patch('src.backend.services.asset_service.AssetService.persist_to_database'):
                purchase_req = PurchaseRequest(
                    ticker="AAPL",
                    desired_amount=Decimal("500.00")
                )

                result = purchase_asset_service(db_session, sample_simulation.id, purchase_req)

                # Check balance deducted
                assert Decimal(result.balance) == Decimal("500.00")

                # Check holding created
                from src.backend.models.holding import HoldingORM
                holding = db_session.query(HoldingORM).filter(
                    HoldingORM.simulation_id == sample_simulation.id,
                    HoldingORM.ticker == "AAPL"
                ).first()

                assert holding is not None
                assert Decimal(holding.quantity) == Decimal("500.00") / Decimal("102.50")
                assert holding.purchase_price == "102.50"


def test_purchase_insufficient_funds(db_session, sample_simulation, mock_asset):
    """Test purchase fails with insufficient funds."""
    with patch('src.backend.services.asset_service.AssetService.search_asset', return_value=mock_asset):
        purchase_req = PurchaseRequest(
            ticker="AAPL",
            desired_amount=Decimal("1000.00")
        )

        with pytest.raises(InsufficientFundsError):
            purchase_asset_service(db_session, sample_simulation.id, purchase_req)


def test_sell_asset_success(db_session, sample_simulation, mock_asset):
    """Test successful asset sale."""
    # Setup: buy first
    from src.backend.models.holding import HoldingORM
    from src.backend.schemas.balance import BalanceOperationRequest
    from src.backend.schemas.enums import Operation
    from src.backend.services.balance_service import handle_balance_service

    # Add balance
    balance_req = BalanceOperationRequest(
        amount=Decimal("1000.00"),
        operation=Operation.ADD,
        category="contribution"
    )
    handle_balance_service(db_session, sample_simulation.id, balance_req)

    # Create holding manually
    holding = HoldingORM(
        simulation_id=sample_simulation.id,
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        quantity="10.0",
        purchase_price="100.00",
        weight="0",
        current_price="102.50",
        market_value="1025.00"
    )
    db_session.add(holding)
    db_session.commit()

    # Mock asset search
    with patch('src.backend.services.asset_service.AssetService.search_asset', return_value=mock_asset):
        with patch('src.backend.services.asset_service.AssetService.get_price_at_date', return_value=Decimal("102.50")):
            with patch('src.backend.services.asset_service.AssetService.remove_from_database_if_orphaned'):
                sell_req = SellRequest(
                    ticker="AAPL",
                    desired_amount=Decimal("500.00")
                )

                result = sell_asset_service(db_session, sample_simulation.id, sell_req)

                # Check balance increased
                assert Decimal(result.balance) > Decimal("1000.00")

                # Check holding updated (partial sale)
                holding = db_session.query(HoldingORM).filter(
                    HoldingORM.simulation_id == sample_simulation.id,
                    HoldingORM.ticker == "AAPL"
                ).first()

                assert holding is not None
                assert Decimal(holding.quantity) < Decimal("10.0")


def test_sell_insufficient_position(db_session, sample_simulation, mock_asset):
    """Test sale fails when trying to sell more than owned."""
    # Create small holding
    from src.backend.models.holding import HoldingORM

    holding = HoldingORM(
        simulation_id=sample_simulation.id,
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        quantity="1.0",
        purchase_price="100.00",
        weight="0",
        current_price="102.50",
        market_value="102.50"
    )
    db_session.add(holding)
    db_session.commit()

    with patch('src.backend.services.asset_service.AssetService.search_asset', return_value=mock_asset):
        with patch('src.backend.services.asset_service.AssetService.get_price_at_date', return_value=Decimal("102.50")):
            sell_req = SellRequest(
                ticker="AAPL",
                desired_amount=Decimal("500.00")  # More than market value
            )

            with pytest.raises(InsufficientPositionError):
                sell_asset_service(db_session, sample_simulation.id, sell_req)
