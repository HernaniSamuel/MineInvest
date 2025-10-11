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


from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
from typing import Optional

from src.backend.models.asset import AssetORM
from src.backend.models.simulation import SimulationORM
from src.backend.services.asset_cache import AssetRAMCache, AssetData
from src.backend.external_apis.yfinance_client import YFinanceClient
from src.backend.services.exceptions import AssetNotFoundError, PriceUnavailableError


class AssetService:
    """Three-tier asset retrieval: RAM → Database → yfinance."""

    @staticmethod
    def search_asset(
            db: Session,
            ticker: str,
            simulation_id: Optional[int] = None
    ) -> AssetData:
        """
        Search for asset across all tiers.

        Priority: RAM cache → Database → yfinance API

        Args:
            db: Database session
            ticker: Asset ticker
            simulation_id: Optional - validate asset exists at sim date

        Returns:
            Complete asset data

        Raises:
            AssetNotFoundError: If ticker invalid
            ValueError: If asset doesn't exist at simulation date
        """
        ticker = ticker.upper()

        # Tier 1: RAM Cache
        cached = AssetRAMCache.get(ticker)
        if cached:
            if simulation_id:
                AssetService._validate_asset_date(db, cached, simulation_id)
            return cached

        # Tier 2: Database (purchased assets)
        db_asset = db.query(AssetORM).filter(AssetORM.ticker == ticker).first()
        if db_asset:
            asset_data = AssetService._orm_to_data(db_asset)
            # Don't cache DB assets in RAM (they're persistent)
            if simulation_id:
                AssetService._validate_asset_date(db, asset_data, simulation_id)
            return asset_data

        # Tier 3: yfinance API
        try:
            asset_data = YFinanceClient.fetch_asset(ticker)
            AssetRAMCache.put(asset_data)  # Cache for future searches

            if simulation_id:
                AssetService._validate_asset_date(db, asset_data, simulation_id)

            return asset_data

        except ValueError as e:
            raise AssetNotFoundError(f"Asset {ticker} not found: {e}")

    @staticmethod
    def _validate_asset_date(db: Session, asset: AssetData, simulation_id: int):
        """Ensure asset existed at simulation's current date."""
        sim = db.query(SimulationORM).filter(SimulationORM.id == simulation_id).first()
        if not sim:
            raise ValueError(f"Simulation {simulation_id} not found")

        if asset.start_date > sim.current_date:
            raise ValueError(
                f"Asset {asset.ticker} did not exist on {sim.current_date}. "
                f"First available: {asset.start_date}"
            )

    @staticmethod
    def get_price_at_date(asset: AssetData, target_date: date) -> Decimal:
        """Get asset's closing price at specific date."""
        target_month = target_date.replace(day=1)

        for month_data in asset.monthly_data:
            if date.fromisoformat(month_data["date"]) == target_month:
                return Decimal(month_data["close"])

        raise PriceUnavailableError(
            f"No price data for {asset.ticker} on {target_date}"
        )

    @staticmethod
    def persist_to_database(db: Session, asset: AssetData, simulation_id: int):
        """Move asset from RAM to database on purchase."""
        existing = db.query(AssetORM).filter(AssetORM.ticker == asset.ticker).first()

        if existing:
            # Add simulation to ownership list
            if simulation_id not in existing.simulation_ids:
                existing.simulation_ids.append(simulation_id)
        else:
            # Create new DB entry
            new_asset = AssetORM(
                ticker=asset.ticker,
                name=asset.name,
                base_currency=asset.base_currency,
                start_date=asset.start_date,
                simulation_ids=[simulation_id],
                monthly_data=asset.monthly_data
            )
            db.add(new_asset)

        # Remove from RAM cache
        AssetRAMCache.remove(asset.ticker)

        db.commit()

    @staticmethod
    def remove_from_database_if_orphaned(db: Session, ticker: str, simulation_id: int):
        """Remove asset from DB if no simulations own it."""
        asset = db.query(AssetORM).filter(AssetORM.ticker == ticker).first()
        if not asset:
            return

        # Remove simulation from ownership
        if simulation_id in asset.simulation_ids:
            asset.simulation_ids.remove(simulation_id)

        # Delete if no owners remain
        if not asset.simulation_ids:
            db.delete(asset)

        db.commit()

    @staticmethod
    def _orm_to_data(orm: AssetORM) -> AssetData:
        """Convert ORM to AssetData."""
        return AssetData(
            ticker=orm.ticker,
            name=orm.name,
            base_currency=orm.base_currency,
            start_date=orm.start_date,
            monthly_data=orm.monthly_data
        )

    @staticmethod
    def get_historical_data_until_date(asset: AssetData, target_date: date) -> list:
        """
        Get all monthly data from asset start date up to target date.

        Args:
            asset: Asset data object
            target_date: End date (simulation current date)

        Returns:
            List of monthly data points up to and including target_date's month
        """
        target_month = target_date.replace(day=1)
        filtered_data = []

        for month_data in asset.monthly_data:
            month_date = date.fromisoformat(month_data["date"])
            if month_date <= target_month:
                filtered_data.append(month_data)
            else:
                break  # Data is chronological, can stop here

        return filtered_data