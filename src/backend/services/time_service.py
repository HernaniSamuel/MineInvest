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
from src.backend.services.exchange_service import ExchangeService
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
    2. Create snapshot BEFORE any changes (for undo)
    3. Advance current_date by 1 month
    4. Get dividends from NEW month and convert to simulation currency
    5. Pay dividends to balance
    6. Update all asset prices to NEW month
    7. Recalculate holdings attributes (market_value, etc)
    8. Generate advancement report

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

    # STEP 4: Process dividends from the NEW month (with currency conversion)
    report.dividends_received = _process_dividends(db, sim, holdings, report)

    # STEP 5: Update all holdings to new month prices
    report.price_updates = _update_prices_for_new_month(db, sim, holdings)

    # STEP 6: Recalculate all holdings attributes (market_value based on new prices)
    print(f"\n🔄 Recalculating holdings attributes...")
    update_holdings_attributes(db, simulation_id)

    # STEP 7: Calculate final state for report
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    report.new_portfolio_value = sum(
        Decimal(h.market_value) for h in holdings
    )

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
    Automatically converts from asset currency to simulation currency.
    """
    dividends = []
    total_dividends = Decimal('0')

    current_month = sim.current_date.replace(day=1)
    simulation_currency = sim.base_currency

    print(f"\n{'=' * 60}")
    print(f"💰 PROCESSING DIVIDENDS FOR MONTH: {current_month}")
    print(f"💵 Simulation currency: {simulation_currency}")
    print(f"{'=' * 60}")

    for holding in holdings:
        print(f"\n📌 Checking {holding.ticker} (quantity: {holding.quantity})")

        # Get asset data
        asset_orm = db.query(AssetORM).filter(
            AssetORM.ticker == holding.ticker
        ).first()

        if not asset_orm:
            print(f"   ⚠️  Asset not found in database")
            continue

        # Get asset currency
        asset_currency = asset_orm.base_currency
        print(f"   💱 Asset currency: {asset_currency}")

        # Find dividend for current month
        dividend_found = False
        for month_data in asset_orm.monthly_data:
            month_date = date.fromisoformat(month_data["date"])

            if month_date == current_month:
                dividend_found = True
                dividend_value = month_data.get("dividends", "0.0")

                print(f"   📅 Found data for {month_date}")
                print(f"   💵 Dividend value: {dividend_value} {asset_currency}")

                if dividend_value and dividend_value != "0.0" and float(dividend_value) > 0:
                    # Calculate dividend in original currency
                    dividend_per_share_original = Decimal(str(dividend_value))
                    quantity = Decimal(str(holding.quantity))
                    total_dividend_original = dividend_per_share_original * quantity

                    print(f"   💰 Dividend calculation (original currency):")
                    print(f"      • Per share: {dividend_per_share_original} {asset_currency}")
                    print(f"      • Quantity: {quantity}")
                    print(f"      • Total: {total_dividend_original} {asset_currency}")

                    # Convert to simulation currency if needed
                    if asset_currency != simulation_currency:
                        print(f"   🔁 Converting {asset_currency} → {simulation_currency}")

                        try:
                            rate_response = ExchangeService.get_exchange_rate(
                                db=db,
                                from_currency=asset_currency,
                                to_currency=simulation_currency,
                                target_date=sim.current_date
                            )
                            exchange_rate = Decimal(str(rate_response.rate))

                            dividend_per_share_converted = dividend_per_share_original * exchange_rate
                            total_dividend_converted = total_dividend_original * exchange_rate

                            print(f"      • Exchange rate: {exchange_rate}")
                            print(
                                f"      • Per share (converted): {dividend_per_share_converted} {simulation_currency}")
                            print(f"      • Total (converted): {total_dividend_converted} {simulation_currency}")

                        except Exception as e:
                            print(f"   ❌ Currency conversion failed: {e}")
                            print(f"   ⚠️  Skipping dividend payment for {holding.ticker}")
                            continue
                    else:
                        # Same currency, no conversion needed
                        dividend_per_share_converted = dividend_per_share_original
                        total_dividend_converted = total_dividend_original
                        exchange_rate = Decimal('1.0')
                        print(f"   ✅ No conversion needed (same currency)")

                    # Pay dividend in simulation currency
                    print(f"   ✅ PAYING DIVIDEND:")
                    print(f"      • Amount: {total_dividend_converted} {simulation_currency}")

                    dividend_request = BalanceOperationRequest(
                        amount=total_dividend_converted,
                        operation=Operation.ADD,
                        category="dividend",
                        ticker=holding.ticker,
                        remove_inflation=False
                    )
                    handle_balance_service(db, sim.id, dividend_request)

                    # Record dividend with conversion info
                    dividend_record = {
                        "ticker": holding.ticker,
                        "dividend_per_share_original": str(dividend_per_share_original),
                        "dividend_per_share_converted": str(dividend_per_share_converted),
                        "quantity": str(quantity),
                        "total_original": str(total_dividend_original),
                        "total_converted": str(total_dividend_converted),
                        "original_currency": asset_currency,
                        "converted_currency": simulation_currency,
                        "exchange_rate": str(exchange_rate),
                        "date": current_month.isoformat(),
                        "was_converted": asset_currency != simulation_currency
                    }

                    dividends.append(dividend_record)
                    total_dividends += total_dividend_converted
                else:
                    print(f"   ℹ️  No dividend for this month")
                break

        if not dividend_found:
            print(f"   ⚠️  No data found for month {current_month}")

    print(f"\n{'=' * 60}")
    print(f"✅ DIVIDENDS SUMMARY")
    print(f"💵 Total dividends paid: {total_dividends} {simulation_currency}")
    print(f"📝 Number of payments: {len(dividends)}")

    if dividends:
        print(f"\n📋 Breakdown:")
        for div in dividends:
            if div["was_converted"]:
                print(f"   • {div['ticker']}: {div['total_original']} {div['original_currency']} "
                      f"→ {div['total_converted']} {div['converted_currency']} "
                      f"(rate: {div['exchange_rate']})")
            else:
                print(f"   • {div['ticker']}: {div['total_converted']} {div['converted_currency']}")

    print(f"{'=' * 60}\n")

    report.total_dividends = total_dividends
    return dividends


def _update_prices_for_new_month(
        db: Session,
        sim: SimulationORM,
        holdings: List[HoldingORM]
) -> List[Dict]:
    """Update prices for all holdings to the new month."""
    price_updates = []

    print(f"\n{'=' * 60}")
    print(f"📈 UPDATING PRICES FOR NEW MONTH: {sim.current_date}")
    print(f"{'=' * 60}\n")

    for holding in holdings:
        old_price = Decimal(str(holding.current_price))

        asset = AssetService.search_asset(db, holding.ticker, sim.id)
        new_price = AssetService.get_price_at_date(asset, sim.current_date)

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
    """Check if simulation can advance to next month."""
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