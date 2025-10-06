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


from collections import OrderedDict
from typing import Optional
from decimal import Decimal
from datetime import date


class AssetData:
    """In-memory representation of asset data."""

    def __init__(
            self,
            ticker: str,
            name: str,
            base_currency: str,
            start_date: date,
            monthly_data: list
    ):
        self.ticker = ticker
        self.name = name
        self.base_currency = base_currency
        self.start_date = start_date
        self.monthly_data = monthly_data  # List of dicts


class AssetRAMCache:
    """LRU cache for searched assets (max 10)."""

    MAX_SIZE = 10
    _cache: OrderedDict[str, AssetData] = OrderedDict()

    @classmethod
    def get(cls, ticker: str) -> Optional[AssetData]:
        """Get asset from cache (refreshes access time)."""
        if ticker in cls._cache:
            # Move to end (most recently used)
            cls._cache.move_to_end(ticker)
            return cls._cache[ticker]
        return None

    @classmethod
    def put(cls, asset: AssetData) -> None:
        """Add asset to cache with LRU eviction."""
        ticker = asset.ticker.upper()

        if ticker in cls._cache:
            # Update existing
            cls._cache[ticker] = asset
            cls._cache.move_to_end(ticker)
        else:
            # Add new
            if len(cls._cache) >= cls.MAX_SIZE:
                # Evict oldest
                cls._cache.popitem(last=False)
            cls._cache[ticker] = asset

    @classmethod
    def remove(cls, ticker: str) -> None:
        """Remove from cache (called on purchase)."""
        cls._cache.pop(ticker.upper(), None)

    @classmethod
    def clear(cls) -> None:
        """Clear entire cache."""
        cls._cache.clear()