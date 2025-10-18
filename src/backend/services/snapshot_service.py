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
    - BEFORE advancing to a new month (for undo capability)
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
    1. Restore current_date to snapshot date
    2. Restore balance to snapshot value
    3. Delete all current holdings
    4. Recreate holdings from snapshot
    5. Delete ALL history for the month AFTER snapshot (including dividends)

    The snapshot represents the state BEFORE advancing the month,
    so restoring it will undo all operations from the advancement.

    WARNING: This cannot be undone! All operations after the snapshot
    will be lost, including dividends received.

    Args:
        db: Database session
        simulation_id: Target simulation

    Returns:
        Restored simulation

    Raises:
        SimulationNotFoundError: If simulation doesn't exist
        ValueError: If no snapshot exists or invalid state
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

    print(f"\n{'=' * 60}")
    print(f"🔄 RESTORING FROM SNAPSHOT")
    print(f"📅 Current date: {sim.current_date}")
    print(f"📅 Snapshot date: {snapshot.month_date}")
    print(f"💰 Current balance: {sim.balance}")
    print(f"💰 Snapshot balance: {snapshot.balance}")
    print(f"{'=' * 60}\n")

    # Validate snapshot is not from the future
    if snapshot.month_date > sim.current_date:
        raise ValueError(
            f"Snapshot is from the future ({snapshot.month_date}), "
            f"but current date is {sim.current_date}. Cannot restore."
        )

    # 1. Restore date to snapshot date
    sim.current_date = snapshot.month_date
    print(f"✅ Date restored to: {sim.current_date}")

    # 2. Restore balance
    sim.balance = snapshot.balance
    print(f"✅ Balance restored to: {sim.balance}")

    # 3. Delete all current holdings
    deleted_holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).delete()
    print(f"✅ Deleted {deleted_holdings} current holdings")
    db.flush()

    # 4. Recreate holdings from snapshot
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
    print(f"✅ Recreated {len(snapshot.holdings_snapshot)} holdings from snapshot")

    # 5. Delete ALL history entries AFTER snapshot date (INCLUDING the snapshot month)
    deleted_history = db.query(HistoryMonthORM).filter(
        HistoryMonthORM.simulation_id == simulation_id,
        HistoryMonthORM.month_date >= snapshot.month_date  # >= ao invés de >
    ).delete()

    if deleted_history > 0:
        print(f"✅ Deleted {deleted_history} history entries from snapshot month onwards")
    db.commit()
    db.refresh(sim)

    print(f"\n{'=' * 60}")
    print(f"✅ RESTORE COMPLETE")
    print(f"📅 Final date: {sim.current_date}")
    print(f"💰 Final balance: {sim.balance}")
    print(f"{'=' * 60}\n")

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

    sim = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not sim:
        return None

    # Can restore if snapshot date is before or equal to current date
    # (usually it will be one month before after an advancement)
    can_restore = snapshot.month_date <= sim.current_date

    return {
        "exists": True,
        "month_date": snapshot.month_date.isoformat(),
        "balance": snapshot.balance,
        "holdings_count": len(snapshot.holdings_snapshot),
        "can_restore": can_restore,
        "current_date": sim.current_date.isoformat()
    }