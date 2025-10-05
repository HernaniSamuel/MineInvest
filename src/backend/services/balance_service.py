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
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from datetime import date

from src.backend.models.simulation import SimulationORM
from src.backend.models.history_month import HistoryMonthORM
from src.backend.schemas.balance import BalanceOperationRequest
from src.backend.schemas.enums import Operation
from src.backend.services.inflation_adjustment import _apply_inflation_adjustment
from src.backend.services.exceptions import (
    InsufficientFundsError,
    SimulationNotFoundError
)


def handle_balance_service(
        db: Session,
        simulation_id: int,
        request: BalanceOperationRequest
) -> SimulationORM:
    """
    Unified method for all balance modifications.

    Handles balance changes and automatically logs to HistoryMonth.

    Args:
        db: Database session
        simulation_id: Target simulation id
        request: Contains amount, operation, category, ticker (if applicable)

    Returns:
        Updated simulation object

    Raises:
        SimulationNotFoundError: If simulation does not exist
        InsufficientFoundsError: If removing more than available balance

    Category Rules:
        - contribution/withdrawal: No ticker, 2 decimals max
        - dividend/purchase/sale: Ticker required
        - dividend: Unlimited decimal precision
        - purchase/sale: 2 decimals max

        Example:
        Contribution:
        >>> req = BalanceOperationRequest(
        ...     amount=Decimal("1000.50"),
        ...     operation=Operation.ADD,
        ...     category="contribution"
        ... )

        Dividend (high precision):
        >>> req = BalanceOperationRequest(
        ...     amount=Decimal("0.012345"),
        ...     operation=Operation.ADD,
        ...     category="dividend",
        ...     ticker="PETR4"
        ... )
    """
    # Retrieve simulation
    simulation = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not simulation:
        raise SimulationNotFoundError(
            f"Simulation with ID {simulation_id} not found"
        )

    # Convert stored string to Decimal for calculation
    current_balance = Decimal(str(simulation.balance))

    # Get validated amount
    amount = request.amount

    # Apply inflation adjustment if requested
    if request.remove_inflation:
        amount = _apply_inflation_adjustment(
            amount=amount,
            base_currency=str(simulation.base_currency),
            reference_date=simulation.current_date,
            current_date=date.today(),
            db_session=db
        )

    # Calculate new balance using operation multiplier
    balance_change = amount * request.operation.value_multiplier
    new_balance = current_balance + balance_change

    # Validate sufficient funds for withdrawals/purchases
    if new_balance < Decimal('0'):
        raise InsufficientFundsError(
            f"Insufficient funds. "
            f"Available: {current_balance}, "
            f"Requested: {request.category} of {amount}, "
            f"Shortfall: {abs(new_balance)}"
        )

    # Update balance
    simulation.balance = str(new_balance)

    # Log operation in HistoryMonth

    _log_balance_operation(
        db=db,
        simulation=simulation,
        operation_type=request.category,
        amount=balance_change,
        ticker=request.ticker
    )
    
    # Commit
    db.commit()
    db.refresh(simulation)

    return simulation


def _log_balance_operation(
        db: Session,
        simulation: SimulationORM,
        operation_type: str,
        amount: Decimal,
        ticker: Optional[str] = None
) -> None:
    """
    Logs operation in current month's history.

    Creates HistoryMonth entry if it doesn't exist for current month.
    Appends operation to operations list with full precision.

    Args:
        db: Database session
        simulation: Simulation object
        operation_type: Category (contribution, withdrawal, purchase, sale, dividend)
        amount: Signed amount (positive=add, negative=remove)
        ticker: Asset ticker if applicable (dividend, purchase, sale)
    """
    # Find or create history for current month
    current_history = db.query(HistoryMonthORM).filter(
        HistoryMonthORM.simulation_id == simulation.id,
        HistoryMonthORM.month_date == simulation.current_date
    ).first()

    if not current_history:
        current_history = HistoryMonthORM(
            simulation_id=simulation.id,
            month_date=simulation.current_date,
            operations=[],
            total='0'
        )
        db.add(current_history)
        db.flush()

    # Append operation with full precision preserved
    operations = current_history.operations or []
    operations.append({
        "type": operation_type,
        "amount": str(amount),
        "ticker": ticker
    })

    # Update and flag as modified
    current_history.operations = operations
    flag_modified(current_history, "operations")

    # Update total to reflect current balance
    current_history.total = simulation.balance
