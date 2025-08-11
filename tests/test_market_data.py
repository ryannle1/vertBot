import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytz
from api.market_data import is_market_open, fetch_closing_price, fetch_current_price
from bot.utils.exceptions import MarketDataException

class TestMarketData(unittest.TestCase):
    def setUp(self):
        self.eastern = pytz.timezone('US/Eastern')
        
    @patch('api.market_data.datetime')
    def test_is_market_open_during_market_hours(self, mock_datetime):
        # Test during market hours (10:00 AM ET on a weekday)
        mock_now = self.eastern.localize(datetime(2024, 1, 1, 10, 0))
        mock_datetime.now.return_value = mock_now
        self.assertTrue(is_market_open())

    @patch('api.market_data.datetime')
    def test_is_market_open_before_market_hours(self, mock_datetime):
        # Test before market hours (8:00 AM ET on a weekday)
        mock_now = self.eastern.localize(datetime(2024, 1, 1, 8, 0))
        mock_datetime.now.return_value = mock_now
        self.assertFalse(is_market_open())

    @patch('api.market_data.datetime')
    def test_is_market_open_after_market_hours(self, mock_datetime):
        # Test after market hours (5:00 PM ET on a weekday)
        mock_now = self.eastern.localize(datetime(2024, 1, 1, 17, 0))
        mock_datetime.now.return_value = mock_now
        self.assertFalse(is_market_open())

    @patch('api.market_data.datetime')
    def test_is_market_open_weekend(self, mock_datetime):
        # Test on weekend (Saturday)
        mock_now = self.eastern.localize(datetime(2024, 1, 6, 10, 0))
        mock_datetime.now.return_value = mock_now
        self.assertFalse(is_market_open())

    @patch('api.market_data.requests.get')
    def test_fetch_closing_price_success(self, mock_get):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pc": 150.25,  # Previous close
            "c": 151.25,   # Current price
            "t": 1704067200  # Unix timestamp
        }
        mock_get.return_value = mock_response

        price, date = fetch_closing_price("AAPL")
        self.assertEqual(price, 150.25)
        self.assertIsInstance(date, str)

    @patch('api.market_data.requests.get')
    def test_fetch_closing_price_error(self, mock_get):
        # Mock API error response
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid symbol"}
        mock_get.return_value = mock_response

        with self.assertRaises(MarketDataException):
            fetch_closing_price("INVALID")

    @patch('api.market_data.requests.get')
    def test_fetch_current_price_success(self, mock_get):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "c": 151.25,  # Current price
            "t": 1704067200  # Unix timestamp
        }
        mock_get.return_value = mock_response

        price, date = fetch_current_price("AAPL")
        self.assertEqual(price, 151.25)
        self.assertIsInstance(date, str)

    @patch('api.market_data.requests.get')
    def test_fetch_current_price_caching(self, mock_get):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "c": 151.25,
            "t": 1704067200
        }
        mock_get.return_value = mock_response

        # First call should hit the API
        price1, date1 = fetch_current_price("AAPL")
        self.assertEqual(price1, 151.25)

        # Second call within cache TTL should use cached value
        price2, date2 = fetch_current_price("AAPL")
        self.assertEqual(price2, 151.25)
        self.assertEqual(mock_get.call_count, 1)  # API should only be called once

    @patch('api.market_data.requests.get')
    def test_fetch_current_price_error(self, mock_get):
        # Mock API error response
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid symbol"}
        mock_get.return_value = mock_response

        with self.assertRaises(MarketDataException):
            fetch_current_price("INVALID")

if __name__ == '__main__':
    unittest.main()
