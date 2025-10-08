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


from sqlalchemy import Column, Integer, String, Date, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from src.backend.models.base import Base


class MonthlySnapshotORM(Base):
    """
    Snapshot of simulation state at the beginning of each month.

    Allows reverting all operations within the current month.
    Only the most recent snapshot is kept.
    """

    __tablename__ = 'monthly_snapshots'

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey('simulations.id'), nullable=False)
    month_date = Column(Date, nullable=False, index=True)  # First day of month
    balance = Column(String, nullable=False)  # Balance at start of month
    holdings_snapshot = Column(JSON, default=list, nullable=False)
    # Format: [{"ticker": "AAPL", "quantity": "10.5", "purchase_price": "100.00", ...}, ...]

    simulation = relationship("SimulationORM", back_populates="snapshots")

    __table_args__ = (
        UniqueConstraint('simulation_id', 'month_date', name='uq_snapshot_sim_month'),
    )