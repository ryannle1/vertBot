import requests
import os
from dotenv import load_dotenv
from datetime import datetime, time, timedelta
import pytz

load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
# print("DEBUG Finnhub Key:", FINNHUB_API_KEY)

def fetch_news(symbol):
    eastern = pytz.timezone('US/Eastern')
    # Get the current date in Eastern timezone
    now_eastern = datetime.now(eastern)
    days_ago = now_eastern - timedelta(days=4)

    market_open = eastern.localize(datetime.combine(now_eastern.date(), time(9, 30)))

    url = f'https://finnhub.io/api/v1/company-news'
    params = {
        'symbol': symbol,
        'from': days_ago.strftime('%Y-%m-%d'),
        'to': now_eastern.strftime('%Y-%m-%d'),
        'token': FINNHUB_API_KEY
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    return data[:5]  # Return top 5 news items


def fetch_general_market_news():
    url = "https://finnhub.io/api/v1/news"
    params = {
        "category": "general",
        "token": FINNHUB_API_KEY
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    return data[:15]  # Return top 15 general market news items