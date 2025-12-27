"""
News data API wrapper for fetching financial news.
Uses async aiohttp for non-blocking HTTP requests.
"""

import aiohttp
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any

from config.constants import MARKET_TIMEZONE
from config.settings import FINNHUB_API_KEY


async def fetch_news(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetch company-specific news for a stock symbol.
    Returns top 5 news items from the past 4 days.
    """
    eastern = pytz.timezone(MARKET_TIMEZONE)
    now_eastern = datetime.now(eastern)
    days_ago = now_eastern - timedelta(days=4)

    url = 'https://finnhub.io/api/v1/company-news'
    params = {
        'symbol': symbol,
        'from': days_ago.strftime('%Y-%m-%d'),
        'to': now_eastern.strftime('%Y-%m-%d'),
        'token': FINNHUB_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()

    return data[:5]  # Return top 5 news items


async def fetch_general_market_news() -> List[Dict[str, Any]]:
    """
    Fetch general market news.
    Returns top 15 general market news items.
    """
    url = "https://finnhub.io/api/v1/news"
    params = {
        "category": "general",
        "token": FINNHUB_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()

    return data[:15]  # Return top 15 general market news items
