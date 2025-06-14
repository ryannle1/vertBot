import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytz
from api.news_data import fetch_news, fetch_general_market_news

class TestNewsData(unittest.TestCase):
    def setUp(self):
        self.eastern = pytz.timezone('US/Eastern')
        self.mock_news_data = [
            {
                "category": "company",
                "datetime": 1704067200,
                "headline": "Test News 1",
                "id": 1,
                "image": "http://example.com/image1.jpg",
                "related": "AAPL",
                "source": "Test Source",
                "summary": "Test Summary 1",
                "url": "http://example.com/news1"
            },
            {
                "category": "company",
                "datetime": 1704067200,
                "headline": "Test News 2",
                "id": 2,
                "image": "http://example.com/image2.jpg",
                "related": "AAPL",
                "source": "Test Source",
                "summary": "Test Summary 2",
                "url": "http://example.com/news2"
            }
        ]

    @patch('api.news_data.requests.get')
    def test_fetch_news_success(self, mock_get):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = self.mock_news_data
        mock_get.return_value = mock_response

        news = fetch_news("AAPL")
        self.assertEqual(len(news), 2)
        self.assertEqual(news[0]["headline"], "Test News 1")
        self.assertEqual(news[1]["headline"], "Test News 2")

    @patch('api.news_data.requests.get')
    def test_fetch_news_error(self, mock_get):
        # Mock API error
        mock_get.side_effect = Exception("API Error")

        with self.assertRaises(Exception):
            fetch_news("AAPL")

    @patch('api.news_data.requests.get')
    def test_fetch_news_empty_response(self, mock_get):
        # Mock empty API response
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        news = fetch_news("AAPL")
        self.assertEqual(len(news), 0)

    @patch('api.news_data.requests.get')
    def test_fetch_general_market_news_success(self, mock_get):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = self.mock_news_data * 8  # 16 items
        mock_get.return_value = mock_response

        news = fetch_general_market_news()
        self.assertEqual(len(news), 15)  # Should return top 15 items

    @patch('api.news_data.requests.get')
    def test_fetch_general_market_news_error(self, mock_get):
        # Mock API error
        mock_get.side_effect = Exception("API Error")

        with self.assertRaises(Exception):
            fetch_general_market_news()

    @patch('api.news_data.requests.get')
    def test_fetch_general_market_news_empty_response(self, mock_get):
        # Mock empty API response
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        news = fetch_general_market_news()
        self.assertEqual(len(news), 0)

if __name__ == '__main__':
    unittest.main()
