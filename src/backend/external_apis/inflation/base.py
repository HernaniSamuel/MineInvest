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


from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import date
from typing import Dict


class InflationAPIInterface(ABC):
    """
    Abstract base class for inflation rate APIs.

    All inflation providers must implement this interface to ensure
    compatibility with the inflation adjustment service.
    """

    @abstractmethod
    def get_accumulated_inflation(
        self,
        currency: str,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """
        Returns accumulated inflation rate between two dates.

        Args:
            currency (str): ISO currency code (e.g., "BRL", "USD")
            start_date (date): Beginning of period
            end_date (date): End of period

        Returns:
            Decimal: Accumulated inflation as multiplier (e.g., 1.15 = 15% inflation)

        Raises:
            ValueError: If currency code is not supported
            ConnectionError: If API unavailable and data not found in local database
        """
        pass