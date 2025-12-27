"""
Centralized constants for VertBot.
All magic numbers and configuration values should be defined here.
"""

# Market timezone and hours
MARKET_TIMEZONE = "US/Eastern"
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

# Scheduled report settings
DAILY_REPORT_HOUR = 16  # 4 PM ET (market close)
DAILY_REPORT_MINUTE = 0

# Price monitoring settings
BIG_CHANGE_THRESHOLD = 2.5  # Percentage change to trigger alerts
PRICE_CHECK_INTERVAL = 300  # Seconds between price checks (5 minutes)

# Cache settings
CACHE_TTL_SECONDS = 60  # Time-to-live for price cache

# Memory limits
MAX_CHAT_CHANNELS = 1000  # Maximum number of channels to track in AI chat memory

# Bot settings
BOT_PREFIX = "!"
