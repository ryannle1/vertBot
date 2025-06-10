import yfinance as yf
import pytz
import datetime
from functools import lru_cache
from datetime import datetime, timedelta




def is_market_open():
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    # Market hours: 9:30am to 4:00pm Eastern, Mon-Fri
    return (now.weekday() < 5 and
            ((now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and
             (now.hour < 16)))


@lru_cache(maxsize=100)
def fetch_closing_price(symbol):
    """Fetch previous market closing price and date for a symbol."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2d")  # Get last 2 days (in case of market holiday)
    if hist.empty or len(hist) < 2:
        raise ValueError("Not enough price data found.")
    last_close = hist['Close'].iloc[-2]
    last_date = hist.index[-2].strftime('%Y-%m-%d')
    return float(last_close), last_date

_price_cache = {}
_cache_ttl = timedelta(minutes=5)

def fetch_current_price(symbol):
    """Fetch the current market price with caching."""
    now = datetime.now()
    if symbol in _price_cache:
        price, timestamp = _price_cache[symbol]
        if now - timestamp < _cache_ttl:
            return price, timestamp.strftime('%Y-%m-%d')
    
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2d")
    if hist.empty:
        raise ValueError("No price data found.")
    last_close = hist['Close'].iloc[-1]
    last_date = hist.index[-1].strftime('%Y-%m-%d')
    
    _price_cache[symbol] = (float(last_close), now)
    return float(last_close), last_date