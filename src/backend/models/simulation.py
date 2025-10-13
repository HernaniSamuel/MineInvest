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
from sqlalchemy.orm import relationship
from decimal import Decimal
from src.backend.models.base import Base
from src.backend.models.custom_types import PreciseDecimal


class SimulationORM(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True, unique=True)
    start_date = Column(Date, nullable=False)
    base_currency = Column(String, nullable=False)
    balance = Column(PreciseDecimal, default=Decimal("0.0000000000000000"), nullable=False)
    current_date = Column(Date, nullable=False)

    holdings = relationship('HoldingORM', back_populates='simulation', cascade="all, delete-orphan")
    history = relationship("HistoryMonthORM", back_populates="simulation", cascade="all, delete-orphan")
    snapshots = relationship("MonthlySnapshotORM", back_populates="simulation", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('name', name='uniq_simulation_name'),
    )
