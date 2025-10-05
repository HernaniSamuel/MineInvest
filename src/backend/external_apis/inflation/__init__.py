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


from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from src.backend.external_apis.inflation.base import InflationAPIInterface
from src.backend.external_apis.inflation.brl_inflation import BCBInflationAPI
from src.backend.external_apis.inflation.usd_inflation import USDInflationAPI


class InflationAPIFactory:
    """Factory to get appropriate inflation API based on currency."""

    @classmethod
    def get_api(cls, currency: str, db_session: Session) -> InflationAPIInterface:
        """
        Get inflation API for specified currency.

        Args:
            currency: ISO currency code
            db_session: Database session for caching

        Returns:
            Appropriate inflation API instance
        """

        currency = currency.upper()

        if currency == "BRL":
            return BCBInflationAPI(db_session)
        elif currency == "USD":
            return USDInflationAPI(db_session)
        else:
            raise ValueError(
                f"No inflation API available for {currency}. "
                f"Supported: BRL, USD"
            )

def get_inflation_adjusted_value(
        amount: Decimal,
        currency: str,
        simulation_date: date,
        current_date: date,
        db_session: Session
) -> Decimal:
    """
    Adjust amount for accumulated inflation with caching.

    Converts money from current_date purchasing power back to
    simulation_date purchasing power (deflation).

    Args:
        amount: Nominal amount
        currency: Base currency
        simulation_date: Target date (past)
        current_date: Source date (today)
        db_session: DB session for cache access

    Returns:
        Real amount adjusted for inflation

    Example:
        If $100 today equals to $90 in 2023 money (10% inflation)
        this returns Decimal (90)
    """
    if simulation_date >= current_date:
        return amount

    api = InflationAPIFactory.get_api(currency, db_session)

    # Get accumulated inflation multiplier
    inflation_multiplier = api.get_accumulated_inflation(
        currency=currency,
        start_date=simulation_date,
        end_date=current_date,
    )

    # Deflate: divide by multiplier to get past value
    adjusted_amount = amount / inflation_multiplier

    return adjusted_amount
