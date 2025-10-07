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


# Delete simulation
def test_delete_simulation_success(db_session, sample_simulation):
    """Test successful simulation deletion."""
    sim_id = sample_simulation.id

    # Verify simulation exists
    sim = db_session.query(SimulationORM).filter(SimulationORM.id == sim_id).first()
    assert sim is not None

    # Delete it
    delete_simulation_service(db_session, sim_id)

    # Verify it's gone
    sim = db_session.query(SimulationORM).filter(SimulationORM.id == sim_id).first()
    assert sim is None


def test_delete_simulation_cascades_to_holdings(db_session, sample_simulation):
    """Test that deleting simulation also deletes holdings."""
    # Create a holding
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

    # Verify holding exists
    holdings = db_session.query(HoldingORM).filter(
        HoldingORM.simulation_id == sample_simulation.id
    ).all()
    assert len(holdings) == 1

    # Delete simulation
    delete_simulation_service(db_session, sample_simulation.id)

    # Verify holdings are gone
    holdings = db_session.query(HoldingORM).filter(
        HoldingORM.simulation_id == sample_simulation.id
    ).all()
    assert len(holdings) == 0


def test_delete_simulation_cascades_to_history(db_session, sample_simulation):
    """Test that deleting simulation also deletes history."""
    # Create history entry
    history = HistoryMonthORM(
        simulation_id=sample_simulation.id,
        month_date=date(2023, 1, 1),
        operations=[{"type": "contribution", "amount": "100.00", "ticker": None}],
        total="100.00"
    )
    db_session.add(history)
    db_session.commit()

    # Verify history exists
    hist = db_session.query(HistoryMonthORM).filter(
        HistoryMonthORM.simulation_id == sample_simulation.id
    ).all()
    assert len(hist) == 1

    # Delete simulation
    delete_simulation_service(db_session, sample_simulation.id)

    # Verify history is gone
    hist = db_session.query(HistoryMonthORM).filter(
        HistoryMonthORM.simulation_id == sample_simulation.id
    ).all()
    assert len(hist) == 0


def test_delete_simulation_removes_from_asset_ownership(db_session, sample_simulation):
    """Test that deleting simulation removes it from asset ownership."""
    # Create asset owned by simulation
    asset = AssetORM(
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        start_date=date(2000, 1, 1),
        simulation_ids=[sample_simulation.id],
        monthly_data=[]
    )
    db_session.add(asset)
    db_session.commit()

    # Verify asset lists simulation as owner
    asset = db_session.query(AssetORM).filter(AssetORM.ticker == "AAPL").first()
    assert sample_simulation.id in asset.simulation_ids

    # Delete simulation
    delete_simulation_service(db_session, sample_simulation.id)

    # Verify simulation removed from ownership
    asset = db_session.query(AssetORM).filter(AssetORM.ticker == "AAPL").first()
    # Asset should be deleted entirely (orphaned)
    assert asset is None


def test_delete_simulation_keeps_asset_if_other_owners(db_session):
    """Test that asset remains if other simulations own it."""
    # Create two simulations
    from src.backend.schemas.simulation import SimulationCreate

    sim1_data = SimulationCreate(
        name="Simulation 1",
        start_date=date(2023, 1, 1),
        base_currency="BRL"
    )
    sim1 = create_simulation_service(db_session, sim1_data)

    sim2_data = SimulationCreate(
        name="Simulation 2",
        start_date=date(2023, 1, 1),
        base_currency="BRL"
    )
    sim2 = create_simulation_service(db_session, sim2_data)

    # Create asset owned by both
    asset = AssetORM(
        ticker="AAPL",
        name="Apple Inc.",
        base_currency="USD",
        start_date=date(2000, 1, 1),
        simulation_ids=[sim1.id, sim2.id],
        monthly_data=[]
    )
    db_session.add(asset)
    db_session.commit()

    # Delete first simulation
    delete_simulation_service(db_session, sim1.id)

    # Asset should still exist, owned only by sim2
    asset = db_session.query(AssetORM).filter(AssetORM.ticker == "AAPL").first()
    assert asset is not None
    assert sim1.id not in asset.simulation_ids
    assert sim2.id in asset.simulation_ids


def test_delete_nonexistent_simulation_fails(db_session):
    """Test that deleting nonexistent simulation raises error."""
    with pytest.raises(SimulationNotFoundError) as exc_info:
        delete_simulation_service(db_session, 99999)

    assert "not found" in str(exc_info.value)


def test_delete_simulation_idempotent(db_session, sample_simulation):
    """Test that deleting twice raises appropriate error."""
    sim_id = sample_simulation.id

    # First delete succeeds
    delete_simulation_service(db_session, sim_id)

    # Second delete fails
    with pytest.raises(SimulationNotFoundError):
        delete_simulation_service(db_session, sim_id)