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


from datetime import date
from decimal import Decimal
from typing import Optional, List
from enum import Enum
from holding import Holding
from asset import Asset
from history_month import HistoryMonth


# Cleaner way to define witch operation will be made
class Operation(Enum):
    """
    Enumeration of operation types for modifying simulation state.

    This enum is used throughout the simulation to indicate whether an operation
    should add to or subtract from a value (balance, holdings, etc.), providing
    type safety and improved code readability compared to magic numbers.

    Attributes:
        ADD (int): Represents an addition operation (value: 1).
                   Used for deposits, purchases, dividend receipts, etc.
        REMOVE (int): Represents a subtraction operation (value: -1).
                      Used for withdrawals, sales, fee deductions, etc.

    Example:
        simulation.handle_balance(Decimal("500.00"), Operation.ADD, "deposit", False)
        simulation.trade_asset(Decimal("1000.00"), Operation.REMOVE, "PETR4")
    """
    ADD = 1
    REMOVE = -1


class Simulation:
    """
    Represents a month-by-month investment simulation with realistic historical data.

    This class manages the complete state of an investment portfolio simulation,
    including balance tracking, asset holdings, transaction history, and temporal
    progression through historical market data. It provides a sandbox environment
    for users to test investment strategies with actual historical prices and events.

    The simulation operates on a monthly granularity, allowing users to make
    investment decisions, advance time, and observe the effects of market movements,
    dividends, and splits on their portfolio over extended periods.

    Attributes:
        name (str): User-defined name for the simulation.
        start_date (date): The month and year when the simulation begins.
        base_currency (str): The base currency for all monetary values (currently "BRL").
        balance (Decimal): Current available cash balance in the simulation.
        current_date (date): The current month and year in the simulation timeline.
        holdings (List[Holding]): List of assets currently held in the portfolio.
        history (List[HistoryMonth]): Chronological record of all monthly operations.

    Example:
        sim = Simulation("My Portfolio", date(2019, 1, 1), "BRL")
        sim.handle_balance(Decimal("10000.00"), Operation.ADD, "contribution", False)
        sim.trade_asset(Decimal("5000.00"), Operation.ADD, "PETR4")
        sim.advance_month()

    Note:
        - All monetary values use Decimal for precision
        - Inflation adjustment uses IPCA data from Banco Central do Brasil
        - Asset data is sourced from yfinance with monthly granularity
    """

    def __init__(self, name: str, start_date: date, base_currency: str, id: int = None) -> None:
        """
        Initializes a new Simulation instance.

        Args:
            id (int, optional): Unique identifier for the simulation. Defaults to None.
            name (str): The name of the simulation.
            start_date (date): The starting date of the simulation.
            base_currency (str): The base currency used in the simulation.

        Attributes:
            balance (Decimal): The current balance of the simulation, initialized to 0.
            current_date (date): Tracks the simulation's current date, starts at `start_date`.
            holdings (List[Holding]): List of assets held in the simulation.
            history (List[HistoryMonth]): List of monthly history snapshots.
            month_snapshot (Optional[dict]): Temporary snapshot of the current month state.
        """

        self.id: int = id
        self.name: str = name
        self.start_date: date = start_date
        self.base_currency: str = base_currency
        self.balance: Decimal = Decimal(0)
        self.current_date: date = start_date
        self.holdings: List[Holding] = []
        self.history: List[HistoryMonth] = []
        self.month_snapshot: Optional[dict] = None

    def handle_balance(self, amount: Decimal, operation: Operation, category: str, remove_accumulated_inflation: bool) -> None:
        """
        Centralized method for securely modifying the simulation balance.

        This method handles all additions and subtractions of funds, ensuring consistency
        and proper logging of operations in the simulation's history.

        Args:
            amount (Decimal): The amount of money to modify the simulation balance.
            operation (int): Operation type: Operation.ADD to add, Operation.REMOVE to remove funds.
            category (str): Reason for the balance change; will be recorded in the history.
            remove_accumulated_inflation (bool): Whether or not to remove accumulated inflation.

        Returns:
            None
        """
        pass

    def remove_accumulated_inflation(self, amount: Decimal) -> None:
        """
        Adjusts the simulation balance by removing accumulated inflation, effectively 'rewinding' the value of money
        from the current date to the reference period.

        Args:
            amount (Decimal): The nominal amount to adjust for inflation.

        Returns:
            None
        """
        pass

    def get_asset(self, ticker: str) -> Asset:
        """
        Search the database for the desired asset, use APIs if the asset is not found in the database.
        Args:
            ticker (str): The asset ticker.

        Raises:
            AssetNotFoundException: If the asset cannot be found in the database or via APIs.

        Returns:
            Asset: The desired asset object.
        """
        pass

    def trade_asset(self, amount: Decimal, operation: Operation , ticker: str) -> None:
        """
        Handles the buying or selling of an asset within the simulation.

        This centralized method updates the simulation balance, the user's holdings,
        the simulation history, and registers or updates the full asset object in the database
        based on the trade operation. It unifies both buy and sell operations by using
        the `option` parameter.

        Args:
            amount (Decimal): The monetary value to be used for the trade.
            operation (int): Operation type. Use Operation.ADD to buy the asset, Operation.REMOVE to sell the asset.
            ticker (str): The ticker symbol of the asset being traded, used for
                          registration and historical tracking.

        Raises:
            ValueError: If `operation` is not 1 or -1.
            InsufficientFundsError: If trying to buy more than the available balance.
            InsufficientHoldingsError: If trying to sell more than the quantity held.

        Returns:
            None: Successful execution implies the trade has been applied.
        """
        pass

    def reset_month(self) -> None:
        """
        Resets the simulation state for the current month to the last saved state.

        This method restores the holdings and balance to their values after the most
        recent month update, effectively undoing all operations performed in the
        current month except for dividend entries. It also instructs the most recent
        HistoryMonth object to reset its recorded operations accordingly.

        Returns:
            None
        """
        pass

    def advance_month(self) -> None:
        """
        Advances the simulation to the next month.

        This method increments the simulation's current_date by one month and triggers
        all necessary updates for the simulation state, including recalculating
        holdings' values, updating the balance if needed, and recording operations
        in the HistoryMonth object. It ensures that all internal data remains
        consistent after the month advancement.

        Returns:
            None
        """
        pass
