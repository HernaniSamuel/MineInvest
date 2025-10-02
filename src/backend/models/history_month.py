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


from sqlalchemy import Column, Integer, Date, ForeignKey, Numeric, JSON
from sqlalchemy.orm import relationship

from decimal import Decimal
from src.backend.models.base import Base


class HistoryMonthORM(Base):
    __tablename__ = 'history_months'

    id = Column(Integer, primary_key=True, index=True)
    month_date = Column(Date, nullable=False)
    operations = Column(JSON, default=lambda: [], nullable=False)
    total = Column(Numeric(32, 16), default=Decimal('0.0000000000000000'), nullable=False)

    simulation_id = Column(Integer, ForeignKey('simulations.id'), nullable=False)
    simulation = relationship('SimulationORM', back_populates='history')
