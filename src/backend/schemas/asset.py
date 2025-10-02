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


from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from typing import Optional

class MontlyDataPoint(BaseModel):
    """Single month of OHLC data"""
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    dividends: Optional[Decimal] = None
    splits: Optional[Decimal] = None
