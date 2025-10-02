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


from sqlalchemy import Column, Integer, String, Date, JSON
from src.backend.models.base import Base


class AssetORM(Base):
    __tablename__ = 'assets'

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    base_currency = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    simulation_ids = Column(JSON, default=[])
    monthly_data = Column(JSON, default=[])
    # MONTLY DATA FORMAT
    # [
    #   {
    #     "date": "date",
    #     "open": Decimal(0.01),
    #     "high": Decimal(0.01),
    #     "low": Decimal(0.01),
    #     "close": Decimal(0.01),
    #     "dividends": Decimal | None,
    #     "splits": Decimal | None
    #   }
    # ]
