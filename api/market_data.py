"""
Market data API wrapper for fetching stock prices.
Refactored to use centralized configuration and logging.
"""

import pytz
from functools import lru_cache
from datetime import datetime, timedelta
import requests
import time

import os
from dotenv import load_dotenv
from bot.utils.logger import get_logger, log_api_call
from bot.utils.exceptions import MarketDataException

# Load environment variables
load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
CACHE_TTL = 60  # seconds for market data cache

# Market hours constants
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_TIMEZONE = "US/Eastern"

logger = get_logger(__name__)

def is_market_open():
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

@lru_cache(maxsize=100)
def fetch_closing_price(symbol):
    """Fetch previous market closing price and date for a symbol using Finnhub."""
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "error" in data:
        logger.error(f"Finnhub API error for {symbol}: {data['error']}")
        log_api_call("finnhub", symbol, "error")
        raise MarketDataException(symbol, data['error'])
    
    if "c" not in data or "t" not in data:
        logger.error(f"Missing price data for {symbol}: {data}")
        log_api_call("finnhub", symbol, "error")
        raise MarketDataException(symbol, "No price data available")
    
    # Get the previous day's closing price
    last_close = float(data["pc"])  # Previous close
    last_date = datetime.fromtimestamp(data["t"]).strftime('%Y-%m-%d')
    
    log_api_call("finnhub", symbol, "success")
    logger.debug(f"Fetched closing price for {symbol}: ${last_close}")
    
    return last_close, last_date

# Price cache for current prices
_price_cache = {}
_cache_ttl = timedelta(seconds=CACHE_TTL)

def fetch_current_price(symbol):
    """Fetch the current market price with caching using Finnhub."""
    now = datetime.now()
    if symbol in _price_cache:
        price, timestamp = _price_cache[symbol]
        if now - timestamp < _cache_ttl:
            return price, timestamp.strftime('%Y-%m-%d')

    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "error" in data:
        logger.error(f"Finnhub API error for {symbol}: {data}")
        log_api_call("finnhub", symbol, "error")
        raise MarketDataException(symbol, data.get('error', 'Unknown error'))
    
    if "c" not in data or "t" not in data:
        logger.error(f"Missing price data for {symbol}: {data}")
        log_api_call("finnhub", symbol, "error")
        raise MarketDataException(symbol, "No price data available")
    
    price = float(data["c"])  # Current price
    last_date = datetime.fromtimestamp(data["t"]).strftime('%Y-%m-%d')
    
    _price_cache[symbol] = (price, now)
    
    log_api_call("finnhub", symbol, "success")
    logger.debug(f"Fetched current price for {symbol}: ${price}")
    
    return price, last_date