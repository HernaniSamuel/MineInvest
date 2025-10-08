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
from decimal import Decimal
from typing import List, Dict, Optional


class DividendPayment(BaseModel):
    """Details of a dividend payment."""
    ticker: str
    dividend_per_share: Decimal
    quantity: Decimal
    total: Decimal


class PriceUpdate(BaseModel):
    """Details of a price change."""
    ticker: str
    old_price: Decimal
    new_price: Decimal
    change: Decimal
    change_percent: Decimal


class MonthAdvancementResponse(BaseModel):
    """Report of month advancement."""
    success: bool
    previous_date: str
    new_date: str
    previous_balance: Decimal
    new_balance: Decimal
    previous_portfolio_value: Decimal
    new_portfolio_value: Decimal
    dividends_received: List[Dict]
    total_dividends: Decimal
    price_updates: List[Dict]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "previous_date": "2023-01-01",
                "new_date": "2023-02-01",
                "previous_balance": "1000.00",
                "new_balance": "1025.50",
                "previous_portfolio_value": "5000.00",
                "new_portfolio_value": "5200.00",
                "dividends_received": [
                    {
                        "ticker": "AAPL",
                        "dividend_per_share": "0.24",
                        "quantity": "10.5",
                        "total": "2.52"
                    }
                ],
                "total_dividends": "25.50",
                "price_updates": [
                    {
                        "ticker": "AAPL",
                        "old_price": "150.00",
                        "new_price": "155.00",
                        "change": "5.00",
                        "change_percent": "3.33"
                    }
                ]
            }
        }
    )


class CanAdvanceResponse(BaseModel):
    """Response for checking if month can be advanced."""
    can_advance: bool
    reason: Optional[str] = None
    next_month: Optional[str] = None
    holdings_count: Optional[int] = None