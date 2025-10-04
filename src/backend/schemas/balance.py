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


from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from src.backend.schemas.enums import Operation
from typing import Optional


class BalanceOperationRequest(BaseModel):
    """Request for balance modification (add or remove)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "amount": "1500.50",
                    "operation": "ADD",
                    "category": "contribution",
                    "remove_inflation": True,
                    "ticker": None
                },
                {
                    "amount": "0.03",
                    "operation": "ADD",
                    "category": "dividend",
                    "remove_inflation": False,
                    "ticker": "PETR4"
                }
            ]
        },
        use_enum_values=False
    )

    amount: Decimal = Field(
        ...,
        gt=0,
        description="Amount to modify (positive, exactly 2 decimal places except for dividends)."
    )
    operation: Operation = Field(
        ...,
        description="ADD or REMOVE"
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Operation category: contribution, withdrawal, dividend, purchase, sale"
    )
    ticker: Optional[str] = Field(
        default=None,
        max_length=20,
        description="The asset's ticker symbol (only required for purchase, sale, or dividend operations)"
    )
    remove_inflation: bool = Field(
        default=False,
        description="Removes accumulated inflation from the amount"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        """
        Raises:
            ValueError: If negative or bigger than 1 trillion - 0.01.
        """
        if v <= Decimal("0"):
            raise ValueError("Amount must be positive")

        if v <= Decimal('0'):
            raise ValueError("Amount must be positive")

        if v > Decimal('999999999999.99'):
            raise ValueError("Amount exceeds maximum allowed")

        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Ensure category is valid."""
        v = v.strip().lower()

        valid_categories = {
            'contribution', 'withdrawal', 'dividend', 'purchase', 'sale'
        }

        if v not in valid_categories:
            raise ValueError(
                f"Invalid category: '{v}'. "
                f"Must be one of: {', '.join(sorted(valid_categories))}"
            )

        return v

    @model_validator(mode='after')
    def validate_category_rules(self):
        """
        Apply category-specific validation rules:

        1. Dividends: Allow unlimited decimal places
        2. Other operations: Exactly 2 decimal places
        3. Purchase/Sale/Dividend: Require ticker
        """
        # Check decimal precision based on category
        decimal_places = abs(self.amount.as_tuple().exponent)

        if self.category != 'dividend' and decimal_places > 2:
            raise ValueError(
                f"Category '{self.category}' requires exactly 2 decimal places. "
                f"Amount {self.amount} has {decimal_places} decimal places."
            )

        # Check ticker requirement
        requires_ticker = {'purchase', 'sale', 'dividend'}

        if self.category in requires_ticker and not self.ticker:
            raise ValueError(
                f"Category '{self.category}' requires a ticker symbol."
            )

        if self.category not in requires_ticker and self.ticker:
            raise ValueError(
                f"Category '{self.category}' should not have a ticker. "
                f"Remove ticker or use purchase/sale/dividend category."
            )

        # Validate ticker format if present
        if self.ticker:
            self.ticker = self.ticker.strip().upper()
            if not self.ticker:
                raise ValueError("Ticker cannot be empty")

        return self

