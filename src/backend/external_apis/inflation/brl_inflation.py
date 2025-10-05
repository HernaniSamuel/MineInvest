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
from typing import List, Tuple
import requests
from sqlalchemy.orm import Session

from src.backend.external_apis.inflation.base import InflationAPIInterface
from src.backend.models.ipca_cache import IPCACacheORM


class BCBInflationAPI(InflationAPIInterface):
    """
    Brazilian inflation API implementation using IPCA data from Banco Central do Brasil.

    This class fetches and caches IPCA (Índice Nacional de Preços ao Consumidor Amplo)
    data from the Brazilian Central Bank API. It implements intelligent caching to minimize
    API calls while keeping data up-to-date.

    Caching Strategy:
        - First request: Fetches complete historical data from 1980 to present
        - Subsequent requests: Uses cached data from local database
        - Only refetches if database is completely empty

    Publication Schedule:
        IPCA data for month N is published around day 10 of month N+1.
        Example: September 2025 data is published ~October 10, 2025

    Attributes:
        IPCA_SERIES_CODE (str): BCB API series code for IPCA (433)
        BASE_URL (str): Base URL template for BCB API endpoints
        FIRST_IPCA_DATE (date): Start date of IPCA historical data (1980-01-01)
        db (Session): SQLAlchemy database session for cache operations
    """

    IPCA_SERIES_CODE = "433"
    BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados"
    FIRST_IPCA_DATE = date(1980, 1, 1)

    def __init__(self, db_session: Session) -> None:
        """
        Initialize BCB Inflation API with database session.

        Args:
            db_session: SQLAlchemy session for accessing IPCA cache
        """
        self.db = db_session

    def get_accumulated_inflation(
            self,
            currency: str,
            start_date: date,
            end_date: date,
    ) -> Decimal:
        """
        Calculate accumulated inflation rate between two dates using cached IPCA data.

        The method automatically handles:
        - Cache verification and population
        - Data availability based on IPCA publication schedule
        - Month normalization (always uses 1st day of month)

        Args:
            currency: ISO currency code (must be "BRL")
            start_date: Beginning of inflation period (simulation date)
            end_date: End of inflation period (typically today)

        Returns:
            Accumulated inflation as a multiplier (e.g., 1.15 = 15% inflation)

        Raises:
            ValueError: If currency is not "BRL" or if no data available for date range

        Example:
            >>> api = BCBInflationAPI(db_session)
            >>> multiplier = api.get_accumulated_inflation(
            ...     currency="BRL",
            ...     start_date=date(2023, 1, 1),
            ...     end_date=date(2024, 1, 1)
            ... )
            >>> # If inflation was 4.5%, multiplier = 1.045
        """
        if currency.upper() != "BRL":
            raise ValueError(f"BCB API only supports BRL, got {currency}")

        if start_date > end_date:
            return Decimal("1.0")

        # Normalize to first day of month
        start_month = start_date.replace(day=1)
        end_month = end_date.replace(day=1)

        # Adjust end date based on IPCA publication schedule
        adjusted_end = self._get_adjusted_end_date(end_month)

        # Fetch from API only if cache is empty
        if self._is_cache_empty():
            self._fetch_and_cache_all_ipca()

        # Calculate using available cached data
        return self._calculate_from_cache(start_month, adjusted_end)

    def _get_adjusted_end_date(self, end_month: date) -> date:
        """
        Adjust end date based on IPCA publication schedule.

        IPCA Publication Rules:
            - Data for month N is published around day 10 of month N+1
            - Before day 10: Use data from 2 months ago (N-2)
            - On/after day 10: Use data from last month (N-1)

        Args:
            end_month: Requested end month (normalized to 1st day)

        Returns:
            Adjusted end month based on data availability

        Examples:
            Today: Oct 4, 2025 (before 10th)
            → Returns: Aug 2025 (Sep data not published yet)

            Today: Oct 15, 2025 (after 10th)
            → Returns: Sep 2025 (Sep data now available)
        """
        today = date.today()

        # Cap at current month if requesting future data
        if end_month > today.replace(day=1):
            end_month = today.replace(day=1)

        # Before 10th: Last month's data (N-1) not yet published, use N-2
        if today.day < 10:
            current_month = today.replace(day=1)

            # Handle year boundary (January/February)
            if current_month.month <= 2:
                months_back = current_month.month + 10
                end_month = date(
                    current_month.year - 1,
                    12 - (months_back - current_month.month),
                    1
                )
            else:
                end_month = current_month.replace(month=current_month.month - 2)

            print(f"Warning: Using IPCA data through {end_month.strftime('%Y-%m')} "
                  f"(last month's data not yet published, today is {today.strftime('%Y-%m-%d')})")

        # On/after 10th: Last month's data (N-1) is available
        elif end_month >= today.replace(day=1):
            if today.month == 1:
                end_month = date(today.year - 1, 12, 1)
            else:
                end_month = today.replace(day=1, month=today.month - 1)

        return end_month

    def _is_cache_empty(self) -> bool:
        """
        Check if IPCA cache is empty.

        Returns:
            True if no cached data exists, False otherwise
        """
        count = self.db.query(IPCACacheORM).count()
        return count == 0

    def _fetch_and_cache_all_ipca(self) -> None:
        """
        Fetch complete IPCA historical data from BCB API and store in cache.

        This method:
            1. Requests all IPCA data from 1980 to present
            2. Clears existing cache
            3. Stores all monthly data in database
            4. Commits transaction

        The fetch is performed only when cache is completely empty, ensuring
        minimal API usage while maintaining data availability.

        Raises:
            ConnectionError: If API request fails
            ValueError: If API response format is invalid

        Side Effects:
            - Deletes all existing cache entries
            - Inserts 500+ new cache entries
            - Commits database transaction
        """
        print("Fetching complete IPCA history from BCB")

        start_str = self.FIRST_IPCA_DATE.strftime("%d/%m/%Y")
        end_str = date.today().strftime("%d/%m/%Y")

        url = self.BASE_URL.format(self.IPCA_SERIES_CODE)
        params = {
            "formato": "json",
            "dataInicial": start_str,
            "dataFinal": end_str
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Clear existing cache to avoid duplicates
            self.db.query(IPCACacheORM).delete()

            # Parse and store each monthly IPCA value
            for entry in data:
                # BCB API date format: "dd/MM/yyyy"
                month_str = entry["data"]
                day, month, year = map(int, month_str.split("/"))
                month_date = date(year, month, 1)  # Normalize to 1st

                ipca_value = entry["valor"]

                cache_entry = IPCACacheORM(
                    month_date=month_date,
                    ipca_value=ipca_value
                )
                self.db.add(cache_entry)

            self.db.commit()
            print(f"Cached {len(data)} months of IPCA data")

        except requests.RequestException as e:
            self.db.rollback()
            raise ConnectionError(f"Failed to fetch IPCA data: {e}")
        except (KeyError, ValueError) as e:
            self.db.rollback()
            raise ValueError(f"Invalid API response format: {e}")

    def _calculate_from_cache(self, start_date: date, end_date: date) -> Decimal:
        """
        Calculate accumulated inflation multiplier from cached IPCA data.

        Retrieves monthly IPCA values for the specified period and compounds them
        to calculate total accumulated inflation.

        Args:
            start_date: Beginning of period (normalized to 1st of month)
            end_date: End of period (normalized to 1st of month)

        Returns:
            Accumulated inflation multiplier

        Raises:
            ValueError: If no cached data exists for requested period

        Formula:
            accumulated = (1 + r₁) × (1 + r₂) × ... × (1 + rₙ)
            where rᵢ = monthly IPCA rate / 100

        Example:
            Month 1: 0.5% → 1.005
            Month 2: 0.4% → 1.004
            Accumulated: 1.005 × 1.004 = 1.009020 (~0.9% total)
        """
        records = self.db.query(IPCACacheORM).filter(
            IPCACacheORM.month_date >= start_date,
            IPCACacheORM.month_date <= end_date
        ).order_by(IPCACacheORM.month_date).all()

        if not records:
            # Provide helpful error with latest available data
            latest = self.db.query(IPCACacheORM).order_by(
                IPCACacheORM.month_date.desc()
            ).first()

            latest_str = latest.month_date.strftime('%Y-%m') if latest else "none"

            raise ValueError(
                f"No IPCA data in cache for {start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}. "
                f"Latest available data: {latest_str}"
            )

        # Log actual data range being used
        actual_start = records[0].month_date
        actual_end = records[-1].month_date
        print(f"Using IPCA data from {actual_start.strftime('%Y-%m')} to {actual_end.strftime('%Y-%m')}")

        # Compound monthly rates
        accumulated = Decimal("1.0")
        for record in records:
            monthly_rate = Decimal(record.ipca_value) / Decimal("100")
            accumulated *= (Decimal("1.0") + monthly_rate)

        return accumulated