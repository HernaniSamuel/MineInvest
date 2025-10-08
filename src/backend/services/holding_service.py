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


def update_holdings_attributes(db: Session, simulation_id: int) -> List[HoldingORM]:
    """
    Recalculate all holding attributes for a simulation.

    Updates for each holding:
    - current_price: Latest price at simulation's current_date
    - market_value: quantity * current_price
    - weight: (market_value / total_portfolio_value) * 100

    Should be called after:
    - Purchasing assets
    - Selling assets
    - Advancing simulation time
    - Manual price updates

    Args:
        db: Database session
        simulation_id: Target simulation

    Returns:
        List of updated holdings

    Raises:
        SimulationNotFoundError: If simulation doesn't exist
    """
    # Get simulation
    sim = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not sim:
        raise SimulationNotFoundError(f"Simulation {simulation_id} not found")

    # Get all holdings
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    if not holdings:
        return []  # No holdings to update

    # Update each holding's price and market value
    for holding in holdings:
        # Get current asset price
        asset = AssetService.search_asset(db, holding.ticker, simulation_id)
        current_price = AssetService.get_price_at_date(asset, sim.current_date)

        # Update price
        holding.current_price = str(current_price)

        # Calculate market value
        quantity = Decimal(holding.quantity)
        market_value = (quantity * current_price).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        holding.market_value = str(market_value)

    # Calculate total portfolio value (sum of all market values)
    total_portfolio_value = sum(
        Decimal(h.market_value) for h in holdings
    )

    # Update weights
    if total_portfolio_value > 0:
        for holding in holdings:
            weight_percentage = (
                    (Decimal(holding.market_value) / total_portfolio_value) * Decimal('100')
            ).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            holding.weight = str(weight_percentage)
    else:
        # No value - set all weights to 0
        for holding in holdings:
            holding.weight = "0.00"

    db.commit()

    # Refresh all holdings
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