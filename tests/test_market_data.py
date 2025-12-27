"""
Tests for market data API functions.
Updated for async API using aiohttp.
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import pytz
import asyncio

from api.market_data import is_market_open, fetch_closing_price, fetch_current_price, _price_cache, _closing_cache
from bot.utils.exceptions import MarketDataException


class TestIsMarketOpen(unittest.TestCase):
    """Tests for the is_market_open function."""

    def setUp(self):
        self.eastern = pytz.timezone('US/Eastern')

    @patch('api.market_data.datetime')
    def test_is_market_open_during_market_hours(self, mock_datetime):
        # Test during market hours (10:00 AM ET on a weekday - Monday Jan 1, 2024)
        mock_now = self.eastern.localize(datetime(2024, 1, 2, 10, 0))  # Tuesday
        mock_datetime.now.return_value = mock_now
        self.assertTrue(is_market_open())

    @patch('api.market_data.datetime')
    def test_is_market_open_before_market_hours(self, mock_datetime):
        # Test before market hours (8:00 AM ET on a weekday)
        mock_now = self.eastern.localize(datetime(2024, 1, 2, 8, 0))  # Tuesday
        mock_datetime.now.return_value = mock_now
        self.assertFalse(is_market_open())

    @patch('api.market_data.datetime')
    def test_is_market_open_after_market_hours(self, mock_datetime):
        # Test after market hours (5:00 PM ET on a weekday)
        mock_now = self.eastern.localize(datetime(2024, 1, 2, 17, 0))  # Tuesday
        mock_datetime.now.return_value = mock_now
        self.assertFalse(is_market_open())

    @patch('api.market_data.datetime')
    def test_is_market_open_weekend(self, mock_datetime):
        # Test on weekend (Saturday)
        mock_now = self.eastern.localize(datetime(2024, 1, 6, 10, 0))  # Saturday
        mock_datetime.now.return_value = mock_now
        self.assertFalse(is_market_open())


class TestAsyncMarketData(unittest.IsolatedAsyncioTestCase):
    """Async tests for market data fetch functions."""

    def setUp(self):
        # Clear caches before each test
        _price_cache.clear()
        _closing_cache.clear()

    @patch('api.market_data.aiohttp.ClientSession')
    async def test_fetch_closing_price_success(self, mock_session_class):
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "pc": 150.25,  # Previous close
            "c": 151.25,   # Current price
            "t": 1704067200  # Unix timestamp
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        price, date = await fetch_closing_price("AAPL")
        self.assertEqual(price, 150.25)
        self.assertIsInstance(date, str)

    @patch('api.market_data.aiohttp.ClientSession')
    async def test_fetch_closing_price_error(self, mock_session_class):
        # Setup mock error response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"error": "Invalid symbol"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        with self.assertRaises(MarketDataException):
            await fetch_closing_price("INVALID")

    @patch('api.market_data.aiohttp.ClientSession')
    async def test_fetch_current_price_success(self, mock_session_class):
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "c": 151.25,  # Current price
            "t": 1704067200  # Unix timestamp
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        price, date = await fetch_current_price("AAPL")
        self.assertEqual(price, 151.25)
        self.assertIsInstance(date, str)

    @patch('api.market_data.aiohttp.ClientSession')
    async def test_fetch_current_price_caching(self, mock_session_class):
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "c": 151.25,
            "t": 1704067200
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        # First call should hit the API
        price1, date1 = await fetch_current_price("TEST_CACHE")
        self.assertEqual(price1, 151.25)

        # Second call within cache TTL should use cached value
        price2, date2 = await fetch_current_price("TEST_CACHE")
        self.assertEqual(price2, 151.25)

        # API should only be called once due to caching
        self.assertEqual(mock_session_class.call_count, 1)

    @patch('api.market_data.aiohttp.ClientSession')
    async def test_fetch_current_price_error(self, mock_session_class):
        # Setup mock error response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"error": "Invalid symbol"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        with self.assertRaises(MarketDataException):
            await fetch_current_price("INVALID_TEST")


if __name__ == '__main__':
    unittest.main()
