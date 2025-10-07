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


from typing import List
from fastapi import Depends, APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from src.backend.models.session import get_db
from src.backend.schemas.balance import BalanceOperationRequest
from src.backend.schemas.simulation import SimulationCreate, SimulationRead, SimulationSumary
from src.backend.schemas.history_month import SimulationHistoryRead
from src.backend.services.balance_service import handle_balance_service
from src.backend.services.history_service import get_simulation_history_service
from src.backend.services.exceptions import (
    SimulationNotFoundError,
    SimulationAlreadyExistsError,
    InsufficientFundsError,
    InvalidAmountError
)
from src.backend.services.simulation_service import (
    create_simulation_service,
    list_simulations_service,
    delete_simulation_service,
    get_simulation_by_id_service,
)

router = APIRouter(prefix="/simulations", tags=["Simulations"])


@router.post("/", response_model=SimulationRead, status_code=201)
def create_simulation(
    simulation: SimulationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new investment simulation.

    - name: Unique name (1-100 characters, whitespace trimmed)
    - start_date: Simulation start date (YYYY-MM-DD, cannot be in future)
    - base_currency: 3-letter ISO currency code (default: BRL)

    Returns the created simulation with ID, initial balance (0), and current_date = start_date.

    Raises:
        - 400: If validation fails or simulation name already exists
        - 422: If request body is malformed
    """
    try:
        return create_simulation_service(db, simulation)
    except SimulationAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"internal server error: {str(e)}")


@router.post("/{simulation_id}/balance", response_model=SimulationRead)
def modify_balance(
        simulation_id: int,
        request: BalanceOperationRequest,
        db: Session = Depends(get_db)
):
    """
    Modify simulation balance (add or remove money).
    Single unified endpoint for all balance operations.
    """
    try:
        return handle_balance_service(db, simulation_id, request)
    except SimulationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[SimulationRead])
def list_simulations(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, description="Max records to return"),
        db: Session = Depends(get_db)
):
    """
    List all simulations with pagination.

    Returns simulations ordered by creation date (newest first).

    Query parameters:
        - skip: Offset for pagination
        - limit: Max results (default: 100, max: 1000)
    """
    try:
        simulations = list_simulations_service(db, skip=skip, limit=limit)
        return simulations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"internal server error: {str(e)}")


@router.get("/{simulation_id}", response_model=SimulationRead)
def get_simulation(
        simulation_id: int,
        db: Session = Depends(get_db)
):
    """
    Get a specific simulation by ID.

    Returns full simulation details including balance and holdings.
    """
    try:
        return get_simulation_by_id_service(db, simulation_id)
    except SimulationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{simulation_id}/history", response_model=SimulationHistoryRead)
def get_simulation_history(
        simulation_id: int,
        db: Session = Depends(get_db)
):
    """
    Get complete transaction history for a simulation.

    Returns chronologically ordered monthly records with:
    - All balance operations (contributions, withdrawals, purchases, sales, dividends)
    - Month-end balance totals
    - Operation details including tickers where applicable
    """
    try:
        return get_simulation_history_service(db, simulation_id)
    except SimulationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{simulation_id}", status_code=204)
def delete_simulation(
        simulation_id: int,
        db: Session = Depends(get_db)
):
    """
    Delete a simulation and all associated data.

    This operation:
    - Deletes the simulation
    - Deletes all holdings (via cascade)
    - Deletes all history records (via cascade)
    - Removes simulation from asset ownership lists
    - Deletes orphaned assets (assets with no owners)

    **Warning**: This action is irreversible.

    Returns:
        204 No Content on success
    """
    try:
        delete_simulation_service(db, simulation_id)
        return None  # 204 returns no content
    except SimulationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
