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
from decimal import Decimal

from src.backend.models.simulation import SimulationORM
from src.backend.models.history_month import HistoryMonthORM
from src.backend.schemas.history_month import SimulationHistoryRead, HistoryMonthRead
from src.backend.services.exceptions import SimulationNotFoundError


def get_simulation_history_service(db: Session, simulation_id: int) -> SimulationHistoryRead:
    """
    Retrieve complete transaction history for a simulation.

    Returns all monthly history records ordered chronologically.

    Args:
        db: Database session
        simulation_id: Target simulation ID

    Returns:
        SimulationHistoryRead with all monthly records

    Raises:
        SimulationNotFoundError: If simulation doesn't exist
    """
    # Get simulation
    simulation = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not simulation:
        raise SimulationNotFoundError(
            f"Simulation with ID {simulation_id} not found"
        )

    # Get all history records, ordered by date
    history_records = db.query(HistoryMonthORM).filter(
        HistoryMonthORM.simulation_id == simulation_id
    ).order_by(HistoryMonthORM.month_date).all()

    # Convert to HistoryMonthRead using from_attributes
    months = [
        HistoryMonthRead(
            id=record.id,
            month_date=record.month_date,
            operations=record.operations,  # Already a list of dicts
            total=Decimal(record.total),  # Convert string to Decimal
            simulation_id=record.simulation_id
        )
        for record in history_records
    ]

    return SimulationHistoryRead(
        simulation_id=simulation.id,
        simulation_name=simulation.name,
        start_date=simulation.start_date,
        current_date=simulation.current_date,
        months=months
    )