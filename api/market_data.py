import yfinance as yf
import pytz
import datetime
from functools import lru_cache
from datetime import datetime, timedelta
import finnhub
import os
import time


FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

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
    # Get the last two trading days (to handle weekends/holidays)
    now = datetime.now()
    to_time = int(time.mktime(now.timetuple()))
    from_time = int(time.mktime((now - timedelta(days=7)).timetuple()))  # last 7 days for safety

    candles = finnhub_client.stock_candles(symbol, 'D', from_time, to_time)
    # candles['c'] is the list of close prices, candles['t'] is the list of timestamps
    if candles.get('s') != 'ok' or not candles.get('c') or len(candles['c']) < 2:
        raise ValueError("Not enough price data found.")

    # The last element is the most recent close, the second-to-last is the previous close
    last_close = candles['c'][-2]
    last_date = datetime.fromtimestamp(candles['t'][-2]).strftime('%Y-%m-%d')
    return float(last_close), last_date

_price_cache = {}
_cache_ttl = timedelta(minutes=5)

def fetch_current_price(symbol):
    """Fetch the current market price with caching using Finnhub."""
    now = datetime.now()
    if symbol in _price_cache:
        price, timestamp = _price_cache[symbol]
        if now - timestamp < _cache_ttl:
            return price, timestamp.strftime('%Y-%m-%d')

    # Fetch quote from Finnhub
    quote = finnhub_client.quote(symbol)
    # quote['c'] is the current price, quote['t'] is the timestamp
    if not quote or 'c' not in quote or quote['c'] is None:
        raise ValueError("No price data found.")

    price = float(quote['c'])
    # Convert timestamp to date string
    last_date = datetime.fromtimestamp(quote['t']).strftime('%Y-%m-%d') if quote.get('t') else now.strftime('%Y-%m-%d')

    _price_cache[symbol] = (price, now)
    return price, last_date