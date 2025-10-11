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

from sqlalchemy.orm import Session
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import logging

from src.backend.models.exchange_rate import ExchangeRateORM
from src.backend.external_apis.yfinance_exchange import YFinanceExchangeAPI
from src.backend.schemas.exchange import (
    ExchangeRateResponse,
    ExchangeRateHistory,
    MonthlyExchangeRate
)

logger = logging.getLogger(__name__)


class ExchangeService:
    """
    Service layer for managing exchange rate operations.

    This service implements an intelligent caching strategy:
    1. Check database cache first for requested rate
    2. If not found, fetch ALL historical data from Yahoo Finance
    3. Store all monthly rates in database for future use
    4. Return the requested rate

    This approach minimizes API calls while ensuring data completeness.
    All data is stored with forward fill applied to eliminate gaps.

    Benefits:
        - First query: ~2-10s (fetches all historical data)
        - Subsequent queries: ~50ms (database lookup)
        - No gaps in data (forward fill ensures continuity)
        - Supports any currency pair available on Yahoo Finance

    Example:
        >>> from sqlalchemy.orm import Session
        >>> rate = ExchangeService.get_exchange_rate(
        ...     db=session,
        ...     from_currency='USD',
        ...     to_currency='BRL',
        ...     target_date=date(2024, 1, 15)
        ... )
        >>> print(f"Rate: {rate.rate}")
        Rate: 4.8756
    """

    @staticmethod
    def get_exchange_rate(
            db: Session,
            from_currency: str,
            to_currency: str,
            target_date: date
    ) -> ExchangeRateResponse:
        """
        Get exchange rate for a specific date with intelligent caching.

        Lookup Strategy:
            1. Normalize currencies to uppercase
            2. Handle same-currency case (return 1.0)
            3. Check database cache for month containing target date
            4. If cache miss: fetch ALL historical data from Yahoo Finance
            5. Store all fetched data in database
            6. Return requested rate

        The service fetches ALL historical data on first miss to populate
        the cache comprehensively, making all future queries instant.

        Args:
            db: Database session for queries and transactions
            from_currency: Source currency code (ISO 4217, e.g., 'USD')
            to_currency: Target currency code (ISO 4217, e.g., 'BRL')
            target_date: Date for which to retrieve the exchange rate

        Returns:
            ExchangeRateResponse containing:
                - rate: Primary exchange rate (close price)
                - open, high, low: Monthly OHLC data
                - yfinance_symbol: Symbol used
                - from_cache: Whether data came from cache

        Raises:
            ValueError: If no exchange rate data can be found

        Example:
            >>> rate = ExchangeService.get_exchange_rate(
            ...     db=session,
            ...     from_currency='USD',
            ...     to_currency='BRL',
            ...     target_date=date(2024, 1, 15)
            ... )
            >>> print(f"1 USD = {rate.rate} BRL")
            1 USD = 4.8756 BRL
        """
        # Normalize currency codes
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        logger.info(
            f"Exchange rate request: {from_currency}/{to_currency} "
            f"for {target_date}"
        )

        # Handle same currency case
        if from_currency == to_currency:
            logger.debug("Same currency requested, returning rate 1.0")
            return ExchangeRateResponse(
                from_currency=from_currency,
                to_currency=to_currency,
                date=target_date,
                rate=Decimal("1.0"),
                open=Decimal("1.0"),
                high=Decimal("1.0"),
                low=Decimal("1.0"),
                yfinance_symbol=f"{from_currency}{to_currency}=X",
                from_cache=True
            )

        # Normalize date to first day of month (monthly data)
        month_start = target_date.replace(day=1)

        # Attempt cache lookup
        cached_rate = ExchangeService._lookup_cached_rate(
            db, from_currency, to_currency, month_start
        )

        if cached_rate:
            logger.info(
                f"Cache HIT: {from_currency}/{to_currency} on {month_start}"
            )
            return ExchangeRateResponse(
                from_currency=cached_rate.from_currency,
                to_currency=cached_rate.to_currency,
                date=cached_rate.date,
                rate=cached_rate.close,
                open=cached_rate.open,
                high=cached_rate.high,
                low=cached_rate.low,
                yfinance_symbol=cached_rate.yfinance_symbol,
                from_cache=True
            )

        # Cache miss - fetch all historical data
        logger.info(
            f"Cache MISS: Fetching all historical data for "
            f"{from_currency}/{to_currency} from Yahoo Finance"
        )

        return ExchangeService._fetch_and_cache_all_rates(
            db, from_currency, to_currency, target_date, month_start
        )

    @staticmethod
    def _lookup_cached_rate(
            db: Session,
            from_currency: str,
            to_currency: str,
            month_start: date
    ) -> Optional[ExchangeRateORM]:
        """
        Look up exchange rate in database cache.

        Args:
            db: Database session
            from_currency: Source currency
            to_currency: Target currency
            month_start: First day of month to look up

        Returns:
            ExchangeRateORM if found, None otherwise
        """
        return db.query(ExchangeRateORM).filter(
            ExchangeRateORM.from_currency == from_currency,
            ExchangeRateORM.to_currency == to_currency,
            ExchangeRateORM.date == month_start
        ).first()

    @staticmethod
    def _fetch_and_cache_all_rates(
            db: Session,
            from_currency: str,
            to_currency: str,
            target_date: date,
            month_start: date
    ) -> ExchangeRateResponse:
        """
        Fetch ALL historical rates from Yahoo Finance and cache them.

        This method fetches complete historical data from 2000-01-01 to today,
        stores all monthly rates in the database, and returns the requested rate.

        Args:
            db: Database session
            from_currency: Source currency
            to_currency: Target currency
            target_date: Original target date
            month_start: Normalized month start for target date

        Returns:
            ExchangeRateResponse for the requested date

        Raises:
            ValueError: If no data available or fetch fails
        """
        try:
            # Fetch ALL monthly rates from Yahoo Finance
            monthly_rates = YFinanceExchangeAPI.fetch_monthly_rates(
                from_currency=from_currency,
                to_currency=to_currency,
                start_date=date(2000, 1, 1),
                end_date=date.today()
            )

            if not monthly_rates:
                raise ValueError(
                    f"No exchange rate data available for {from_currency}/{to_currency}"
                )

            logger.info(f"Fetched {len(monthly_rates)} monthly rates from Yahoo Finance")

            # Store all rates in database
            saved_count = ExchangeService._cache_rates(
                db, from_currency, to_currency, monthly_rates
            )

            logger.info(f"Cached {saved_count} new exchange rates in database")

            # Retrieve the specific rate that was requested
            requested_rate = ExchangeService._lookup_cached_rate(
                db, from_currency, to_currency, month_start
            )

            if not requested_rate:
                # If exact month not found, get closest previous month
                requested_rate = db.query(ExchangeRateORM).filter(
                    ExchangeRateORM.from_currency == from_currency,
                    ExchangeRateORM.to_currency == to_currency,
                    ExchangeRateORM.date <= month_start
                ).order_by(ExchangeRateORM.date.desc()).first()

                if not requested_rate:
                    raise ValueError(
                        f"No exchange rate found for {from_currency}/{to_currency} "
                        f"at or before {target_date}"
                    )

            return ExchangeRateResponse(
                from_currency=requested_rate.from_currency,
                to_currency=requested_rate.to_currency,
                date=requested_rate.date,
                rate=requested_rate.close,
                open=requested_rate.open,
                high=requested_rate.high,
                low=requested_rate.low,
                yfinance_symbol=requested_rate.yfinance_symbol,
                from_cache=False  # Just fetched
            )

        except Exception as e:
            logger.error(f"Failed to fetch exchange rate: {str(e)}")
            raise ValueError(f"Failed to get exchange rate: {str(e)}")

    @staticmethod
    def _cache_rates(
            db: Session,
            from_currency: str,
            to_currency: str,
            monthly_rates: List[dict]
    ) -> int:
        """
        Store monthly exchange rates in database cache.

        Skips rates that already exist (handles concurrent requests gracefully).

        Args:
            db: Database session
            from_currency: Source currency
            to_currency: Target currency
            monthly_rates: List of rate dictionaries from Yahoo Finance

        Returns:
            Number of new rates saved
        """
        saved_count = 0

        for rate_data in monthly_rates:
            # Convert date string to date object
            rate_date = datetime.fromisoformat(rate_data['date']).date()

            # Check if already exists (handle concurrent requests)
            existing = ExchangeService._lookup_cached_rate(
                db, from_currency, to_currency, rate_date
            )

            if not existing:
                # Create new rate entry
                new_rate = ExchangeRateORM(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    date=rate_date,
                    open=Decimal(str(rate_data['open'])),
                    high=Decimal(str(rate_data['high'])),
                    low=Decimal(str(rate_data['low'])),
                    close=Decimal(str(rate_data['close'])),
                    yfinance_symbol=rate_data['symbol']
                )
                db.add(new_rate)
                saved_count += 1

        # Commit all new rates
        db.commit()

        return saved_count

    @staticmethod
    def get_exchange_history(
            db: Session,
            from_currency: str,
            to_currency: str,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> ExchangeRateHistory:
        """
        Get complete historical exchange rate data for a currency pair.

        Returns all cached monthly exchange rates within the specified date range.
        If no data exists in cache, triggers a fetch from Yahoo Finance first.

        Args:
            db: Database session
            from_currency: Source currency code (ISO 4217)
            to_currency: Target currency code (ISO 4217)
            start_date: Start date for history (optional)
            end_date: End date for history (optional)

        Returns:
            ExchangeRateHistory containing:
                - from_currency: Source currency
                - to_currency: Target currency
                - yfinance_symbol: Symbol used
                - data: List of monthly rates ordered by date

        Example:
            >>> history = ExchangeService.get_exchange_history(
            ...     db=session,
            ...     from_currency='USD',
            ...     to_currency='BRL',
            ...     start_date=date(2023, 1, 1),
            ...     end_date=date(2023, 12, 31)
            ... )
            >>> len(history.data)  # 12 months
            12
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        logger.info(
            f"Exchange history request: {from_currency}/{to_currency} "
            f"from {start_date} to {end_date}"
        )

        # Build query
        query = db.query(ExchangeRateORM).filter(
            ExchangeRateORM.from_currency == from_currency,
            ExchangeRateORM.to_currency == to_currency
        )

        if start_date:
            query = query.filter(ExchangeRateORM.date >= start_date)
        if end_date:
            query = query.filter(ExchangeRateORM.date <= end_date)

        rates = query.order_by(ExchangeRateORM.date).all()

        # If no data, trigger fetch to populate cache
        if not rates:
            logger.info("No cached history found, triggering fetch")
            ExchangeService.get_exchange_rate(
                db,
                from_currency,
                to_currency,
                end_date or date.today()
            )

            # Query again after population
            rates = query.order_by(ExchangeRateORM.date).all()

        # Convert to schema
        monthly_data = [
            MonthlyExchangeRate(
                date=rate.date,
                open=rate.open,
                high=rate.high,
                low=rate.low,
                close=rate.close
            )
            for rate in rates
        ]

        symbol = rates[0].yfinance_symbol if rates else f"{from_currency}{to_currency}=X"

        logger.info(f"Returning {len(monthly_data)} monthly data points")

        return ExchangeRateHistory(
            from_currency=from_currency,
            to_currency=to_currency,
            yfinance_symbol=symbol,
            data=monthly_data
        )