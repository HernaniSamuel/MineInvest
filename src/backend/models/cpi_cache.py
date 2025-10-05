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


from sqlalchemy import Column, Integer, String, Date, UniqueConstraint
from src.backend.models.base import Base


class CPICacheORM(Base):
    """
    Cache for US CPI (Consumer Price Index) monthly data from FRED.

    Stores historical CPI-U index values for inflation calculations.
    Data source: Federal Reserve Economic Data (FRED) - Series CPIAUCSL

    Attributes:
        id: Primary key
        month_date: First day of month (unique index for fast lookups)
        cpi_value: CPI index value as string (preserves FRED precision)

    Example Data:
        month_date: 2024-01-01
        cpi_value: "308.417"
    """

    __tablename__ = 'cpi_cache'

    id = Column(Integer, primary_key=True, index=True)
    month_date = Column(Date, nullable=False, unique=True, index=True)
    cpi_value = Column(String, nullable=False)
