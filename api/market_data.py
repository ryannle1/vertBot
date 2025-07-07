# import yfinance as yf
import pytz
import datetime
from functools import lru_cache
from datetime import datetime, timedelta
import requests
import os
import time
from dotenv import load_dotenv
import logging

load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

def is_market_open():
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    # Market hours: 9:30am to 4:00pm Eastern, Mon-Fri
    return (now.weekday() < 5 and
            ((now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and
             (now.hour < 16)))

@lru_cache(maxsize=100)
def fetch_closing_price(symbol):
    """Fetch previous market closing price and date for a symbol using Finnhub."""
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "error" in data:
        raise ValueError(f"Error fetching data: {data['error']}")
    
    if "c" not in data or "t" not in data:
        raise ValueError("No price data found.")
    
    # Get the previous day's closing price
    last_close = float(data["pc"])  # Previous close
    last_date = datetime.fromtimestamp(data["t"]).strftime('%Y-%m-%d')
    
    return last_close, last_date

_price_cache = {}
_cache_ttl = timedelta(minutes=5)

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
        logging.error(f"Finnhub API Error for {symbol}: {data}")
        raise ValueError(f"Error fetching data: {data['error']}")
    
    if "c" not in data or "t" not in data:
        logging.error(f"Finnhub API Response missing data for {symbol}: {data}")
        raise ValueError("No price data found.")
    
    price = float(data["c"])  # Current price
    last_date = datetime.fromtimestamp(data["t"]).strftime('%Y-%m-%d')
    
    _price_cache[symbol] = (price, now)
    return price, last_date