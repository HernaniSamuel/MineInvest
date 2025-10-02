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


from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import date
from decimal import Decimal


class SimulationCreate(BaseModel):
    """Schema for creating a new simulation"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "My Investment Portfolio 2023",
                "start_date": "2023-01-01",
                "base_currency": "BRL"
            }
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique name for the simulation",
    )
    start_date: date = Field(
        ...,
        description="Starting date of the simulation (format YYYY-MM-DD)",
    )
    base_currency: str = Field(
        default="BRL",
        pattern=r"^[A-Z]{3}$",
        description="Base currency (3-letter ISO code, e.g., BRL, USD)"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure the name is not just whitespace"""
        if not v or not v.strip():
            raise ValueError("Simulation name cannot be empty or whitespace")
        return v.strip()

    @field_validator('start_date')
    @classmethod
    def validade_start_date(cls, v: date) -> date:
        """Ensure start date is not in the future"""
        if v > date.today():
            raise ValueError("Start date cannot be in the future")
        return v


class SimulationRead(BaseModel):
    """Schema for reading simulation data"""
    id: int
    name: str
    base_currency: str
    start_date: date
    current_date: date
    balance: Decimal

    model_config = ConfigDict(from_attributes=True)

class SimulationSumary(BaseModel):
    """Lightweight schema for listing simulations"""
    id: int
    name: str
    base_currency: str
    start_date: date
    current_date: date
    balance: Decimal
    holdings_count: int = Field(description="Number of assets in portfolio")

    model_config = ConfigDict(from_attributes=True)