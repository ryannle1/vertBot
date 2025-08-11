"""
Central configuration and constants for VertBot.
System constants and defaults only - user configuration is loaded dynamically.
"""

import os
from typing import List

# Load environment variables (for API keys only)
from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# SYSTEM CONSTANTS (Not user-configurable)
# ============================================================================

# Bot Configuration
BOT_PREFIX = "!"
DELETE_COMMAND_MESSAGES = True
ERROR_MESSAGE_DELETE_AFTER = 10  # seconds

# Market Hours (US Eastern Time) - These are fixed by the market
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0
MARKET_TIMEZONE = "US/Eastern"

# Daily report scheduling defaults (users configure channel, not time)
DAILY_REPORT_HOUR = 16  # 4 PM market close
DAILY_REPORT_MINUTE = 0
DAILY_REPORT_TIMEZONE = "US/Eastern"

# ============================================================================
# API CONFIGURATION (From environment variables)
# ============================================================================

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")

# If running in Docker and OLLAMA_HOST is not set, use the service name
if OLLAMA_HOST == "http://localhost:11434" and os.getenv("DOCKER_ENV"):
    OLLAMA_HOST = "http://ollama:11434"

# ============================================================================
# DEFAULT VALUES (Used when user hasn't configured their own)
# ============================================================================

# Default stock symbols - only used if user hasn't configured their own
DEFAULT_STOCK_SYMBOLS: List[str] = [
    "AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", 
    "TSLA", "META", "NFLX", "COST", "KO"
]

# Price monitoring defaults
BIG_CHANGE_THRESHOLD = 2.5  # Percentage - users can override per guild
PRICE_CHECK_INTERVAL = 300  # seconds (5 minutes)

# ============================================================================
# FILE PATHS (System paths, not user-configurable)
# ============================================================================

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNELS_CONFIG_PATH = os.path.join(CONFIG_DIR, "channels.json")
TICKERS_CONFIG_PATH = os.path.join(CONFIG_DIR, "tickers.json")
TICKERS_CSV_PATH = os.path.join(os.path.dirname(CONFIG_DIR), "data", "tickers.csv")

# ============================================================================
# DISCORD STYLING (System defaults)
# ============================================================================

class EmbedColors:
    """Default embed colors for Discord messages."""
    SUCCESS = 0x00FF00  # Green
    ERROR = 0xFF0000    # Red
    WARNING = 0xFFFF00  # Yellow
    INFO = 0x0000FF     # Blue
    PRICE_UP = 0x00FF00 # Green for price increase
    PRICE_DOWN = 0xFF0000 # Red for price decrease
    PRICE_NEUTRAL = 0x808080 # Gray for no change

# ============================================================================
# STANDARD MESSAGES (System defaults)
# ============================================================================

class ErrorMessages:
    """Standard error messages used across the bot."""
    INVALID_TICKER = "Invalid ticker symbol. Please provide a valid stock ticker."
    API_ERROR = "Failed to fetch data from the API. Please try again later."
    NO_DATA = "No data available for this ticker."
    PERMISSION_DENIED = "You don't have permission to use this command."
    MARKET_CLOSED = "Market is currently closed. Trading hours: Mon-Fri, 9:30 AM - 4:00 PM ET"
    CONFIGURATION_ERROR = "Configuration error. Please contact an administrator."
class SuccessMessages:
    """Standard success messages used across the bot."""
    CHANNEL_SET = "Report channel has been set successfully!"
    TICKER_ADDED = "Ticker has been added to the watchlist."
    TICKER_REMOVED = "Ticker has been removed from the watchlist."
    REPORT_SENT = "Market report has been sent successfully."

# ============================================================================
# TECHNICAL SETTINGS (System configuration)
# ============================================================================

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Cache Configuration
CACHE_TTL = 60  # seconds for market data cache
NEWS_CACHE_TTL = 300  # seconds for news data cache

# Rate Limiting
RATE_LIMIT_CALLS = 60  # API calls
RATE_LIMIT_PERIOD = 60  # seconds

# AI Configuration
AI_MAX_RETRIES = 3
AI_TIMEOUT = 30  # seconds
AI_TEMPERATURE = 0.7
AI_TOP_P = 0.9
AI_TOP_K = 40

# Chart Configuration (defaults for chart generation)
CHART_DEFAULT_PERIOD = "1mo"  # Default time period for charts
CHART_DEFAULT_INTERVAL = "1d"  # Default interval for charts
CHART_WIDTH = 12
CHART_HEIGHT = 6
CHART_DPI = 100

# ============================================================================
# NOTES FOR DEVELOPERS
# ============================================================================
"""
User-configurable settings are stored in:
- channels.json: Discord channel IDs per guild for reports
- tickers.json: Stock tickers to monitor per guild
- .env: API keys and tokens

Users configure these through Discord commands:
- !setreportchannel - Set the report channel for their guild
- !addticker - Add tickers to monitor
- !removeticker - Remove tickers from monitoring
- !listtickers - View current ticker configuration

The bot loads user configuration dynamically from these files.
This constants.py file only contains system defaults and technical settings.
"""