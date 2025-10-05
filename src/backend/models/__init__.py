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
from io import StringIO
import csv
import requests
from sqlalchemy.orm import Session

from src.backend.external_apis.inflation.base import InflationAPIInterface
from src.backend.models.cpi_cache import CPICacheORM


class USDInflationAPI(InflationAPIInterface):
    """
    US inflation API implementation using CPI data from FRED (Federal Reserve Economic Data).

    This class fetches and caches CPI-U (Consumer Price Index for All Urban Consumers)
    data from the Federal Reserve Bank of St. Louis FRED API. It implements intelligent
    caching to minimize API calls while keeping data up-to-date.

    Caching Strategy:
        - First request: Fetches complete historical CPI data
        - Subsequent requests: Uses cached data from local database
        - Only refetches if database is completely empty

    Publication Schedule:
        CPI data for month N is published around day 12-15 of month N+1.
        For safety, we wait until day 20 to ensure data availability.
        Example: September 2025 data is published ~October 12-15, 2025

    Attributes:
        CPI_SERIES_ID (str): FRED series identifier for CPI-U (CPIAUCSL)
        FRED_CSV_URL (str): Direct CSV download URL from FRED
        SAFE_PUBLICATION_DAY (int): Conservative day to assume new data (20th)
        db (Session): SQLAlchemy database session for cache operations
    """

    CPI_SERIES_ID = "CPIAUCSL"
    FRED_CSV_URL = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={CPI_SERIES_ID}"
    SAFE_PUBLICATION_DAY = 20

    def __init__(self, db_session: Session) -> None:
        """
        Initialize USD Inflation API with database session.

        Args:
            db_session: SQLAlchemy session for accessing CPI cache
        """
        self.db = db_session

    def get_accumulated_inflation(
            self,
            currency: str,
            start_date: date,
            end_date: date,
    ) -> Decimal:
        """
        Calculate accumulated inflation rate between two dates using cached CPI data.

        The method automatically handles:
        - Cache verification and population
        - Data availability based on CPI publication schedule
        - Month normalization (always uses 1st day of month)
        - Percentage change calculation from CPI index values

        Args:
            currency: ISO currency code (must be "USD")
            start_date: Beginning of inflation period (simulation date)
            end_date: End of inflation period (typically today)

        Returns:
            Accumulated inflation as a multiplier (e.g., 1.15 = 15% inflation)

        Raises:
            ValueError: If currency is not "USD" or if no data available for date range

        Example:
            >>> api = USDInflationAPI(db_session)
            >>> multiplier = api.get_accumulated_inflation(
            ...     currency="USD",
            ...     start_date=date(2023, 1, 1),
            ...     end_date=date(2024, 1, 1)
            ... )
            >>> # If CPI went from 300 to 312, multiplier = 312/300 = 1.04 (4% inflation)
        """
        if currency.upper() != "USD":
            raise ValueError(f"FRED API only supports USD, got {currency}")

        if start_date > end_date:
            return Decimal("1.0")

        # Normalize to first day of month
        start_month = start_date.replace(day=1)
        end_month = end_date.replace(day=1)

        # Adjust end date based on CPI publication schedule
        adjusted_end = self._get_adjusted_end_date(end_month)

        # Fetch from API only if cache is empty
        if self._is_cache_empty():
            self._fetch_and_cache_all_cpi()

        # Calculate using available cached data
        return self._calculate_from_cache(start_month, adjusted_end)

    def _get_adjusted_end_date(self, end_month: date) -> date:
        """
        Adjust end date based on CPI publication schedule.

        CPI Publication Rules:
            - Data for month N is published around day 12-15 of month N+1
            - For safety, we wait until day 20 to ensure availability
            - Before day 20: Use data from 2 months ago (N-2)
            - On/after day 20: Use data from last month (N-1)

        Args:
            end_month: Requested end month (normalized to 1st day)

        Returns:
            Adjusted end month based on data availability

        Examples:
            Today: Oct 15, 2025 (before 20th)
            → Returns: Aug 2025 (Sep data might not be available yet)

            Today: Oct 25, 2025 (after 20th)
            → Returns: Sep 2025 (Sep data definitely available)
        """
        today = date.today()

        # Cap at current month if requesting future data
        if end_month > today.replace(day=1):
            end_month = today.replace(day=1)

        # Before 20th: Last month's data (N-1) might not be published yet, use N-2
        if today.day < self.SAFE_PUBLICATION_DAY:
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

            print(f"Warning: Using CPI data through {end_month.strftime('%Y-%m')} "
                  f"(last month's data not yet published, today is {today.strftime('%Y-%m-%d')})")

        # On/after 20th: Last month's data (N-1) is definitely available
        elif end_month >= today.replace(day=1):
            if today.month == 1:
                end_month = date(today.year - 1, 12, 1)
            else:
                end_month = today.replace(day=1, month=today.month - 1)

        return end_month

    def _is_cache_empty(self) -> bool:
        """
        Check if CPI cache is empty.

        Returns:
            True if no cached data exists, False otherwise
        """
        count = self.db.query(CPICacheORM).count()
        return count == 0

    def _fetch_and_cache_all_cpi(self) -> None:
        """
        Fetch complete CPI historical data from FRED and store in cache.

        This method:
            1. Downloads CSV data from FRED (all available history)
            2. Parses CSV to extract date and CPI index values
            3. Clears existing cache
            4. Stores all monthly data in database
            5. Commits transaction

        The fetch is performed only when cache is completely empty, ensuring
        minimal API usage while maintaining data availability.

        CSV Format from FRED:
            DATE,CPIAUCSL
            1947-01-01,21.48
            1947-02-01,21.62
            ...

        Raises:
            ConnectionError: If FRED request fails
            ValueError: If CSV format is invalid or unparseable

        Side Effects:
            - Deletes all existing cache entries
            - Inserts 900+ new cache entries (data since 1947)
            - Commits database transaction
        """
        print("Fetching complete CPI history from FRED")

        try:
            response = requests.get(self.FRED_CSV_URL, timeout=30)
            response.raise_for_status()

            # Parse CSV content
            csv_content = StringIO(response.text)
            csv_reader = csv.DictReader(csv_content)

            # Clear existing cache to avoid duplicates
            self.db.query(CPICacheORM).delete()

            # Parse and store each monthly CPI value
            records_added = 0
            for row in csv_reader:
                # FRED CSV format: "YYYY-MM-DD" (always 1st of month)
                date_str = row['DATE']
                cpi_value = row['CPIAUCSL']

                # Skip rows with missing data (marked as ".")
                if cpi_value == ".":
                    continue

                # Parse date
                year, month, day = map(int, date_str.split('-'))
                month_date = date(year, month, 1)

                cache_entry = CPICacheORM(
                    month_date=month_date,
                    cpi_value=cpi_value
                )
                self.db.add(cache_entry)
                records_added += 1

            self.db.commit()
            print(f"Cached {records_added} months of CPI data from FRED")

        except requests.RequestException as e:
            self.db.rollback()
            raise ConnectionError(f"Failed to fetch CPI data from FRED: {e}")
        except (KeyError, ValueError) as e:
            self.db.rollback()
            raise ValueError(f"Invalid CSV format from FRED: {e}")

    def _calculate_from_cache(self, start_date: date, end_date: date) -> Decimal:
        """
        Calculate accumulated inflation multiplier from cached CPI index data.

        Unlike percentage-based systems (like IPCA), CPI is an index. Inflation
        is calculated as the ratio between end and start index values.

        Args:
            start_date: Beginning of period (normalized to 1st of month)
            end_date: End of period (normalized to 1st of month)

        Returns:
            Accumulated inflation multiplier

        Raises:
            ValueError: If no cached data exists for requested period

        Formula:
            multiplier = CPI_end / CPI_start

        Example:
            CPI Jan 2023: 300.00
            CPI Jan 2024: 312.00
            Inflation: 312.00 / 300.00 = 1.04 (4% inflation)
        """
        # Get start CPI value
        start_record = self.db.query(CPICacheORM).filter(
            CPICacheORM.month_date == start_date
        ).first()

        # Get end CPI value
        end_record = self.db.query(CPICacheORM).filter(
            CPICacheORM.month_date == end_date
        ).first()

        # Handle missing data
        if not start_record or not end_record:
            latest = self.db.query(CPICacheORM).order_by(
                CPICacheORM.month_date.desc()
            ).first()

            latest_str = latest.month_date.strftime('%Y-%m') if latest else "none"

            missing = []
            if not start_record:
                missing.append(f"start ({start_date.strftime('%Y-%m')})")
            if not end_record:
                missing.append(f"end ({end_date.strftime('%Y-%m')})")

            raise ValueError(
                f"No CPI data in cache for {' and '.join(missing)}. "
                f"Latest available data: {latest_str}"
            )

        # Log actual data range being used
        print(f"Using CPI data: {start_date.strftime('%Y-%m')} "
              f"(index: {start_record.cpi_value}) → "
              f"{end_date.strftime('%Y-%m')} (index: {end_record.cpi_value})")

        # Calculate inflation as ratio of indices
        start_cpi = Decimal(start_record.cpi_value)
        end_cpi = Decimal(end_record.cpi_value)

        if start_cpi == 0:
            raise ValueError(f"Invalid CPI value (zero) for {start_date.strftime('%Y-%m')}")

        multiplier = end_cpi / start_cpi

        return multiplier
