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


from fastapi import APIRouter, Query, HTTPException
import httpx
import logging
from typing import Dict
import asyncio
from datetime import datetime, timedelta

router = APIRouter(prefix="/api", tags=["Assets"])
logger = logging.getLogger(__name__)

# Simple in-memory cache
_search_cache: Dict[str, tuple] = {}  # {query: (data, timestamp)}
CACHE_DURATION = 300  # 5 minutes


@router.get("/search-assets")
async def search_assets(q: str = Query(..., min_length=2, max_length=50)):
    """
    Search for assets via Yahoo Finance with caching and rate limiting.
    """
    # Normalize query
    query_key = q.lower().strip()

    # Check cache first
    if query_key in _search_cache:
        cached_data, cached_time = _search_cache[query_key]
        if datetime.now() - cached_time < timedelta(seconds=CACHE_DURATION):
            logger.info(f"Returning cached results for: {q}")
            return cached_data

    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={q}"

        # Mimic browser headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://finance.yahoo.com',
            'Referer': 'https://finance.yahoo.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }

        # Add small delay to avoid rapid requests
        await asyncio.sleep(0.5)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers, timeout=15.0)

            if response.status_code == 429:
                logger.warning(f"Rate limited by Yahoo Finance for query: {q}")
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests to Yahoo Finance. Please wait a moment and try again."
                )

            response.raise_for_status()
            data = response.json()

            # Filter and format results
            quotes = data.get('quotes', [])
            filtered_quotes = [
                q for q in quotes
                if q.get('quoteType') == 'EQUITY'
            ]

            result = {
                "count": len(filtered_quotes),
                "quotes": filtered_quotes[:15]
            }

            # Cache the result
            _search_cache[query_key] = (result, datetime.now())

            # Clean old cache entries (keep only last 100)
            if len(_search_cache) > 100:
                oldest_key = min(_search_cache.keys(), key=lambda k: _search_cache[k][1])
                del _search_cache[oldest_key]

            logger.info(f"Successfully fetched {len(filtered_quotes)} results for: {q}")
            return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("Rate limited by Yahoo Finance")
            raise HTTPException(
                status_code=429,
                detail="Search temporarily unavailable. Please wait 30 seconds and try again."
            )
        logger.error(f"Yahoo Finance HTTP error: {e.response.status_code}")
        raise HTTPException(
            status_code=503,
            detail=f"Yahoo Finance unavailable (Error {e.response.status_code})"
        )

    except httpx.RequestError as e:
        logger.error(f"Connection error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Yahoo Finance. Please try again later."
        )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed unexpectedly")