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

from src.backend.models.session import get_db
from src.backend.schemas.trading import (
    AssetSearchResponse,
    PurchaseRequest,
    SellRequest
)
from src.backend.schemas.simulation import SimulationRead
from src.backend.services.asset_service import AssetService
from src.backend.services.trading_service import (
    purchase_asset_service,
    sell_asset_service
)
from src.backend.services.exceptions import (
    AssetNotFoundError,
    InsufficientFundsError,
    InsufficientPositionError,
    PriceUnavailableError,
    SimulationNotFoundError
)

router = APIRouter(prefix="/assets", tags=["Assets & Trading"])


@router.get("/{ticker}", response_model=AssetSearchResponse)
def search_asset(
        ticker: str,
        simulation_id: int = Query(None, description="Validate asset exists at simulation date"),
        db: Session = Depends(get_db)
):
    """
    Search for an asset across RAM cache, database, or yfinance.

    Returns complete historical data up to simulation date. If simulation_id provided,
    validates asset existed at simulation's current date and filters data accordingly.
    """
    try:
        asset = AssetService.search_asset(db, ticker, simulation_id)

        # Base response
        response = AssetSearchResponse(
            ticker=asset.ticker,
            name=asset.name,
            base_currency=asset.base_currency,
            start_date=asset.start_date.isoformat(),
            current_price=None,
            historical_data=[]
        )

        # If simulation provided, include filtered historical data and current price
        if simulation_id:
            from src.backend.models.simulation import SimulationORM
            from src.backend.schemas.trading import MonthlyDataPoint
            from decimal import Decimal
            from datetime import date

            sim = db.query(SimulationORM).filter(SimulationORM.id == simulation_id).first()
            if sim:
                # Get historical data up to simulation date
                filtered_data = AssetService.get_historical_data_until_date(
                    asset,
                    sim.current_date
                )

                # Convert to Pydantic models
                response.historical_data = [
                    MonthlyDataPoint(
                        date=date.fromisoformat(data["date"]),
                        open=Decimal(data["open"]),
                        high=Decimal(data["high"]),
                        low=Decimal(data["low"]),
                        close=Decimal(data["close"]),
                        dividends=Decimal(data["dividends"]) if data.get("dividends") else None,
                        splits=Decimal(data["splits"]) if data.get("splits") else None
                    )
                    for data in filtered_data
                ]

                # Set current price (last close price)
                if response.historical_data:
                    response.current_price = response.historical_data[-1].close
        else:
            # No simulation - return all historical data
            from src.backend.schemas.trading import MonthlyDataPoint
            from decimal import Decimal
            from datetime import date

            response.historical_data = [
                MonthlyDataPoint(
                    date=date.fromisoformat(data["date"]),
                    open=Decimal(data["open"]),
                    high=Decimal(data["high"]),
                    low=Decimal(data["low"]),
                    close=Decimal(data["close"]),
                    dividends=Decimal(data["dividends"]) if data.get("dividends") else None,
                    splits=Decimal(data["splits"]) if data.get("splits") else None
                )
                for data in asset.monthly_data
            ]

        return response

    except AssetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{simulation_id}/purchase", response_model=SimulationRead)
def purchase_asset(
        simulation_id: int,
        request: PurchaseRequest,
        db: Session = Depends(get_db)
):
    """
    Purchase an asset for a simulation.

    Calculates quantity based on current price and desired amount.
    Deducts balance and creates/updates holding.
    """
    try:
        return purchase_asset_service(db, simulation_id, request)
    except SimulationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AssetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PriceUnavailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{simulation_id}/sell", response_model=SimulationRead)
def sell_asset(
        simulation_id: int,
        request: SellRequest,
        db: Session = Depends(get_db)
):
    """
    Sell an owned asset.

    Calculates quantity to sell based on current price.
    Adds proceeds to balance and updates/removes holding.
    """
    try:
        return sell_asset_service(db, simulation_id, request)
    except SimulationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientPositionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AssetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PriceUnavailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))