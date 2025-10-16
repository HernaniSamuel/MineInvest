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


from decimal import Decimal, ROUND_DOWN
from sqlalchemy.orm import Session
from typing import List

from src.backend.models.simulation import SimulationORM
from src.backend.models.holding import HoldingORM
from src.backend.services.asset_service import AssetService
from src.backend.services.exceptions import SimulationNotFoundError
from src.backend.services.exchange_service import ExchangeService

def update_holdings_attributes(db: Session, simulation_id: int) -> List[HoldingORM]:
    """
    Recalculate all holding attributes for a simulation.

    Updates for each holding:
    - current_price: Latest price at simulation's current_date (converted to simulation currency)
    - market_value: quantity * current_price
    - weight: (market_value / total_portfolio_value) * 100

    Should be called after:
    - Purchasing assets
    - Selling assets
    - Advancing simulation time
    - Manual price updates
    """
    # Get simulation
    sim = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not sim:
        raise SimulationNotFoundError(f"Simulation {simulation_id} not found")

    sim_currency = sim.base_currency

    # Get holdings
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    if not holdings:
        return []

    for holding in holdings:
        asset = AssetService.search_asset(db, holding.ticker, simulation_id)
        current_price_original = AssetService.get_price_at_date(asset, sim.current_date)
        current_price_original = Decimal(str(current_price_original))

        asset_currency = getattr(holding, "base_currency", sim_currency)

        # 🔁 Conversão de moeda se necessário
        if asset_currency != sim_currency:
            rate_response = ExchangeService.get_exchange_rate(
                db=db,
                from_currency=asset_currency,
                to_currency=sim_currency,
                target_date=sim.current_date
            )
            exchange_rate = Decimal(str(rate_response.rate))
            current_price_converted = (current_price_original * exchange_rate).quantize(
                Decimal("0.0001"), rounding=ROUND_DOWN
            )
        else:
            current_price_converted = current_price_original

        holding.current_price = str(current_price_converted)

        quantity = Decimal(str(holding.quantity))
        market_value = (quantity * current_price_converted).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        holding.market_value = str(market_value)

    total_portfolio_value = sum(Decimal(h.market_value) for h in holdings)

    if total_portfolio_value > 0:
        for holding in holdings:
            weight = (
                (Decimal(holding.market_value) / total_portfolio_value) * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            holding.weight = str(weight)
    else:
        for holding in holdings:
            holding.weight = "0.00"

    db.commit()
    for holding in holdings:
        db.refresh(holding)

    return holdings


def get_holdings_summary(db: Session, simulation_id: int) -> dict:
    """
    Get portfolio summary statistics.

    Returns:
        Dictionary with:
        - total_holdings: Number of different assets
        - total_market_value: Sum of all positions
        - total_invested: Sum of all purchase prices * quantities
        - total_gain_loss: market_value - invested
        - gain_loss_percentage: (gain_loss / invested) * 100

    Args:
        db: Database session
        simulation_id: Target simulation

    Returns:
        Summary statistics dictionary
    """
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    if not holdings:
        return {
            "total_holdings": 0,
            "total_market_value": "0.00",
            "total_invested": "0.00",
            "total_gain_loss": "0.00",
            "gain_loss_percentage": "0.00"
        }

    total_market_value = Decimal('0')
    total_invested = Decimal('0')

    for holding in holdings:
        market_value = Decimal(holding.market_value)
        invested = Decimal(holding.quantity) * Decimal(holding.purchase_price)

        total_market_value += market_value
        total_invested += invested

    total_gain_loss = total_market_value - total_invested

    gain_loss_percentage = (
        (total_gain_loss / total_invested * Decimal('100'))
        if total_invested > 0
        else Decimal('0')
    ).quantize(Decimal('0.01'), rounding=ROUND_DOWN)

    return {
        "total_holdings": len(holdings),
        "total_market_value": str(total_market_value.quantize(Decimal('0.01'))),
        "total_invested": str(total_invested.quantize(Decimal('0.01'))),
        "total_gain_loss": str(total_gain_loss.quantize(Decimal('0.01'))),
        "gain_loss_percentage": str(gain_loss_percentage)
    }