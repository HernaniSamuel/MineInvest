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


from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from src.backend.models.simulation import SimulationORM
from src.backend.models.holding import HoldingORM
from src.backend.models.history_month import HistoryMonthORM
from src.backend.models.asset import AssetORM
from src.backend.schemas.simulation import SimulationCreate
from src.backend.services.exceptions import SimulationAlreadyExistsError, SimulationNotFoundError


def create_simulation_service(db: Session, simulation: SimulationCreate) -> SimulationORM:
    """
    Creates a new simulation in the database.

    Args:
        db: SQLAlchemy database session
        simulation: Validated simulation created data

    Returns:
        SimulationORM: The created simulation object

    Raises:
        SimulationAlreadyExistsError: If a simulation with the same name already exists
        ValueError: If validation fails

    Business Rules:
        - Simulation name must be unique (case-insensitive check)
        - Balance starts at 0
        - current_date equals start_date initially
        - No holdings or history created yet (empty relationships)
    """
    # Check if simulation name already exists (case-insensitive)
    existing_sim = db.query(SimulationORM).filter(
        SimulationORM.name.ilike(simulation.name.strip())
    ).first()

    if existing_sim:
        raise SimulationAlreadyExistsError(
            f"A simulation named '{simulation.name}' already exists with ID {existing_sim.id}"
        )

    # Create new simulation
    db_sim = SimulationORM(
        name=simulation.name.strip(),
        start_date=simulation.start_date,
        base_currency=simulation.base_currency.upper(),
        balance=str("0.0000000000000000"), # 16 zeros after point
        current_date=simulation.start_date
    )

    try:
        db.add(db_sim)
        db.commit()
        db.refresh(db_sim)
        return db_sim
    except IntegrityError as e:
        db.rollback()
        # Handle race condition where another request created same name simultaneously
        raise SimulationAlreadyExistsError(
            f"A simulation named '{simulation.name}' already exists"
        ) from e


def list_simulations_service(
        db: Session,
        skip: int = 0,
        limit: int = 100
) -> List[SimulationORM]:
    """
    Retrieves all simulations with pagination.

    Args:
        db: SQLAlchemy database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return

    Returns:
        List[SimulationORM]: List of simulation objects ordered by creation (newest first)

    Note:
        - Returns simulations ordered by ID descending (newest first)
        - Includes basic relationships (holdings count via len())
    """
    # noinspection PyTypeChecker
    return (
        db.query(SimulationORM)
        .order_by(SimulationORM.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def delete_simulation_service(db: Session, simulation_id: int) -> None:
    """
    Delete a simulation and clean up associated data.

    Cleanup process:
    1. Find simulation
    2. Get all owned tickers
    3. Delete simulation (cascades to holdings and history via SQLAlchemy)
    4. Remove simulation_id from each asset's simulation_ids list
    5. Delete orphaned assets (assets with empty simulation_ids)

    Args:
        db: Database session
        simulation_id: ID of simulation to delete

    Raises:
        SimulationNotFoundError: If simulation doesn't exist
    """
    # 1. Find simulation
    simulation = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not simulation:
        raise SimulationNotFoundError(
            f"Simulation with ID {simulation_id} not found"
        )

    # 2. Delete simulation (cascades delete holdings and history automatically)
    db.delete(simulation)
    db.flush()  # Execute delete but don't commit yet

    # 3. Find all assets that reference this simulation
    # Use SQL query since JSON filtering varies by database
    all_assets = db.query(AssetORM).all()

    for asset in all_assets:
        if simulation_id in asset.simulation_ids:
            # Remove this simulation from asset's ownership list
            asset.simulation_ids.remove(simulation_id)
            flag_modified(asset, "simulation_ids")

            # Delete asset if no simulations own it anymore
            if not asset.simulation_ids:
                db.delete(asset)

    db.commit()


def get_simulation_by_id_service(db: Session, simulation_id: int) -> SimulationORM:
    """
    Retrieve a simulation by ID.

    Args:
        db: Database session
        simulation_id: Simulation ID

    Returns:
        SimulationORM object

    Raises:
        SimulationNotFoundError: If not found
    """
    simulation = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not simulation:
        raise SimulationNotFoundError(
            f"Simulation with ID {simulation_id} not found"
        )

    # noinspection PyTypeChecker
    return simulation
