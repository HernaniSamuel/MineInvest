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

    CORRECT Process:
    1. Record initial state (before any changes)
    2. Advance current_date by 1 month
    3. Get dividends from NEW month (the month we just entered)
    4. Pay dividends to balance
    5. Update all asset prices to NEW month
    6. Recalculate holdings attributes (market_value, etc)
    7. Create snapshot of the NEW month state
    8. Generate advancement report

    Example Flow:
        - Current: 30/04/2022
        - Advance to: 31/05/2022
        - Pay dividends from: May 2022 (01/05/2022)
        - Update prices to: May 2022 prices

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

    # STEP 1: Record initial state (BEFORE any changes)
    report.previous_date = sim.current_date
    report.previous_balance = Decimal(sim.balance)

    # Get holdings BEFORE advancing
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    report.previous_portfolio_value = sum(
        Decimal(h.market_value) for h in holdings
    )

    print(f"\n{'=' * 60}")
    print(f"🎯 ADVANCING SIMULATION {simulation_id}")
    print(f"📅 Current date: {sim.current_date}")
    print(f"💰 Current balance: {sim.balance}")
    print(f"📊 Current portfolio value: {report.previous_portfolio_value}")
    print(f"{'=' * 60}\n")

    # STEP 2: Create snapshot BEFORE any changes (for undo capability)
    print(f"📸 Creating snapshot BEFORE advancing (for undo)...")
    create_monthly_snapshot(db, simulation_id)
    print(f"✅ Snapshot created for {sim.current_date}\n")

    # STEP 3: Advance date by 1 month
    new_date = sim.current_date + relativedelta(months=1)
    old_date = sim.current_date
    sim.current_date = new_date
    report.new_date = new_date

    print(f"\n📅 Date advanced: {old_date} → {new_date}\n")

    db.commit()
    db.refresh(sim)

    # STEP 4: Process dividends from the NEW month (the month we just entered)
    # Dividends are paid when you ENTER the new month
    report.dividends_received = _process_dividends(db, sim, holdings, report)

    # STEP 5: Update all holdings to new month prices
    report.price_updates = _update_prices_for_new_month(db, sim, holdings)

    # STEP 6: Recalculate all holdings attributes (market_value based on new prices)
    print(f"\n🔄 Recalculating holdings attributes...")
    update_holdings_attributes(db, simulation_id)

    # STEP 6: Create snapshot of the NEW month state (AFTER all updates)
    print(f"\n📸 Creating snapshot for {new_date}...")
    create_monthly_snapshot(db, simulation_id)

    # STEP 7: Calculate final state for report
    # Refresh holdings to get updated values
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    report.new_portfolio_value = sum(
        Decimal(h.market_value) for h in holdings
    )

    # Refresh simulation to get updated balance
    db.refresh(sim)
    report.new_balance = Decimal(sim.balance)

    print(f"\n{'=' * 60}")
    print(f"✅ ADVANCEMENT COMPLETE")
    print(f"📅 New date: {report.new_date}")
    print(f"💰 New balance: {report.new_balance}")
    print(f"💵 Total dividends received: {report.total_dividends}")
    print(f"📊 New portfolio value: {report.new_portfolio_value}")
    print(f"{'=' * 60}\n")

    return report


def _process_dividends(
        db: Session,
        sim: SimulationORM,
        holdings: List[HoldingORM],
        report: MonthAdvancementReport
) -> List[Dict]:
    """
    Calculate and pay dividends for all holdings in the NEW month.

    IMPORTANT: This is called AFTER advancing the date.
    When you advance from April to May, you get May's dividends.
    The simulation date represents the END of that month.

    Example:
        - Sim date: 30/04/2022 → Advance → 31/05/2022
        - Pay dividends from: 01/05/2022 (the NEW month)

    Args:
        db: Database session
        sim: Simulation object (with NEW date, already advanced)
        holdings: List of current holdings
        report: Report object to track total

    Returns:
        List of dividend payments
    """
    dividends = []
    total_dividends = Decimal('0')

    # Use NEW month (the month we just entered)
    current_month = sim.current_date.replace(day=1)

    print(f"\n{'=' * 60}")
    print(f"💰 PROCESSING DIVIDENDS FOR MONTH: {current_month}")
    print(f"{'=' * 60}")

    for holding in holdings:
        print(f"\n📌 Checking {holding.ticker} (quantity: {holding.quantity})")
        print(f"   🔍 Searching asset with ticker: '{holding.ticker}'")

        # DEBUG: Check all assets in database
        all_assets = db.query(AssetORM).all()
        print(f"   📊 Total assets in DB: {len(all_assets)}")
        if all_assets:
            print(f"   📋 Available tickers: {[a.ticker for a in all_assets]}")

        # Get asset data
        asset_orm = db.query(AssetORM).filter(
            AssetORM.ticker == holding.ticker
        ).first()

        if not asset_orm:
            print(f"   ⚠️  Asset not found in database")
            print(f"   ❌ Query failed: AssetORM.ticker == '{holding.ticker}'")

            # Try alternative queries
            print(f"   🔄 Trying alternative searches...")
            asset_by_id = db.query(AssetORM).filter(
                AssetORM.id == holding.asset_id
            ).first() if hasattr(holding, 'asset_id') else None

            if asset_by_id:
                print(f"   ✅ Found by asset_id! Ticker: {asset_by_id.ticker}")
                asset_orm = asset_by_id
            else:
                continue

        # Find dividend for CURRENT month
        dividend_found = False
        for month_data in asset_orm.monthly_data:
            month_date = date.fromisoformat(month_data["date"])

            if month_date == current_month:
                dividend_found = True
                dividend_value = month_data.get("dividends", "0.0")

                print(f"   📅 Found data for {month_date}")
                print(f"   💵 Dividend value: {dividend_value}")

                if dividend_value and dividend_value != "0.0" and float(dividend_value) > 0:
                    # Calculate dividend payment
                    dividend_per_share = Decimal(str(dividend_value))
                    quantity = Decimal(str(holding.quantity))
                    total_dividend = dividend_per_share * quantity

                    print(f"   ✅ PAYING DIVIDEND:")
                    print(f"      • Per share: {dividend_per_share}")
                    print(f"      • Quantity: {quantity}")
                    print(f"      • Total: {total_dividend}")

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
                        "total": str(total_dividend),
                        "date": current_month.isoformat()
                    })

                    total_dividends += total_dividend
                else:
                    print(f"   ℹ️  No dividend for this month (value: {dividend_value})")
                break

        if not dividend_found:
            print(f"   ⚠️  No data found for month {current_month}")

    print(f"\n{'=' * 60}")
    print(f"✅ DIVIDENDS SUMMARY")
    print(f"💵 Total dividends paid: {total_dividends}")
    print(f"📝 Number of payments: {len(dividends)}")
    print(f"{'=' * 60}\n")

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
        sim: Simulation object (with UPDATED current_date)
        holdings: List of holdings

    Returns:
        List of price changes
    """
    price_updates = []

    print(f"\n{'=' * 60}")
    print(f"📈 UPDATING PRICES FOR NEW MONTH: {sim.current_date}")
    print(f"{'=' * 60}\n")

    for holding in holdings:
        old_price = Decimal(str(holding.current_price))

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

        print(f"📊 {holding.ticker}:")
        print(f"   Old price: {old_price}")
        print(f"   New price: {new_price}")
        print(f"   Change: {price_change} ({price_change_pct:.2f}%)\n")

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