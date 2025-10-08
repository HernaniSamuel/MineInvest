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
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import Dict, List

from src.backend.models.simulation import SimulationORM
from src.backend.models.holding import HoldingORM
from src.backend.models.asset import AssetORM
from src.backend.schemas.balance import BalanceOperationRequest
from src.backend.schemas.enums import Operation
from src.backend.services.snapshot_service import create_monthly_snapshot
from src.backend.services.balance_service import handle_balance_service
from src.backend.services.holding_service import update_holdings_attributes
from src.backend.services.asset_service import AssetService
from src.backend.services.exceptions import SimulationNotFoundError


class MonthAdvancementReport:
    """Report of what happened during month advancement."""

    def __init__(self):
        self.dividends_received: List[Dict] = []
        self.price_updates: List[Dict] = []
        self.total_dividends: Decimal = Decimal('0')
        self.previous_date: date = None
        self.new_date: date = None
        self.previous_balance: Decimal = Decimal('0')
        self.new_balance: Decimal = Decimal('0')
        self.previous_portfolio_value: Decimal = Decimal('0')
        self.new_portfolio_value: Decimal = Decimal('0')


def advance_month_service(db: Session, simulation_id: int) -> MonthAdvancementReport:
    """
    Advance simulation by one month.

    Process:
    1. Create snapshot of current state (for undo)
    2. Calculate and pay dividends for all holdings
    3. Advance current_date by 1 month
    4. Update all asset prices to new month
    5. Recalculate holdings attributes
    6. Generate advancement report

    Args:
        db: Database session
        simulation_id: Target simulation

    Returns:
        MonthAdvancementReport with details of what happened

    Raises:
        SimulationNotFoundError: If simulation doesn't exist
    """
    report = MonthAdvancementReport()

    # Get simulation
    sim = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not sim:
        raise SimulationNotFoundError(f"Simulation {simulation_id} not found")

    # Record initial state
    report.previous_date = sim.current_date
    report.previous_balance = Decimal(sim.balance)

    # Calculate initial portfolio value
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    report.previous_portfolio_value = sum(
        Decimal(h.market_value) for h in holdings
    )

    # Step 1: Create snapshot BEFORE any changes
    create_monthly_snapshot(db, simulation_id)

    # Step 2: Process dividends for current month
    report.dividends_received = _process_dividends(db, sim, holdings, report)

    # Step 3: Advance date by 1 month
    new_date = sim.current_date + relativedelta(months=1)
    sim.current_date = new_date
    report.new_date = new_date

    db.commit()
    db.refresh(sim)

    # Step 4: Update all holdings to new month prices
    report.price_updates = _update_prices_for_new_month(db, sim, holdings)

    # Step 5: Recalculate all holdings attributes
    update_holdings_attributes(db, simulation_id)

    # Refresh holdings to get updated values
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    # Calculate new portfolio value
    report.new_portfolio_value = sum(
        Decimal(h.market_value) for h in holdings
    )

    # Record final balance
    db.refresh(sim)
    report.new_balance = Decimal(sim.balance)

    return report


def _process_dividends(
        db: Session,
        sim: SimulationORM,
        holdings: List[HoldingORM],
        report: MonthAdvancementReport
) -> List[Dict]:
    """
    Calculate and pay dividends for all holdings in the current month.

    Args:
        db: Database session
        sim: Simulation object
        holdings: List of current holdings
        report: Report object to track total

    Returns:
        List of dividend payments
    """
    dividends = []
    total_dividends = Decimal('0')

    for holding in holdings:
        # Get asset data
        asset_orm = db.query(AssetORM).filter(
            AssetORM.ticker == holding.ticker
        ).first()

        if not asset_orm:
            continue

        # Find dividend for current month
        current_month = sim.current_date.replace(day=1)

        for month_data in asset_orm.monthly_data:
            month_date = date.fromisoformat(month_data["date"])

            if month_date == current_month and month_data.get("dividends"):
                # Calculate dividend payment
                dividend_per_share = Decimal(month_data["dividends"])
                quantity = Decimal(holding.quantity)
                total_dividend = dividend_per_share * quantity

                if total_dividend > 0:
                    # Pay dividend through balance service
                    dividend_request = BalanceOperationRequest(
                        amount=total_dividend,
                        operation=Operation.ADD,
                        category="dividend",
                        ticker=holding.ticker,
                        remove_inflation=False
                    )
                    handle_balance_service(db, sim.id, dividend_request)

                    dividends.append({
                        "ticker": holding.ticker,
                        "dividend_per_share": str(dividend_per_share),
                        "quantity": str(quantity),
                        "total": str(total_dividend)
                    })

                    total_dividends += total_dividend

                break

    report.total_dividends = total_dividends
    return dividends


def _update_prices_for_new_month(
        db: Session,
        sim: SimulationORM,
        holdings: List[HoldingORM]
) -> List[Dict]:
    """
    Update prices for all holdings to the new month.

    Args:
        db: Database session
        sim: Simulation object (with updated current_date)
        holdings: List of holdings

    Returns:
        List of price changes
    """
    price_updates = []

    for holding in holdings:
        old_price = Decimal(holding.current_price)

        # Get asset and new price
        asset = AssetService.search_asset(db, holding.ticker, sim.id)
        new_price = AssetService.get_price_at_date(asset, sim.current_date)

        # Calculate change
        price_change = new_price - old_price
        price_change_pct = (
            (price_change / old_price * Decimal('100'))
            if old_price > 0
            else Decimal('0')
        )

        price_updates.append({
            "ticker": holding.ticker,
            "old_price": str(old_price),
            "new_price": str(new_price),
            "change": str(price_change),
            "change_percent": str(price_change_pct.quantize(Decimal('0.01')))
        })

    return price_updates


def can_advance_month(db: Session, simulation_id: int) -> Dict:
    """
    Check if simulation can advance to next month.

    Returns information about whether advancement is possible
    and any warnings.

    Args:
        db: Database session
        simulation_id: Target simulation

    Returns:
        Dictionary with 'can_advance' bool and 'reason' if blocked
    """
    sim = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not sim:
        return {
            "can_advance": False,
            "reason": "Simulation not found"
        }

    # Check if we're already at current real date
    today = date.today()
    sim_month = sim.current_date.replace(day=1)
    today_month = today.replace(day=1)

    if sim_month >= today_month:
        return {
            "can_advance": False,
            "reason": f"Simulation is at current month ({sim_month}). Cannot advance beyond present."
        }

    # Check if next month's data exists for all holdings
    next_month = sim.current_date + relativedelta(months=1)
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    missing_data = []
    for holding in holdings:
        asset = db.query(AssetORM).filter(
            AssetORM.ticker == holding.ticker
        ).first()

        if asset:
            has_data = any(
                date.fromisoformat(m["date"]) == next_month.replace(day=1)
                for m in asset.monthly_data
            )
            if not has_data:
                missing_data.append(holding.ticker)

    if missing_data:
        return {
            "can_advance": False,
            "reason": f"Price data not available for next month for: {', '.join(missing_data)}"
        }

    return {
        "can_advance": True,
        "next_month": next_month.isoformat(),
        "holdings_count": len(holdings)
    }