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


from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.backend.models.base import Base


class HoldingORM(Base):
    __tablename__ = 'holdings'

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False)
    name = Column(String, nullable=False)
    base_currency = Column(String, nullable=False)

    quantity = Column(String, nullable=False)
    purchase_price = Column(String, nullable=False)
    weight = Column(String, nullable=False)
    current_price = Column(String, nullable=False)
    market_value = Column(String, nullable=False)

    simulation_id = Column(Integer, ForeignKey('simulations.id'), nullable=False)
    simulation = relationship("SimulationORM", back_populates="holdings")
