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


class Asset:
    """
    Represents a financial asset with historical monthly data and associated metadata.

    This class stores key information about an asset, including its name, ticker symbol,
    current price, monthly historical data (OHLC, dividends, splits), and the period
    for which the data is available. It also records the base currency of the asset.

    Attributes:
        name (str): The full name of the asset.
        ticker (str): The unique ticker symbol used to identify the asset.
        price (Decimal): The current price of the asset.
        monthly_data (dict): Historical monthly data, structured as a dictionary
                             where each key is a month (date) and the value contains
                             OHLC, dividends, and splits.
        start_date (date): The first date for which historical data is available.
        end_date (date): The last date for which historical data is available.
        base_currency (str): The currency in which the asset is denominated.

    Example:
        monthly_data = {
            date(2025, 1, 1): {
                "open": Decimal("10.50"),
                "high": Decimal("12.00"),
                "low": Decimal("10.25"),
                "close": Decimal("11.75"),
                "dividends": Decimal("0.10"),
                "split": 1
            }
        }

        asset = Asset(
            name="Example Corp",
            ticker="EXC",
            price=Decimal("11.75"),
            monthly_data=monthly_data,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            base_currency="BRL"
        )
    """
    def __init__(self, name: str, ticker: str, price: Decimal, monthly_data: dict, start_date: date, end_date: date, base_currency: str) -> None:
        self.name: str = name
        self.ticker: str = ticker
        self.price: Decimal = price
        self.monthly_data: dict = monthly_data
        self.start_date: date = start_date
        self.end_date: date = end_date
        self.base_currency: str = base_currency
