"""
Market data API wrapper for fetching stock prices.
Uses async aiohttp for non-blocking HTTP requests and TTL-based caching.
"""

import time
import pytz
import aiohttp
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

from config.constants import (
    MARKET_TIMEZONE,
    MARKET_OPEN_HOUR,
    MARKET_OPEN_MINUTE,
    MARKET_CLOSE_HOUR,
    CACHE_TTL_SECONDS,
)
from config.settings import FINNHUB_API_KEY
from bot.utils.logger import get_logger, log_api_call
from bot.utils.exceptions import MarketDataException

logger = get_logger(__name__)


class TTLCache:
    """Simple TTL-based cache for market data."""

    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp."""
        self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


# Global cache instances
_price_cache = TTLCache(ttl_seconds=CACHE_TTL_SECONDS)
_closing_cache = TTLCache(ttl_seconds=3600)  # 1 hour for closing prices


def is_market_open() -> bool:
    """Check if the US stock market is currently open."""
    eastern = pytz.timezone(MARKET_TIMEZONE)
    now = datetime.now(eastern)

    # Check if it's a weekday
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Check if within market hours
    market_open_time = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0)
    market_close_time = now.replace(hour=MARKET_CLOSE_HOUR, minute=0, second=0)

    return market_open_time <= now < market_close_time


async def _fetch_quote(symbol: str) -> Dict[str, Any]:
    """Fetch quote data from Finnhub API."""
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

    if "error" in data:
        logger.error(f"Finnhub API error for {symbol}: {data['error']}")
        log_api_call("finnhub", symbol, "error")
        raise MarketDataException(symbol, data['error'])

    if "c" not in data or data.get("c") == 0:
        logger.error(f"Missing or invalid price data for {symbol}: {data}")
        log_api_call("finnhub", symbol, "error")
        raise MarketDataException(symbol, "No price data available")

    log_api_call("finnhub", symbol, "success")
    return data


async def fetch_closing_price(symbol: str) -> Tuple[float, str]:
    """
    Fetch previous market closing price and date for a symbol using Finnhub.
    Uses caching to reduce API calls.
    """
    # Check cache first
    cached = _closing_cache.get(symbol)
    if cached:
        logger.debug(f"Cache hit for closing price: {symbol}")
        return cached

    data = await _fetch_quote(symbol)

    # Get the previous day's closing price
    last_close = float(data["pc"])  # Previous close
    last_date = datetime.fromtimestamp(data["t"]).strftime('%Y-%m-%d')

    result = (last_close, last_date)
    _closing_cache.set(symbol, result)

    logger.debug(f"Fetched closing price for {symbol}: ${last_close}")
    return result


async def fetch_current_price(symbol: str) -> Tuple[float, str]:
    """
    Fetch the current market price with caching using Finnhub.
    Uses TTL cache to avoid excessive API calls.
    """
    # Check cache first
    cached = _price_cache.get(symbol)
    if cached:
        logger.debug(f"Cache hit for current price: {symbol}")
        return cached

    data = await _fetch_quote(symbol)

    price = float(data["c"])  # Current price
    last_date = datetime.fromtimestamp(data["t"]).strftime('%Y-%m-%d')

    result = (price, last_date)
    _price_cache.set(symbol, result)

    logger.debug(f"Fetched current price for {symbol}: ${price}")
    return result


# Synchronous wrappers for backwards compatibility
def fetch_closing_price_sync(symbol: str) -> Tuple[float, str]:
    """Synchronous wrapper for fetch_closing_price (for non-async contexts)."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(fetch_closing_price(symbol))


def fetch_current_price_sync(symbol: str) -> Tuple[float, str]:
    """Synchronous wrapper for fetch_current_price (for non-async contexts)."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(fetch_current_price(symbol))
