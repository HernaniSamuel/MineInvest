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
from datetime import date
from typing import Optional

class Holding:
    """
    Represents a purchased asset within a portfolio.

    Stores information about a specific holding, including ticker, name,
    base currency, quantity, purchase price, weight, current price, and
    monetary value.

    Attributes:
        ticker (str): The ticker symbol of the asset.
        name (str): The full name of the asset.
        base_currency (str): The base currency of the asset.
        quantity (Decimal): The amount of the asset held.
        purchase_price (Decimal): Price at first purchase (converted to portfolio currency).
        weight (Decimal): The proportion of the portfolio represented by this holding.
        current_price (Decimal): Current price of the asset (converted) in the current simulation month.
        market_value (Decimal): Monetary value of this holding (current_price * quantity).
    """

    def __init__(self, ticker: str, name: str, base_currency: str,
                 quantity: Decimal, purchase_price: Decimal,
                 weight: Decimal, current_price: Decimal,
                 market_value: Decimal) -> None:
        self.ticker: str = ticker
        self.name: str = name
        self.base_currency: str = base_currency
        self.quantity: Decimal = quantity
        self.purchase_price: Decimal = purchase_price
        self.weight: Decimal = weight
        self.current_price: Decimal = current_price
        self.market_value: Decimal = market_value

    def update_price(self, current_month: date) -> Decimal:
        """
        Updates the current price of the asset for the given month.

        This method should fetch the monthly price from the database or API
        and convert it to the portfolio's base currency.

        Args:
            current_month (date): The month for which to fetch the asset price.

        Returns:
            Decimal: The updated current price rounded to two decimal places.
        """
        # TODO: implement price fetching and conversion
        return self.current_price

    def update_market_value(self, current_price: Decimal, quantity: Decimal) -> Decimal:
        """
        Updates the monetary value of the holding.

        Args:
            current_price (Decimal): Current price of the asset.
            quantity (Decimal): Quantity of the asset held.

        Returns:
            Decimal: Updated market value (current_price * quantity) rounded to two decimal places.
        """
        self.market_value = round(current_price * quantity, 2)
        return self.market_value

    def update_weight(self, new_weight: Decimal) -> None:
        """
        Updates the weight of the asset in the portfolio.

        Args:
            new_weight (Decimal): New weight value to assign.
        """
        self.weight = new_weight

    def update_quantity(self, new_quantity: Decimal) -> None:
        """
        Updates the quantity of the asset held.

        Args:
            new_quantity (Decimal): New quantity to assign.
        """
        self.quantity = new_quantity
