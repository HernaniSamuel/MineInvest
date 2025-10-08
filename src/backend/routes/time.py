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


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.backend.models.session import get_db
from src.backend.schemas.time import MonthAdvancementResponse, CanAdvanceResponse
from src.backend.services.time_service import advance_month_service, can_advance_month
from src.backend.services.exceptions import SimulationNotFoundError

router = APIRouter(prefix="/simulations", tags=["Time Management"])


@router.get("/{simulation_id}/can-advance", response_model=CanAdvanceResponse)
def check_can_advance(
        simulation_id: int,
        db: Session = Depends(get_db)
):
    """
    Check if simulation can advance to next month.

    Verifies:
    - Simulation exists
    - Not already at current real-world date
    - Price data available for next month

    Returns information about whether advancement is possible.
    """
    result = can_advance_month(db, simulation_id)
    return CanAdvanceResponse(**result)


@router.post("/{simulation_id}/advance", response_model=MonthAdvancementResponse)
def advance_month(
        simulation_id: int,
        db: Session = Depends(get_db)
):
    """
    Advance simulation by one month.

    This will:
    1. Create a snapshot (for undo capability)
    2. Calculate and pay dividends for all holdings
    3. Advance current_date by 1 month
    4. Update all asset prices to new month
    5. Recalculate portfolio weights

    Returns detailed report of:
    - Dividends received
    - Price changes
    - New portfolio value
    - Balance changes

    **Note**: This creates a snapshot before advancing,
    allowing you to undo if needed.
    """
    try:
        # Check if can advance
        can_advance = can_advance_month(db, simulation_id)
        if not can_advance["can_advance"]:
            raise HTTPException(
                status_code=400,
                detail=can_advance["reason"]
            )

        # Advance
        report = advance_month_service(db, simulation_id)

        return MonthAdvancementResponse(
            success=True,
            previous_date=report.previous_date.isoformat(),
            new_date=report.new_date.isoformat(),
            previous_balance=report.previous_balance,
            new_balance=report.new_balance,
            previous_portfolio_value=report.previous_portfolio_value,
            new_portfolio_value=report.new_portfolio_value,
            dividends_received=report.dividends_received,
            total_dividends=report.total_dividends,
            price_updates=report.price_updates
        )

    except SimulationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))