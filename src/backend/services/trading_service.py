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


from decimal import Decimal
from sqlalchemy.orm import Session

from src.backend.models.simulation import SimulationORM
from src.backend.models.holding import HoldingORM
from src.backend.schemas.trading import PurchaseRequest, SellRequest
from src.backend.schemas.balance import BalanceOperationRequest
from src.backend.schemas.enums import Operation
from src.backend.services.asset_service import AssetService
from src.backend.services.balance_service import handle_balance_service
from src.backend.services.holding_service import update_holdings_attributes
from src.backend.services.exceptions import (
    InsufficientFundsError,
    InsufficientPositionError,
    AssetNotFoundError,
    PriceUnavailableError,
    SimulationNotFoundError
)


def purchase_asset_service(
        db: Session,
        simulation_id: int,
        request: PurchaseRequest
) -> SimulationORM:
    """
    Purchase an asset for a simulation.

    Flow:
    1. Validate simulation exists and has sufficient funds
    2. Search asset (RAM → DB → yfinance)
    3. Get price at simulation's current date
    4. Calculate quantity = desired_amount / price
    5. Deduct balance via handle_balance_service
    6. Create/update holding
    7. Persist asset to database

    Args:
        db: Database session
        simulation_id: Target simulation
        request: Purchase details (ticker, amount)

    Returns:
        Updated simulation

    Raises:
        SimulationNotFoundError: Simulation not found
        InsufficientFundsError: Balance < desired_amount
        AssetNotFoundError: Ticker invalid
        PriceUnavailableError: No price for sim date
    """
    # 1. Get simulation
    sim = db.query(SimulationORM).filter(SimulationORM.id == simulation_id).first()
    if not sim:
        raise SimulationNotFoundError(f"Simulation {simulation_id} not found")

    # Check balance
    current_balance = Decimal(sim.balance)
    if current_balance < request.desired_amount:
        raise InsufficientFundsError(
            f"Insufficient funds. Available: {current_balance}, "
            f"Required: {request.desired_amount}"
        )

    # 2. Search asset (three-tier)
    asset = AssetService.search_asset(db, request.ticker, simulation_id)

    # 3. Get current price
    price = AssetService.get_price_at_date(asset, sim.current_date)

    # 4. Calculate quantity (unlimited precision)
    quantity = request.desired_amount / price

    # 5. Deduct balance (this handles history logging)
    balance_request = BalanceOperationRequest(
        amount=request.desired_amount,
        operation=Operation.REMOVE,
        category="purchase",
        ticker=asset.ticker,
        remove_inflation=False
    )
    sim = handle_balance_service(db, simulation_id, balance_request)

    # 6. Create or update holding
    existing_holding = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id,
        HoldingORM.ticker == asset.ticker
    ).first()

    if existing_holding:
        # Add to existing position
        old_quantity = Decimal(existing_holding.quantity)
        new_quantity = old_quantity + quantity
        existing_holding.quantity = str(new_quantity)
        existing_holding.current_price = str(price)
        existing_holding.market_value = str((new_quantity * price).quantize(Decimal('0.01')))
    else:
        # Create new holding
        new_holding = HoldingORM(
            simulation_id=simulation_id,
            ticker=asset.ticker,
            name=asset.name,
            base_currency=asset.base_currency,
            quantity=str(quantity),
            purchase_price=str(price),
            weight="0",  # Will be calculated separately
            current_price=str(price),
            market_value=str(request.desired_amount)
        )
        db.add(new_holding)

        # 7. Persist asset to database (moves from RAM if needed)
        AssetService.persist_to_database(db, asset, simulation_id)

        # 8. Update all holdings attributes (NEW)
        update_holdings_attributes(db, simulation_id)

    db.commit()
    db.refresh(sim)

    return sim


def sell_asset_service(
        db: Session,
        simulation_id: int,
        request: SellRequest
) -> SimulationORM:
    """
    Sell an owned asset.

    Flow:
    1. Validate simulation owns asset
    2. Get current price
    3. Calculate quantity to sell
    4. Validate sufficient position
    5. Add proceeds to balance
    6. Update or delete holding
    7. Remove asset from DB if no owners remain

    Args:
        db: Database session
        simulation_id: Target simulation
        request: Sale details (ticker, amount)

    Returns:
        Updated simulation

    Raises:
        InsufficientPositionError: Trying to sell more than owned
        AssetNotFoundError: Asset not owned
        PriceUnavailableError: No price data
    """
    # 1. Get simulation and holding
    sim = db.query(SimulationORM).filter(SimulationORM.id == simulation_id).first()
    if not sim:
        raise SimulationNotFoundError(f"Simulation {simulation_id} not found")

    holding = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id,
        HoldingORM.ticker == request.ticker.upper()
    ).first()

    if not holding:
        raise AssetNotFoundError(
            f"Simulation does not own {request.ticker}"
        )

    # 2. Get current price (from DB asset or fetch)
    asset = AssetService.search_asset(db, request.ticker, simulation_id)
    price = AssetService.get_price_at_date(asset, sim.current_date)

    # 3. Calculate quantities
    current_quantity = Decimal(holding.quantity)
    market_value = (current_quantity * price).quantize(Decimal('0.01'))

    if request.desired_amount > market_value:
        raise InsufficientPositionError(
            f"Insufficient position. Market value: {market_value}, "
            f"Requested: {request.desired_amount}"
        )

    quantity_to_sell = request.desired_amount / price
    remaining_quantity = current_quantity - quantity_to_sell

    # 5. Add proceeds to balance
    balance_request = BalanceOperationRequest(
        amount=request.desired_amount,
        operation=Operation.ADD,
        category="sale",
        ticker=asset.ticker,
        remove_inflation=False
    )
    sim = handle_balance_service(db, simulation_id, balance_request)

    # 6. Update or delete holding
    if remaining_quantity >= Decimal('0.00000001'):  # Keep if significant
        # Partial sale
        holding.quantity = str(remaining_quantity)
        holding.current_price = str(price)
        holding.market_value = str((remaining_quantity * price).quantize(Decimal('0.01')))
    else:
        # Complete sale
        db.delete(holding)

    # 7. Remove from DB if no other sims own it
    AssetService.remove_from_database_if_orphaned(db, asset.ticker, simulation_id)

    # Update all holdings attributes (NEW)
    update_holdings_attributes(db, simulation_id)

    db.commit()
    db.refresh(sim)

    return sim
