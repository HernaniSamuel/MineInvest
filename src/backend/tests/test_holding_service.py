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
from unittest.mock import patch

from src.backend.services.holding_service import (
    update_holdings_attributes,
    get_holdings_summary
)
from src.backend.services.asset_cache import AssetData
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


@pytest.fixture
def mock_asset_aapl():
    return AssetData(
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        start_date=date(2000, 1, 1),
        monthly_data=[
            {"date": "2023-01-01", "close": "150.00"}
        ]
    )


@pytest.fixture
def mock_asset_msft():
    return AssetData(
        ticker="MSFT",
        name="Microsoft Corp.",
        base_currency="USD",
        start_date=date(2000, 1, 1),
        monthly_data=[
            {"date": "2023-01-01", "close": "300.00"}
        ]
    )


def test_update_holdings_attributes(db_session, sample_simulation, mock_asset_aapl):
    """Test updating holding attributes."""
    # Create holdings
    holding1 = HoldingORM(
        simulation_id=sample_simulation.id,
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        quantity="10.0",
        purchase_price="100.00",
        weight="0",
        current_price="100.00",
        market_value="1000.00"
    )
    db_session.add(holding1)
    db_session.commit()

    # Mock asset search
    with patch('src.backend.services.asset_service.AssetService.search_asset', return_value=mock_asset_aapl):
        with patch('src.backend.services.asset_service.AssetService.get_price_at_date', return_value=Decimal("150.00")):
            holdings = update_holdings_attributes(db_session, sample_simulation.id)

            # Check updated values
            assert len(holdings) == 1
            assert Decimal(holdings[0].current_price) == Decimal("150.00")
            assert Decimal(holdings[0].market_value) == Decimal("1500.00")
            assert Decimal(holdings[0].weight) == Decimal("100.00")  # 100% of portfolio


def test_update_holdings_calculates_weights(db_session, sample_simulation, mock_asset_aapl, mock_asset_msft):
    """Test portfolio weight calculation with multiple holdings."""
    # Create two holdings
    holding1 = HoldingORM(
        simulation_id=sample_simulation.id,
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        quantity="10.0",
        purchase_price="100.00",
        weight="0",
        current_price="100.00",
        market_value="1000.00"
    )
    holding2 = HoldingORM(
        simulation_id=sample_simulation.id,
        ticker="MSFT",
        name="Microsoft Corp.",
        base_currency="USD",
        quantity="5.0",
        purchase_price="200.00",
        weight="0",
        current_price="200.00",
        market_value="1000.00"
    )
    db_session.add_all([holding1, holding2])
    db_session.commit()

    # Mock searches
    def mock_search(db, ticker, sim_id):
        return mock_asset_aapl if ticker == "AAPL" else mock_asset_msft

    def mock_price(asset, target_date):
        return Decimal("150.00") if asset.ticker == "AAPL" else Decimal("300.00")

    with patch('src.backend.services.asset_service.AssetService.search_asset', side_effect=mock_search):
        with patch('src.backend.services.asset_service.AssetService.get_price_at_date', side_effect=mock_price):
            holdings = update_holdings_attributes(db_session, sample_simulation.id)

            # AAPL: 10 * 150 = 1500
            # MSFT: 5 * 300 = 1500
            # Total = 3000
            # Each weight = 50%

            aapl = next(h for h in holdings if h.ticker == "AAPL")
            msft = next(h for h in holdings if h.ticker == "MSFT")

            assert Decimal(aapl.market_value) == Decimal("1500.00")
            assert Decimal(msft.market_value) == Decimal("1500.00")
            assert Decimal(aapl.weight) == Decimal("50.00")
            assert Decimal(msft.weight) == Decimal("50.00")


def test_get_holdings_summary(db_session, sample_simulation):
    """Test portfolio summary calculation."""
    # Create holdings with profit and loss
    holding1 = HoldingORM(
        simulation_id=sample_simulation.id,
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        quantity="10.0",
        purchase_price="100.00",  # Bought at 100
        weight="50",
        current_price="150.00",  # Now worth 150
        market_value="1500.00"  # Profit: 500
    )
    holding2 = HoldingORM(
        simulation_id=sample_simulation.id,
        ticker="MSFT",
        name="Microsoft Corp.",
        base_currency="USD",
        quantity="10.0",
        purchase_price="200.00",  # Bought at 200
        weight="50",
        current_price="180.00",  # Now worth 180
        market_value="1800.00"  # Loss: 200
    )
    db_session.add_all([holding1, holding2])
    db_session.commit()

    summary = get_holdings_summary(db_session, sample_simulation.id)

    # Total invested: (10*100) + (10*200) = 3000
    # Total market: 1500 + 1800 = 3300
    # Gain: 300
    # Percentage: 10%

    assert summary["total_holdings"] == 2
    assert Decimal(summary["total_market_value"]) == Decimal("3300.00")
    assert Decimal(summary["total_invested"]) == Decimal("3000.00")
    assert Decimal(summary["total_gain_loss"]) == Decimal("300.00")
    assert Decimal(summary["gain_loss_percentage"]) == Decimal("10.00")


def test_empty_portfolio_summary(db_session, sample_simulation):
    """Test summary with no holdings."""
    summary = get_holdings_summary(db_session, sample_simulation.id)

    assert summary["total_holdings"] == 0
    assert summary["total_market_value"] == "0.00"