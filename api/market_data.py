# import yfinance as yf
import pytz
import datetime
from functools import lru_cache
from datetime import datetime, timedelta
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../config/secrets.env'))
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

def is_market_open():
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    # Market hours: 9:30am to 4:00pm Eastern, Mon-Fri
    return (now.weekday() < 5 and
            ((now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and
             (now.hour < 16)))

@lru_cache(maxsize=100)
def fetch_closing_price(symbol):
    """Fetch previous market closing price and date for a symbol using Alpha Vantage."""
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "Error Message" in data:
        raise ValueError(f"Error fetching data: {data['Error Message']}")
    
    if "Time Series (Daily)" not in data:
        raise ValueError("No price data found.")
    
    # Get the last two trading days
    daily_data = data["Time Series (Daily)"]
    dates = sorted(daily_data.keys(), reverse=True)
    if len(dates) < 2:
        raise ValueError("Not enough price data found.")
    
    # Get the previous day's data (second most recent)
    last_date = dates[1]
    last_close = float(daily_data[last_date]["4. close"])
    
    return last_close, last_date

_price_cache = {}
_cache_ttl = timedelta(minutes=5)

def fetch_current_price(symbol):
    """Fetch the current market price with caching using Alpha Vantage."""
    now = datetime.now()
    if symbol in _price_cache:
        price, timestamp = _price_cache[symbol]
        if now - timestamp < _cache_ttl:
            return price, timestamp.strftime('%Y-%m-%d')

    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "Error Message" in data:
        raise ValueError(f"Error fetching data: {data['Error Message']}")
    
    if "Global Quote" not in data:
        raise ValueError("No price data found.")
    
    quote = data["Global Quote"]
    if not quote or "05. price" not in quote:
        raise ValueError("No price data found.")
    
    price = float(quote["05. price"])
    last_date = quote.get("07. latest trading day", now.strftime('%Y-%m-%d'))
    
    _price_cache[symbol] = (price, now)
    return price, last_date