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
from sqlalchemy.exc import IntegrityError
from datetime import date
from decimal import Decimal
from typing import List, Optional, cast

from src.backend.models.simulation import SimulationORM
from src.backend.schemas.simulation import SimulationCreate
from src.backend.services.exceptions import SimulationAlreadyExistsError


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

def get_simulation_by_id_service(db: Session, simulation_id: int) -> Optional[SimulationORM]:
    """
    Retrieves a single simulation by ID.

    Args:
        db: SQLAlchemy database session
        simulation_id: ID of the simulation to retrieve

    Returns:
        SimulationORM if found, None otherwise
    """
    return db.query(SimulationORM).filter(SimulationORM.id == simulation_id).first()


def get_simulation_by_name_service(db: Session, name: str) -> Optional[SimulationORM]:
    """
    Retrieves a single simulation by name (case-insensitive).

    Args:
        db: SQLAlchemy database session
        name: Name of the simulation to retrieve

    Returns:
        SimulationORM if found, None otherwise
    """
    return db.query(SimulationORM).filter(SimulationORM.name.ilike(name.strip())).first()