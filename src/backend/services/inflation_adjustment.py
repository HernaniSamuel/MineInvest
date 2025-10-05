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


from decimal import Decimal, ROUND_DOWN
from datetime import date
from sqlalchemy.orm import Session
from src.backend.external_apis.inflation import get_inflation_adjusted_value


def _apply_inflation_adjustment(
    amount: Decimal,
    base_currency: str,
    reference_date: date,
    current_date: date,
    db_session: Session
) -> Decimal:

    """
    Applies IPCA/CPI deflation to convert current money to reference date money.

    Args:
        amount (Decimal): Nominal amount in current money
        base_currency (str): Currency code (BRL, USD)
        reference_date (date): Simulation date (target)
        current_date (date): Today's date (source)
        db_session (Session): Database session for caching

    Returns:
        Real amount in reference_date purchasing power

    Example:
        User deposits $1000 today, but simulation is at 2023-01-01.
        If inflation was 15% from 2023 to today:
        $1000 / 1.15 = $869.57 (in 2023 money)
    """
    try:
        adjusted = get_inflation_adjusted_value(
            amount=amount,
            currency=base_currency,
            simulation_date=reference_date,
            current_date=current_date,
            db_session=db_session
        )

        # Quantize to 2 decimals (no rounding up for money)
        result = adjusted.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

        # If adjustment results in 0.00, return original amount
        if result == Decimal('0.00'):
            print(f"Warning: Inflation adjustment would result in 0.00, using original amount")
            return amount

        return result

    except (ValueError, ConnectionError) as e:
        print(f"Warning: Inflation adjustment failed: {e}")
        return amount