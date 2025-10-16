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

import yfinance as yf
from datetime import date
from typing import List, Dict, Tuple, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class YFinanceExchangeAPI:
    """
    Yahoo Finance API wrapper for fetching historical exchange rate data.

    This class handles all interactions with Yahoo Finance for currency pair data,
    including symbol construction, data fetching, and rate inversion when necessary.

    Symbol Format:
        Yahoo Finance uses the format: XXXYYY=X
        - XXX: Source currency (e.g., USD)
        - YYY: Target currency (e.g., BRL)
        - =X: Forex indicator

        Examples:
            - USDBRL=X: US Dollar to Brazilian Real
            - EURBRL=X: Euro to Brazilian Real
            - GBPUSD=X: British Pound to US Dollar

    Data Strategy:
        - Fetches daily data and resamples to monthly using first day of month
        - Uses forward fill to eliminate gaps in data
        - Attempts direct symbol first, then tries inverse if not found
        - Returns OHLC (Open, High, Low, Close) data for each month
    """

    @staticmethod
    def build_currency_symbol(from_currency: str, to_currency: str) -> str:
        """
        Build Yahoo Finance symbol for a currency pair.

        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'BRL')

        Returns:
            Yahoo Finance symbol (e.g., 'USDBRL=X')

        Example:
            >>> YFinanceExchangeAPI.build_currency_symbol('USD', 'BRL')
            'USDBRL=X'
        """
        return f"{from_currency}{to_currency}=X"

    @staticmethod
    def fetch_monthly_rates(
            from_currency: str,
            to_currency: str,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> List[Dict]:
        """
        Fetch monthly exchange rates from Yahoo Finance with forward fill.

        This method fetches daily exchange rate data and resamples it to monthly
        intervals. Missing data is filled using forward fill to ensure continuous
        time series without gaps.

        Process:
            1. Attempt to fetch data with direct symbol (XXXYYY=X)
            2. If no data, try inverse symbol (YYYXXX=X) and invert rates
            3. Resample daily data to monthly (first day of month)
            4. Apply forward fill to eliminate gaps
            5. Return structured monthly OHLC data

        Args:
            from_currency: Source currency code (ISO 4217)
            to_currency: Target currency code (ISO 4217)
            start_date: Start date for historical data (default: 2000-01-01)
            end_date: End date for historical data (default: today)

        Returns:
            List of dictionaries containing monthly exchange rate data:
            [
                {
                    'date': '2024-01-01',
                    'open': 4.8532,
                    'high': 4.9123,
                    'low': 4.8234,
                    'close': 4.8756,
                    'symbol': 'USDBRL=X'
                },
                ...
            ]

        Raises:
            ValueError: If no exchange rate data can be found for the currency pair

        Example:
            >>> rates = YFinanceExchangeAPI.fetch_monthly_rates('USD', 'BRL')
            >>> len(rates) > 0
            True
            >>> rates[0]['symbol']
            'USDBRL=X'
        """
        # Handle same currency case
        if from_currency == to_currency:
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = date(2000, 1, 1)

            logger.info(f"Same currency ({from_currency}), returning rate of 1.0")
            return [{
                'date': start_date.replace(day=1).isoformat(),
                'open': 1.0,
                'high': 1.0,
                'low': 1.0,
                'close': 1.0,
                'symbol': f"{from_currency}{to_currency}=X"
            }]

        # Build primary and fallback symbols
        direct_symbol = YFinanceExchangeAPI.build_currency_symbol(from_currency, to_currency)
        inverse_symbol = YFinanceExchangeAPI.build_currency_symbol(to_currency, from_currency)

        # Set default dates
        if not start_date:
            start_date = date(2000, 1, 1)
        if not end_date:
            end_date = date.today()

        logger.info(
            f"Fetching exchange rates: {from_currency}/{to_currency} "
            f"from {start_date} to {end_date}"
        )

        # Try direct symbol first
        hist, needs_inversion = YFinanceExchangeAPI._fetch_symbol_data(
            direct_symbol, start_date, end_date
        )

        # If direct failed, try inverse
        if hist.empty:
            logger.info(f"Direct symbol {direct_symbol} failed, trying inverse {inverse_symbol}")
            hist, _ = YFinanceExchangeAPI._fetch_symbol_data(
                inverse_symbol, start_date, end_date
            )
            needs_inversion = True

            if hist.empty:
                raise ValueError(
                    f"No exchange rate data found for {from_currency}/{to_currency}. "
                    f"Tried symbols: {direct_symbol}, {inverse_symbol}"
                )

        # Resample to monthly with forward fill
        monthly_data = YFinanceExchangeAPI._resample_to_monthly(hist, needs_inversion)

        # Format results
        result = []
        for date_idx, row in monthly_data.iterrows():
            result.append({
                'date': date_idx.date().isoformat(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'symbol': direct_symbol  # Always return normalized symbol
            })

        logger.info(f"Successfully fetched {len(result)} monthly data points")
        return result

    @staticmethod
    def _fetch_symbol_data(
            symbol: str,
            start_date: date,
            end_date: date
    ) -> Tuple[pd.DataFrame, bool]:
        """
        Fetch daily data for a specific Yahoo Finance symbol.

        Args:
            symbol: Yahoo Finance symbol (e.g., 'USDBRL=X')
            start_date: Start date
            end_date: End date

        Returns:
            Tuple of (DataFrame with OHLC data, False)
            Returns empty DataFrame if fetch fails
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date, interval="1d")
            logger.debug(f"Fetched {len(hist)} daily records for {symbol}")
            return hist, False
        except Exception as e:
            logger.warning(f"Failed to fetch {symbol}: {str(e)}")
            return pd.DataFrame(), False

    @staticmethod
    def _resample_to_monthly(
            hist: pd.DataFrame,
            needs_inversion: bool
    ) -> pd.DataFrame:
        """
        Resample daily data to monthly with forward fill.

        This method:
        1. Resamples daily OHLC data to monthly intervals (first day of month)
        2. Applies forward fill to eliminate gaps in the time series
        3. Inverts rates if necessary (for inverse currency pairs)

        Args:
            hist: DataFrame with daily OHLC data from Yahoo Finance
            needs_inversion: If True, invert all rates (1/rate)

        Returns:
            DataFrame with monthly OHLC data, no gaps

        Note:
            When inverting rates, high and low are swapped (1/low becomes high)
        """
        # Ensure datetime index
        hist.index = pd.to_datetime(hist.index)

        # Resample to monthly (first day of month)
        monthly = hist.resample('MS').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        })

        # Apply forward fill to eliminate gaps
        monthly = monthly.ffill()

        # Invert rates if needed
        if needs_inversion:
            logger.debug("Inverting exchange rates (inverse symbol)")
            # When inverting, low becomes high and vice versa
            monthly_inverted = monthly.copy()
            monthly_inverted['Open'] = 1.0 / monthly['Open']
            monthly_inverted['High'] = 1.0 / monthly['Low']  # Note the swap
            monthly_inverted['Low'] = 1.0 / monthly['High']  # Note the swap
            monthly_inverted['Close'] = 1.0 / monthly['Close']
            return monthly_inverted

        return monthly

    @staticmethod
    def fetch_rate_for_date(
            from_currency: str,
            to_currency: str,
            target_date: date
    ) -> Optional[Dict]:
        """
        Fetch exchange rate for a specific date.

        This is a convenience method that fetches the monthly rate
        for the month containing the target date.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            target_date: Date to fetch rate for

        Returns:
            Dictionary with monthly rate data, or None if not found

        Example:
            >>> rate = YFinanceExchangeAPI.fetch_rate_for_date(
            ...     'USD', 'BRL', date(2024, 1, 15)
            ... )
            >>> rate['close']  # Rate for January 2024
            4.8756
        """
        # Fetch data for the month containing target date
        start_of_month = target_date.replace(day=1)
        end_of_month = target_date

        rates = YFinanceExchangeAPI.fetch_monthly_rates(
            from_currency,
            to_currency,
            start_date=start_of_month,
            end_date=end_of_month
        )

        if rates:
            return rates[-1]  # Return latest available rate

        return None
