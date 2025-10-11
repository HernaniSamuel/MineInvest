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

from sqlalchemy import Column, Integer, String, Numeric, Date, UniqueConstraint, Index
from sqlalchemy.orm import validates
from src.backend.models.base import Base


class ExchangeRateORM(Base):
    """
    ORM model for storing historical exchange rates between currency pairs.

    This model stores monthly OHLC (Open, High, Low, Close) data for currency pairs
    to minimize external API calls. Data is cached from Yahoo Finance and reused
    for all future queries within the same month.

    Attributes:
        id (int): Primary key
        from_currency (str): Source currency code (ISO 4217, e.g., 'USD')
        to_currency (str): Target currency code (ISO 4217, e.g., 'BRL')
        date (date): First day of the month for this exchange rate
        open (Decimal): Opening exchange rate for the month
        high (Decimal): Highest exchange rate during the month
        low (Decimal): Lowest exchange rate during the month
        close (Decimal): Closing exchange rate for the month (primary rate used)
        yfinance_symbol (str): Yahoo Finance symbol used (e.g., 'USDBRL=X')

    Constraints:
        - Unique constraint on (from_currency, to_currency, date) to prevent duplicates
        - Multi-column index on (from_currency, to_currency, date) for fast lookups

    Example:
        >>> rate = ExchangeRateORM(
        ...     from_currency='USD',
        ...     to_currency='BRL',
        ...     date=date(2024, 1, 1),
        ...     open=Decimal('4.8532'),
        ...     high=Decimal('4.9123'),
        ...     low=Decimal('4.8234'),
        ...     close=Decimal('4.8756'),
        ...     yfinance_symbol='USDBRL=X'
        ... )
    """
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, index=True)

    # Currency pair (ISO 4217 codes)
    from_currency = Column(String(3), nullable=False, index=True)
    to_currency = Column(String(3), nullable=False, index=True)

    # Date (always first day of month for monthly data)
    date = Column(Date, nullable=False, index=True)

    # Monthly OHLC data
    open = Column(Numeric(precision=18, scale=8), nullable=False)
    high = Column(Numeric(precision=18, scale=8), nullable=False)
    low = Column(Numeric(precision=18, scale=8), nullable=False)
    close = Column(Numeric(precision=18, scale=8), nullable=False)

    # Yahoo Finance symbol (e.g., 'USDBRL=X')
    yfinance_symbol = Column(String(10), nullable=False)

    # Table constraints
    __table_args__ = (
        UniqueConstraint('from_currency', 'to_currency', 'date', name='uq_currency_pair_date'),
        Index('idx_currency_pair_date', 'from_currency', 'to_currency', 'date'),
    )

    @validates('from_currency', 'to_currency')
    def validate_currency_code(self, key: str, value: str) -> str:
        """
        Validate that currency codes are 3-letter uppercase ISO 4217 codes.

        Args:
            key: Field name being validated
            value: Currency code to validate

        Returns:
            Validated currency code

        Raises:
            ValueError: If currency code is not exactly 3 uppercase letters
        """
        if not value or len(value) != 3 or not value.isupper():
            raise ValueError(f"{key} must be a 3-letter uppercase ISO 4217 currency code")
        return value

    def __repr__(self) -> str:
        """String representation of the exchange rate."""
        return (
            f"<ExchangeRate {self.from_currency}/{self.to_currency} "
            f"on {self.date}: {self.close}>"
        )