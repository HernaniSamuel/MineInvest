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
from src.backend.models.holding import HoldingORM
from src.backend.models.monthly_snapshot import MonthlySnapshotORM
from src.backend.models.history_month import HistoryMonthORM
from src.backend.services.exceptions import SimulationNotFoundError


def create_monthly_snapshot(db: Session, simulation_id: int) -> MonthlySnapshotORM:
    """
    Create a snapshot of the current simulation state.

    Captures:
    - Current balance
    - All holdings (quantity, purchase_price, etc.)
    - Current month date

    Should be called:
    - When advancing to a new month
    - Manually before risky operations

    Only keeps ONE snapshot per simulation (the most recent).

    Args:
        db: Database session
        simulation_id: Target simulation

    Returns:
        Created snapshot

    Raises:
        SimulationNotFoundError: If simulation doesn't exist
    """
    # Get simulation
    sim = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not sim:
        raise SimulationNotFoundError(f"Simulation {simulation_id} not found")

    # Get current holdings
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    # Serialize holdings
    holdings_snapshot = [
        {
            "ticker": h.ticker,
            "name": h.name,
            "base_currency": h.base_currency,
            "quantity": h.quantity,
            "purchase_price": h.purchase_price,
            "weight": h.weight,
            "current_price": h.current_price,
            "market_value": h.market_value
        }
        for h in holdings
    ]

    # Delete existing snapshot for this simulation (keep only latest)
    db.query(MonthlySnapshotORM).filter(
        MonthlySnapshotORM.simulation_id == simulation_id
    ).delete()

    # Create new snapshot
    snapshot = MonthlySnapshotORM(
        simulation_id=simulation_id,
        month_date=sim.current_date,
        balance=sim.balance,
        holdings_snapshot=holdings_snapshot
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return snapshot


def restore_from_snapshot(db: Session, simulation_id: int) -> SimulationORM:
    """
    Restore simulation to the state of the most recent snapshot.

    This will:
    1. Restore balance to snapshot value
    2. Delete all current holdings
    3. Recreate holdings from snapshot
    4. Clear current month's history (except dividends)
    5. Keep the snapshot for potential re-restore

    WARNING: This cannot be undone! All operations in the current
    month will be lost (except dividends which are kept).

    Args:
        db: Database session
        simulation_id: Target simulation

    Returns:
        Restored simulation

    Raises:
        SimulationNotFoundError: If simulation doesn't exist
        ValueError: If no snapshot exists
    """
    # Get simulation
    sim = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not sim:
        raise SimulationNotFoundError(f"Simulation {simulation_id} not found")

    # Get snapshot
    snapshot = db.query(MonthlySnapshotORM).filter(
        MonthlySnapshotORM.simulation_id == simulation_id
    ).first()

    if not snapshot:
        raise ValueError(
            f"No snapshot exists for simulation {simulation_id}. "
            "Cannot restore without a snapshot."
        )

    # Check if snapshot is for current month
    if snapshot.month_date != sim.current_date:
        raise ValueError(
            f"Snapshot is for {snapshot.month_date}, but current month is {sim.current_date}. "
            "Can only restore within the same month."
        )

    # 1. Restore balance
    sim.balance = snapshot.balance

    # 2. Delete all current holdings
    db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).delete()
    db.flush()

    # 3. Recreate holdings from snapshot
    for h_data in snapshot.holdings_snapshot:
        holding = HoldingORM(
            simulation_id=simulation_id,
            ticker=h_data["ticker"],
            name=h_data["name"],
            base_currency=h_data["base_currency"],
            quantity=h_data["quantity"],
            purchase_price=h_data["purchase_price"],
            weight=h_data["weight"],
            current_price=h_data["current_price"],
            market_value=h_data["market_value"]
        )
        db.add(holding)

    # 4. Clear current month's history (except dividends)
    history = db.query(HistoryMonthORM).filter(
        HistoryMonthORM.simulation_id == simulation_id,
        HistoryMonthORM.month_date == sim.current_date
    ).first()

    if history:
        # Keep only dividend operations
        dividend_ops = [
            op for op in history.operations
            if op["type"] == "dividend"
        ]

        if dividend_ops:
            # Recalculate total from dividends only
            dividend_total = sum(Decimal(op["amount"]) for op in dividend_ops)
            snapshot_balance = Decimal(snapshot.balance)

            # ✅ FIX: Update simulation balance to include dividends
            new_balance = snapshot_balance + dividend_total
            sim.balance = str(new_balance)

            history.operations = dividend_ops
            history.total = str(new_balance)
        else:
            # No dividends - delete history entry
            db.delete(history)

    db.commit()
    db.refresh(sim)

    return sim


def get_snapshot_info(db: Session, simulation_id: int) -> dict:
    """
    Get information about the current snapshot.

    Returns:
        Dictionary with snapshot details or None if no snapshot exists
    """
    snapshot = db.query(MonthlySnapshotORM).filter(
        MonthlySnapshotORM.simulation_id == simulation_id
    ).first()

    if not snapshot:
        return None

    return {
        "exists": True,
        "month_date": snapshot.month_date.isoformat(),
        "balance": snapshot.balance,
        "holdings_count": len(snapshot.holdings_snapshot),
        "can_restore": snapshot.month_date == db.query(SimulationORM).filter(
            SimulationORM.id == simulation_id
        ).first().current_date
    }