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


from decimal import Decimal
from pydantic import BaseModel
from pydantic import ConfigDict
from typing import List


class HoldingCreate(BaseModel):
    ticker: str
    name: str
    base_currency: str
    quantity: Decimal
    purchase_price: Decimal
    weight: Decimal
    current_price: Decimal
    market_value: Decimal


class HoldingRead(BaseModel):
    """Individual holding details."""
    id: int
    ticker: str
    name: str
    base_currency: str
    quantity: Decimal
    purchase_price: Decimal
    current_price: Decimal
    market_value: Decimal
    weight: Decimal  # Percentage of portfolio

    model_config = ConfigDict(from_attributes=True)


class PortfolioSummary(BaseModel):
    """Portfolio summary statistics."""
    total_holdings: int
    total_market_value: Decimal
    total_invested: Decimal
    total_gain_loss: Decimal
    gain_loss_percentage: Decimal


class PortfolioRead(BaseModel):
    """Complete portfolio with holdings and summary."""
    simulation_id: int
    simulation_name: str
    current_balance: Decimal
    holdings: List[HoldingRead]
    summary: PortfolioSummary
