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
from typing import List
from decimal import Decimal

from src.backend.models.session import get_db
from src.backend.models.simulation import SimulationORM
from src.backend.models.holding import HoldingORM
from src.backend.schemas.holding import HoldingRead, PortfolioSummary, PortfolioRead
from src.backend.services.holding_service import (
    update_holdings_attributes,
    get_holdings_summary
)
from src.backend.services.exceptions import SimulationNotFoundError

router = APIRouter(prefix="/simulations", tags=["Holdings & Portfolio"])


@router.get("/{simulation_id}/holdings", response_model=List[HoldingRead])
def list_holdings(
        simulation_id: int,
        db: Session = Depends(get_db)
):
    """
    List all holdings for a simulation.

    Returns current positions with:
    - Quantity owned
    - Purchase price (weighted average)
    - Current market price
    - Market value
    - Portfolio weight percentage
    """
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    return holdings


@router.get("/{simulation_id}/portfolio", response_model=PortfolioRead)
def get_portfolio(
        simulation_id: int,
        db: Session = Depends(get_db)
):
    """
    Get complete portfolio overview.

    Returns:
    - Current balance
    - All holdings with details
    - Portfolio summary (total value, gain/loss, etc.)
    """
    # Get simulation
    sim = db.query(SimulationORM).filter(
        SimulationORM.id == simulation_id
    ).first()

    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Get holdings
    holdings = db.query(HoldingORM).filter(
        HoldingORM.simulation_id == simulation_id
    ).all()

    # Get summary
    summary = get_holdings_summary(db, simulation_id)

    return PortfolioRead(
        simulation_id=sim.id,
        simulation_name=sim.name,
        current_balance=Decimal(sim.balance),
        holdings=[HoldingRead.model_validate(h) for h in holdings],
        summary=PortfolioSummary(**summary)
    )


@router.post("/{simulation_id}/holdings/refresh", response_model=List[HoldingRead])
def refresh_holdings(
        simulation_id: int,
        db: Session = Depends(get_db)
):
    """
    Manually refresh all holding attributes.

    Recalculates:
    - Current prices at simulation date
    - Market values
    - Portfolio weights

    Useful after:
    - Time advancement
    - Asset price changes
    - Manual corrections
    """
    try:
        holdings = update_holdings_attributes(db, simulation_id)
        return holdings
    except SimulationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
