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

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from src.backend.models.session import get_db
from src.backend.services.exchange_service import ExchangeService
from src.backend.schemas.exchange import ExchangeRateResponse, ExchangeRateHistory

router = APIRouter(prefix="/exchange", tags=["Exchange Rates"])


@router.get("/rate", response_model=ExchangeRateResponse)
def get_exchange_rate(
        from_currency: str = Query(
            ...,
            description="Source currency code (ISO 4217, e.g., 'USD')",
            min_length=3,
            max_length=3
        ),
        to_currency: str = Query(
            ...,
            description="Target currency code (ISO 4217, e.g., 'BRL')",
            min_length=3,
            max_length=3
        ),
        date: str = Query(
            ...,
            description="Date for exchange rate in ISO format (YYYY-MM-DD)"
        ),
        db: Session = Depends(get_db)
):
    """
    Get historical exchange rate between two currencies for a specific date.

    This endpoint implements intelligent caching:
    - First request: Fetches ALL historical data from Yahoo Finance (~2-10s)
    - Subsequent requests: Returns cached data instantly (~50ms)

    The exchange rate returned is the closing rate for the month containing
    the specified date. Data includes OHLC values and metadata.

    Caching Strategy:
        On cache miss, the service fetches complete historical data (2000-present)
        and stores it in the database, ensuring all future queries are fast.

    Examples:
        GET /api/exchange/rate?from_currency=USD&to_currency=BRL&date=2024-01-15
        GET /api/exchange/rate?from_currency=EUR&to_currency=USD&date=2023-06-01
        GET /api/exchange/rate?from_currency=GBP&to_currency=JPY&date=2024-03-20

    Response Fields:
        - rate: Primary exchange rate (close price) - use this for calculations
        - open: Opening rate for the month
        - high: Highest rate during the month
        - low: Lowest rate during the month
        - from_cache: True if data came from database cache
        - yfinance_symbol: Yahoo Finance symbol used (e.g., 'USDBRL=X')

    Args:
        from_currency: Source currency code (3 letters, e.g., 'USD')
        to_currency: Target currency code (3 letters, e.g., 'BRL')
        date: Date in YYYY-MM-DD format
        db: Database session (injected)

    Returns:
        ExchangeRateResponse with rate data and metadata

    Raises:
        HTTPException 400: Invalid date format or currency codes
        HTTPException 500: Failed to fetch exchange rate data
    """
    try:
        # Parse date string to date object
        target_date = datetime.fromisoformat(date).date()

        # Get exchange rate from service
        rate = ExchangeService.get_exchange_rate(
            db=db,
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            target_date=target_date
        )

        return rate

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get exchange rate: {str(e)}"
        )


@router.get("/history", response_model=ExchangeRateHistory)
def get_exchange_history(
        from_currency: str = Query(
            ...,
            description="Source currency code (ISO 4217)",
            min_length=3,
            max_length=3
        ),
        to_currency: str = Query(
            ...,
            description="Target currency code (ISO 4217)",
            min_length=3,
            max_length=3
        ),
        start_date: Optional[str] = Query(
            None,
            description="Start date for history (YYYY-MM-DD, optional)"
        ),
        end_date: Optional[str] = Query(
            None,
            description="End date for history (YYYY-MM-DD, optional)"
        ),
        db: Session = Depends(get_db)
):
    """
    Get complete historical exchange rate data for a currency pair.

    Returns all cached monthly exchange rates (OHLC) for the specified
    currency pair within the given date range. If no cache exists,
    automatically fetches from Yahoo Finance first.

    Use Cases:
        - Charting exchange rate trends over time
        - Historical analysis and backtesting
        - Bulk data export for reporting

    Data Continuity:
        All data is forward-filled to eliminate gaps in the time series,
        ensuring a complete and continuous dataset.

    Examples:
        # Get all available data
        GET /api/exchange/history?from_currency=USD&to_currency=BRL

        # Get specific date range
        GET /api/exchange/history?from_currency=EUR&to_currency=BRL&start_date=2023-01-01&end_date=2023-12-31

        # Get last year's data
        GET /api/exchange/history?from_currency=GBP&to_currency=USD&start_date=2023-01-01

    Response Structure:
        {
          "from_currency": "USD",
          "to_currency": "BRL",
          "yfinance_symbol": "USDBRL=X",
          "data": [
            {
              "date": "2023-01-01",
              "open": 5.2134,
              "high": 5.3456,
              "low": 5.1234,
              "close": 5.2789
            },
            ...
          ]
        }

    Args:
        from_currency: Source currency code (3 letters)
        to_currency: Target currency code (3 letters)
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        db: Database session (injected)

    Returns:
        ExchangeRateHistory with list of monthly data points

    Raises:
        HTTPException 400: Invalid date format or currency codes
        HTTPException 500: Failed to fetch exchange rate history
    """
    try:
        # Parse optional date parameters
        start = datetime.fromisoformat(start_date).date() if start_date else None
        end = datetime.fromisoformat(end_date).date() if end_date else None

        # Get historical data from service
        history = ExchangeService.get_exchange_history(
            db=db,
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            start_date=start,
            end_date=end
        )

        return history

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get exchange history: {str(e)}"
        )