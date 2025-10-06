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
from decimal import Decimal
from src.backend.services.asset_cache import AssetData
import pandas as pd
from dateutil.relativedelta import relativedelta

class YFinanceClient:

    @staticmethod
    def fetch_asset(ticker: str) -> AssetData:
        """Fetch complete historical data with forward fill for missing months."""
        try:
            asset = yf.Ticker(ticker)
            info = asset.info
            name = info.get('longName') or info.get('shortName') or ticker
            currency = info.get('currency', 'USD')

            hist = asset.history(
                period="max",
                auto_adjust=False,
                actions=True
            )

            if hist.empty:
                raise ValueError(f"No data available for {ticker}")

            # Resample to monthly
            hist_monthly = hist.resample('MS').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Dividends': 'sum',
                'Stock Splits': 'prod'
            })

            # Forward fill missing months (CRITICAL for gaps)
            # This propagates last known price forward
            hist_monthly = hist_monthly.ffill()

            # Generate complete month range (no gaps)
            start_date = hist_monthly.index[0]
            end_date = hist_monthly.index[-1]
            complete_range = pd.date_range(start=start_date, end=end_date, freq='MS')

            # Reindex with complete range, forward fill any remaining gaps
            hist_monthly = hist_monthly.reindex(complete_range, method='ffill')

            # Convert to monthly_data list
            monthly_data = []
            for dt, row in hist_monthly.iterrows():
                month_date = dt.date().replace(day=1)

                monthly_data.append({
                    "date": month_date.isoformat(),
                    "open": str(Decimal(str(row['Open'])).quantize(Decimal('0.01'))),
                    "high": str(Decimal(str(row['High'])).quantize(Decimal('0.01'))),
                    "low": str(Decimal(str(row['Low'])).quantize(Decimal('0.01'))),
                    "close": str(Decimal(str(row['Close'])).quantize(Decimal('0.01'))),
                    "dividends": str(Decimal(str(row['Dividends']))) if pd.notna(row['Dividends']) and row[
                        'Dividends'] > 0 else None,
                    "splits": str(Decimal(str(row['Stock Splits']))) if pd.notna(row['Stock Splits']) and row[
                        'Stock Splits'] != 1.0 else None
                })

            return AssetData(
                ticker=ticker.upper(),
                name=name,
                base_currency=currency,
                start_date=hist_monthly.index[0].date(),
                monthly_data=monthly_data
            )

        except Exception as e:
            raise ValueError(f"Failed to fetch {ticker}: {str(e)}")