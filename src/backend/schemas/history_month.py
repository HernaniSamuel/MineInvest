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


from pydantic import BaseModel, ConfigDict
from datetime import date
from decimal import Decimal
from typing import List, Dict, Optional


class OperationDict(BaseModel):
    """Individual operation within a month"""
    type: str  # 'contribution', 'withdrawal', 'purchase', 'sale', 'dividend'
    amount: Decimal  # Changed from 'value' to match what you're storing
    ticker: Optional[str] = None


class HistoryMonthRead(BaseModel):
    """Single month's history."""
    id: int
    month_date: date
    operations: List[Dict]  # List of operation dicts
    total: Decimal
    simulation_id: int

    model_config = ConfigDict(from_attributes=True)


class SimulationHistoryRead(BaseModel):
    """Complete simulation history."""
    simulation_id: int
    simulation_name: str
    start_date: date
    current_date: date
    months: List[HistoryMonthRead]

    model_config = ConfigDict(from_attributes=True)