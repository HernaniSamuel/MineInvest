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
import logging

from src.backend.models.simulation import SimulationORM
from src.backend.models.holding import HoldingORM
from src.backend.schemas.trading import PurchaseRequest, SellRequest
from src.backend.schemas.simulation import SimulationRead
from src.backend.services.asset_service import AssetService
from src.backend.services.exchange_service import ExchangeService
from src.backend.services.exceptions import (
    AssetNotFoundError,
    InsufficientFundsError,
    InsufficientPositionError,
    PriceUnavailableError,
    SimulationNotFoundError
)

logger = logging.getLogger(__name__)


def purchase_asset_service(
        db: Session,
        simulation_id: int,
        request: PurchaseRequest
) -> SimulationRead:
    """
    Purchase an asset for a simulation with automatic currency conversion.

    This service handles the complete asset purchase workflow:
    1. Validates simulation and asset existence
    2. Retrieves current asset price at simulation date
    3. Converts price to simulation currency (if needed)
    4. Calculates quantity of shares to purchase
    5. Validates sufficient balance
    6. Deducts amount from balance
    7. Creates or updates holding with weighted average price

    Currency Conversion:
        If the asset's currency differs from the simulation's base currency,
        the service automatically fetches the exchange rate for the simulation's
        current date and converts the asset price accordingly.

    Example:
        >>> # Simulation in BRL, buying AAPL (priced in USD)
        >>> result = purchase_asset_service(
        ...     db=session,
        ...     simulation_id=1,
        ...     request=PurchaseRequest(
        ...         ticker='AAPL',
        ...         desired_amount=5000.00  # BRL
        ...     )
        ... )
        >>> # Service will:
        >>> # 1. Get AAPL price in USD (e.g., $180.50)
        >>> # 2. Get USD/BRL rate (e.g., 4.87)
        >>> # 3. Convert: 180.50 * 4.87 = 879.04 BRL per share
        >>> # 4. Calculate shares: 5000 / 879.04 = 5.6875 shares
        >>> # 5. Deduct 5000 BRL from balance
        >>> # 6. Add 5.6875 shares to holdings

    Args:
        db: Database session for transactions
        simulation_id: ID of the simulation making the purchase
        request: Purchase request containing ticker and desired amount

    Returns:
        SimulationRead with updated balance and holdings

    Raises:
        SimulationNotFoundError: If simulation doesn't exist
        AssetNotFoundError: If asset doesn't exist or not available at date
        PriceUnavailableError: If no price data for asset at simulation date
        InsufficientFundsError: If desired amount exceeds available balance

    Note:
        The desired_amount is always in the simulation's base currency,
        regardless of the asset's native currency.
    """
    logger.info(
        f"Purchase request: simulation_id={simulation_id}, "
        f"ticker={request.ticker}, amount={request.desired_amount}"
    )

    # Validate simulation exists
    simulation = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not simulation:
        raise SimulationNotFoundError(f"Simulation {simulation_id} not found")

    # Validate and fetch asset
    asset = AssetService.search_asset(db, request.ticker, simulation_id)
    if not asset:
        raise AssetNotFoundError(f"Asset {request.ticker} not found")

    # Get asset price at simulation date
    historical_data = AssetService.get_historical_data_until_date(
        asset,
        simulation.current_date
    )

    if not historical_data:
        raise PriceUnavailableError(
            f"No price data for {request.ticker} at {simulation.current_date}"
        )

    # Extract price and currencies
    original_price = Decimal(str(historical_data[-1]["close"]))
    asset_currency = asset.base_currency
    simulation_currency = simulation.base_currency

    logger.info(
        f"Asset price: {original_price} {asset_currency}, "
        f"Simulation currency: {simulation_currency}"
    )

    # Convert price if currencies differ
    if asset_currency != simulation_currency:
        logger.info(f"Currency conversion required: {asset_currency} → {simulation_currency}")

        # Fetch exchange rate from service
        exchange_response = ExchangeService.get_exchange_rate(
            db=db,
            from_currency=asset_currency,
            to_currency=simulation_currency,
            target_date=simulation.current_date
        )

        exchange_rate = exchange_response.rate
        converted_price = original_price * exchange_rate

        logger.info(
            f"Exchange rate: {exchange_rate} ({exchange_response.yfinance_symbol}), "
            f"Converted price: {converted_price} {simulation_currency}, "
            f"Cache hit: {exchange_response.from_cache}"
        )
    else:
        converted_price = original_price
        logger.info("No currency conversion needed")

    # Calculate share quantity based on desired amount
    desired_amount = Decimal(str(request.desired_amount))
    quantity = desired_amount / converted_price

    logger.info(
        f"Purchase calculation: {desired_amount} {simulation_currency} / "
        f"{converted_price} {simulation_currency} = {quantity} shares"
    )

    # Validate sufficient balance
    if desired_amount > simulation.balance:
        raise InsufficientFundsError(
            f"Insufficient funds. Available: {simulation.balance} {simulation_currency}, "
            f"Required: {desired_amount} {simulation_currency}"
        )

    # Deduct amount from balance
    simulation.balance -= desired_amount
    logger.info(f"Balance after purchase: {simulation.balance} {simulation_currency}")

    # Create or update holding
    holding = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id,
        HoldingORM.ticker == request.ticker
    ).first()

    if holding:
        # Update existing holding with weighted average price
        total_quantity = holding.quantity + quantity
        new_average_price = (
                (holding.average_price * holding.quantity + converted_price * quantity)
                / total_quantity
        )

        logger.info(
            f"Updating holding: {holding.quantity} + {quantity} = {total_quantity} shares, "
            f"Average price: {holding.average_price} → {new_average_price}"
        )

        holding.average_price = new_average_price
        holding.quantity = total_quantity
    else:
        # Create new holding
        holding = HoldingORM(
            simulation_id=simulation_id,
            ticker=request.ticker,
            quantity=quantity,
            average_price=converted_price
        )
        db.add(holding)

        logger.info(
            f"Created new holding: {quantity} shares at {converted_price} {simulation_currency}"
        )

    # Commit transaction
    db.commit()
    db.refresh(simulation)

    logger.info(f"Purchase completed successfully for {request.ticker}")

    return SimulationRead.model_validate(simulation)


def sell_asset_service(
        db: Session,
        simulation_id: int,
        request: SellRequest
) -> SimulationRead:
    """
    Sell an asset from a simulation with automatic currency conversion.

    This service handles the complete asset sale workflow:
    1. Validates simulation and existing position
    2. Retrieves current asset price at simulation date
    3. Converts price to simulation currency (if needed)
    4. Calculates quantity of shares to sell
    5. Validates sufficient position
    6. Adds proceeds to balance
    7. Updates or removes holding

    Currency Conversion:
        Like purchases, sales automatically handle currency conversion when
        the asset's currency differs from the simulation's base currency.

    Example:
        >>> # Simulation in BRL, selling AAPL (priced in USD)
        >>> result = sell_asset_service(
        ...     db=session,
        ...     simulation_id=1,
        ...     request=SellRequest(
        ...         ticker='AAPL',
        ...         desired_amount=3000.00  # BRL worth to sell
        ...     )
        ... )
        >>> # Service will:
        >>> # 1. Get AAPL price in USD (e.g., $185.75)
        >>> # 2. Get USD/BRL rate (e.g., 4.92)
        >>> # 3. Convert: 185.75 * 4.92 = 913.89 BRL per share
        >>> # 4. Calculate shares to sell: 3000 / 913.89 = 3.2826 shares
        >>> # 5. Validate position has at least 3.2826 shares
        >>> # 6. Add 3000 BRL to balance
        >>> # 7. Reduce position by 3.2826 shares

    Args:
        db: Database session for transactions
        simulation_id: ID of the simulation making the sale
        request: Sell request containing ticker and desired amount

    Returns:
        SimulationRead with updated balance and holdings

    Raises:
        SimulationNotFoundError: If simulation doesn't exist
        InsufficientPositionError: If no position exists or insufficient shares
        AssetNotFoundError: If asset doesn't exist
        PriceUnavailableError: If no price data for asset at simulation date

    Note:
        If the sale reduces the position to near-zero (< 0.000001 shares),
        the holding is automatically removed from the database.
    """
    logger.info(
        f"Sell request: simulation_id={simulation_id}, "
        f"ticker={request.ticker}, amount={request.desired_amount}"
    )

    # Validate simulation exists
    simulation = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not simulation:
        raise SimulationNotFoundError(f"Simulation {simulation_id} not found")

    # Validate position exists
    holding = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id,
        HoldingORM.ticker == request.ticker
    ).first()

    if not holding:
        raise InsufficientPositionError(f"No position in {request.ticker}")

    logger.info(
        f"Current position: {holding.quantity} shares at "
        f"average price {holding.average_price}"
    )

    # Validate and fetch asset
    asset = AssetService.search_asset(db, request.ticker, simulation_id)
    if not asset:
        raise AssetNotFoundError(f"Asset {request.ticker} not found")

    # Get current asset price
    historical_data = AssetService.get_historical_data_until_date(
        asset,
        simulation.current_date
    )

    if not historical_data:
        raise PriceUnavailableError(
            f"No price data for {request.ticker} at {simulation.current_date}"
        )

    # Extract price and currencies
    original_price = Decimal(str(historical_data[-1]["close"]))
    asset_currency = asset.base_currency
    simulation_currency = simulation.base_currency

    logger.info(f"Current asset price: {original_price} {asset_currency}")

    # Convert price if currencies differ
    if asset_currency != simulation_currency:
        logger.info(f"Currency conversion required: {asset_currency} → {simulation_currency}")

        # Fetch exchange rate from service
        exchange_response = ExchangeService.get_exchange_rate(
            db=db,
            from_currency=asset_currency,
            to_currency=simulation_currency,
            target_date=simulation.current_date
        )

        exchange_rate = exchange_response.rate
        converted_price = original_price * exchange_rate

        logger.info(
            f"Exchange rate: {exchange_rate}, "
            f"Converted price: {converted_price} {simulation_currency}, "
            f"Cache hit: {exchange_response.from_cache}"
        )
    else:
        converted_price = original_price
        logger.info("No currency conversion needed")

    # Calculate quantity to sell based on desired amount
    desired_amount = Decimal(str(request.desired_amount))
    quantity_to_sell = desired_amount / converted_price

    logger.info(
        f"Sell calculation: {desired_amount} {simulation_currency} / "
        f"{converted_price} {simulation_currency} = {quantity_to_sell} shares"
    )

    # Validate sufficient position
    if quantity_to_sell > holding.quantity:
        max_amount = holding.quantity * converted_price
        raise InsufficientPositionError(
            f"Insufficient position. You own {holding.quantity} shares. "
            f"At current price of {converted_price} {simulation_currency}, "
            f"you can sell up to {max_amount:.2f} {simulation_currency}"
        )

    # Add proceeds to balance
    simulation.balance += desired_amount
    logger.info(f"Balance after sale: {simulation.balance} {simulation_currency}")

    # Update or remove holding
    holding.quantity -= quantity_to_sell

    # Remove holding if position is effectively zero
    if holding.quantity < Decimal("0.000001"):
        logger.info("Position closed completely, removing holding")
        db.delete(holding)
    else:
        logger.info(f"Position reduced to {holding.quantity} shares")

    # Commit transaction
    db.commit()
    db.refresh(simulation)

    logger.info(f"Sale completed successfully for {request.ticker}")

    return SimulationRead.model_validate(simulation)