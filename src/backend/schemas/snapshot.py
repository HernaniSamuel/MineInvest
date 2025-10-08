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
from typing import Optional


class SnapshotInfo(BaseModel):
    """Information about the current snapshot."""
    exists: bool
    month_date: Optional[str] = None
    balance: Optional[str] = None
    holdings_count: Optional[int] = None
    can_restore: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exists": True,
                "month_date": "2023-01-01",
                "balance": "10000.00",
                "holdings_count": 5,
                "can_restore": True
            }
        }
    )


class RestoreResponse(BaseModel):
    """Response after restoring from snapshot."""
    success: bool
    message: str
    simulation_id: int
    restored_balance: str
    restored_holdings_count: int