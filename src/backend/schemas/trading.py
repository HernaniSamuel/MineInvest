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
from decimal import Decimal
from typing import Optional


class AssetSearchResponse(BaseModel):
    """Response for asset search."""

    ticker: str
    name: str
    base_currency: str
    start_date: str  # ISO format
    current_price: Optional[Decimal] = None  # Price at simulation date if provided

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "base_currency": "USD",
                "start_date": "1980-12-12",
                "current_price": "150.25"
            }
        }
    )


class PurchaseRequest(BaseModel):
    """Request to purchase an asset."""

    ticker: str = Field(..., min_length=1, max_length=10)
    desired_amount: Decimal = Field(..., gt=0)

    @field_validator('desired_amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure exactly 2 decimal places."""
        if abs(v.as_tuple().exponent) > 2:
            raise ValueError("Amount must have exactly 2 decimal places")
        return v.quantize(Decimal('0.01'))

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        return v.strip().upper()


class SellRequest(BaseModel):
    """Request to sell an asset."""

    ticker: str = Field(..., min_length=1, max_length=10)
    desired_amount: Decimal = Field(..., gt=0)

    @field_validator('desired_amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if abs(v.as_tuple().exponent) > 2:
            raise ValueError("Amount must have exactly 2 decimal places")
        return v.quantize(Decimal('0.01'))

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        return v.strip().upper()


# TODO: Verificar possibilidade de unificação de compra/venda de ativos em uma só operação
