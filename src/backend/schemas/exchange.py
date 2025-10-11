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

from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import date as date_type
from typing import Optional


class ExchangeRateBase(BaseModel):
    """
    Base schema for exchange rate data.

    Contains the minimal information needed to identify and request
    an exchange rate between two currencies on a specific date.

    Attributes:
        from_currency: Source currency code (ISO 4217, e.g., 'USD')
        to_currency: Target currency code (ISO 4217, e.g., 'BRL')
        date: Date for which to retrieve the exchange rate
    """
    from_currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Source currency code (ISO 4217)"
    )
    to_currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Target currency code (ISO 4217)"
    )
    date: date_type = Field(
        ...,
        description="Date for the exchange rate"
    )

    @field_validator('from_currency', 'to_currency')
    @classmethod
    def validate_currency_uppercase(cls, v: str) -> str:
        """
        Ensure currency codes are uppercase for consistency.

        Args:
            v: Currency code to validate

        Returns:
            Uppercase currency code
        """
        return v.upper()


class ExchangeRateRequest(ExchangeRateBase):
    """
    Request schema for fetching exchange rates.

    Used when clients request historical exchange rate data
    for a specific currency pair and date.
    """
    pass


class ExchangeRateResponse(ExchangeRateBase):
    """
    Response schema containing exchange rate data.

    Includes the requested exchange rate plus additional metadata
    about the data source and OHLC values for the month.

    Attributes:
        rate: Primary exchange rate (close price) to use for calculations
        open: Opening rate for the month
        high: Highest rate during the month
        low: Lowest rate during the month
        yfinance_symbol: Yahoo Finance symbol used to fetch the data
        from_cache: Whether this data came from database cache or was freshly fetched
    """
    rate: Decimal = Field(
        ...,
        description="Primary exchange rate (close price)"
    )
    open: Optional[Decimal] = Field(
        None,
        description="Opening exchange rate for the month"
    )
    high: Optional[Decimal] = Field(
        None,
        description="Highest exchange rate during the month"
    )
    low: Optional[Decimal] = Field(
        None,
        description="Lowest exchange rate during the month"
    )
    yfinance_symbol: Optional[str] = Field(
        None,
        description="Yahoo Finance symbol used (e.g., 'USDBRL=X')"
    )
    from_cache: bool = Field(
        default=False,
        description="True if data retrieved from database cache"
    )

    class Config:
        from_attributes = True


class MonthlyExchangeRate(BaseModel):
    """
    Monthly OHLC exchange rate data point.

    Represents a complete month's worth of exchange rate data
    with open, high, low, and close values.

    Attributes:
        date: First day of the month
        open: Opening rate
        high: Highest rate
        low: Lowest rate
        close: Closing rate (primary value used)
    """
    date: date_type = Field(
        ...,
        description="First day of the month"
    )
    open: Decimal = Field(
        ...,
        description="Opening exchange rate"
    )
    high: Decimal = Field(
        ...,
        description="Highest exchange rate"
    )
    low: Decimal = Field(
        ...,
        description="Lowest exchange rate"
    )
    close: Decimal = Field(
        ...,
        description="Closing exchange rate"
    )

    class Config:
        from_attributes = True


class ExchangeRateHistory(BaseModel):
    """
    Complete historical exchange rate data for a currency pair.

    Contains all monthly exchange rate data points for a given
    currency pair, useful for charting and historical analysis.

    Attributes:
        from_currency: Source currency code
        to_currency: Target currency code
        yfinance_symbol: Yahoo Finance symbol used
        data: List of monthly exchange rate data points, ordered by date
    """
    from_currency: str = Field(
        ...,
        description="Source currency code (ISO 4217)"
    )
    to_currency: str = Field(
        ...,
        description="Target currency code (ISO 4217)"
    )
    yfinance_symbol: str = Field(
        ...,
        description="Yahoo Finance symbol (e.g., 'USDBRL=X')"
    )
    data: list[MonthlyExchangeRate] = Field(
        ...,
        description="Monthly exchange rate data points, ordered by date"
    )

    class Config:
        from_attributes = True