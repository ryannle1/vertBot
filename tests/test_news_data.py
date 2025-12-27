import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import pytz
import asyncio
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

    @patch('api.news_data.aiohttp.ClientSession')
    def test_fetch_news_success(self, mock_session_cls):
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=self.mock_news_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        news = asyncio.run(fetch_news("AAPL"))
        self.assertEqual(len(news), 2)
        self.assertEqual(news[0]["headline"], "Test News 1")
        self.assertEqual(news[1]["headline"], "Test News 2")

    @patch('api.news_data.aiohttp.ClientSession')
    def test_fetch_news_error(self, mock_session_cls):
        # Mock API error
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("API Error")
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        with self.assertRaises(Exception):
            asyncio.run(fetch_news("AAPL"))

    @patch('api.news_data.aiohttp.ClientSession')
    def test_fetch_news_empty_response(self, mock_session_cls):
        # Mock empty API response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        news = asyncio.run(fetch_news("AAPL"))
        self.assertEqual(len(news), 0)

    @patch('api.news_data.aiohttp.ClientSession')
    def test_fetch_general_market_news_success(self, mock_session_cls):
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=self.mock_news_data * 8)  # 16 items
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        news = asyncio.run(fetch_general_market_news())
        self.assertEqual(len(news), 15)  # Should return top 15 items

    @patch('api.news_data.aiohttp.ClientSession')
    def test_fetch_general_market_news_error(self, mock_session_cls):
        # Mock API error
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("API Error")
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        with self.assertRaises(Exception):
            asyncio.run(fetch_general_market_news())

    @patch('api.news_data.aiohttp.ClientSession')
    def test_fetch_general_market_news_empty_response(self, mock_session_cls):
        # Mock empty API response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        news = asyncio.run(fetch_general_market_news())
        self.assertEqual(len(news), 0)

if __name__ == '__main__':
    unittest.main()
