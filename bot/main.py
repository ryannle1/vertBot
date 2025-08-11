"""
VertBot main entry point - Refactored version.
Handles bot initialization, scheduling, and core functionality.
"""

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
import datetime
import asyncio
from typing import Dict, Optional, Set, Tuple

# Bot configuration constants
BOT_PREFIX = "!"
BIG_CHANGE_THRESHOLD = 2.5  # Percentage change threshold
PRICE_CHECK_INTERVAL = 300  # seconds (5 minutes)
DAILY_REPORT_HOUR = 16  # 4 PM market close
DAILY_REPORT_MINUTE = 0
DAILY_REPORT_TIMEZONE = "US/Eastern"
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_TIMEZONE = "US/Eastern"
# No default stock symbols - users must configure their own
from bot.commands.report import load_channels
from bot.commands.tickers import get_guild_tickers
from api.news_data import fetch_news
from api.market_data import fetch_closing_price, fetch_current_price, is_market_open
from bot.utils.logger import get_logger, log_api_call
from bot.utils.formatters import (
    create_market_report_embed, create_price_embed, 
    format_ticker, format_price, format_percentage
)
from bot.utils.exceptions import MarketDataException
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Initialize logger
logger = get_logger(__name__)

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

# Initialize scheduler
scheduler = AsyncIOScheduler()

# State tracking for avoiding duplicate announcements
class MarketMonitor:
    """Manages market monitoring state and logic."""
    
    def __init__(self):
        self.announced_changes: Dict[Tuple[int, str], float] = {}
        self.daily_report_sent: bool = False
        self.last_report_date: Optional[datetime.date] = None
        self.yesterdays_closes: Dict[str, float] = {}
        self.last_close_fetch: Optional[datetime.date] = None
    
    def should_announce_change(self, guild_id: int, symbol: str, pct_change: float) -> bool:
        """Check if a price change should be announced."""
        if abs(pct_change) < BIG_CHANGE_THRESHOLD:
            return False
        
        key = (guild_id, symbol)
        last_announcement = self.announced_changes.get(key)
        
        if not last_announcement or abs(pct_change) > abs(last_announcement):
            self.announced_changes[key] = pct_change
            return True
        return False
    
    def reset_daily_tracking(self):
        """Reset daily tracking variables."""
        self.daily_report_sent = False
        self.announced_changes.clear()
        logger.info("Daily tracking reset")
    
    async def fetch_closing_prices(self, symbols: list) -> Dict[str, float]:
        """Fetch closing prices for multiple symbols with caching."""
        today = datetime.date.today()
        
        # Only refresh closing prices once per day
        if self.last_close_fetch != today:
            self.yesterdays_closes.clear()
            self.last_close_fetch = today
            
        results = {}
        for symbol in symbols:
            if symbol not in self.yesterdays_closes:
                try:
                    price, _ = fetch_closing_price(symbol)
                    self.yesterdays_closes[symbol] = price
                    results[symbol] = price
                    log_api_call("market_data", symbol, "success")
                except Exception as e:
                    logger.error(f"Failed to fetch closing price for {symbol}: {e}")
                    log_api_call("market_data", symbol, "error")
            else:
                results[symbol] = self.yesterdays_closes[symbol]
        
        return results

# Initialize market monitor
market_monitor = MarketMonitor()


async def monitor_price_changes():
    """Monitor stocks for significant price changes during market hours."""
    logger.info("Price monitoring task started")
    
    while True:
        try:
            if not is_market_open():
                await asyncio.sleep(PRICE_CHECK_INTERVAL)
                continue
            
            channels = load_channels()
            
            for guild in bot.guilds:
                channel_id = channels.get(str(guild.id))
                if not channel_id:
                    continue
                
                channel = guild.get_channel(channel_id)
                if not channel:
                    continue
                
                guild_tickers = get_guild_tickers(guild.id)
                if not guild_tickers:
                    continue
                
                # Get closing prices (cached)
                closing_prices = await market_monitor.fetch_closing_prices(guild_tickers)
                
                # Check current prices for significant changes
                await check_price_changes(guild, channel, guild_tickers, closing_prices)
        
        except Exception as e:
            logger.error(f"Error in price monitoring: {e}", exc_info=True)
        
        await asyncio.sleep(PRICE_CHECK_INTERVAL)


async def check_price_changes(guild, channel, tickers, closing_prices):
    """Check for significant price changes and send alerts."""
    for symbol in tickers:
        try:
            if symbol not in closing_prices:
                continue
            
            current_price, _ = fetch_current_price(symbol)
            close_price = closing_prices[symbol]
            
            pct_change = ((current_price - close_price) / close_price) * 100
            
            if market_monitor.should_announce_change(guild.id, symbol, pct_change):
                await send_price_alert(channel, symbol, current_price, close_price, pct_change)
            
            await asyncio.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Error checking price for {symbol} in guild {guild.name}: {e}")


async def send_price_alert(channel, symbol: str, current_price: float, close_price: float, pct_change: float):
    """Send a price alert to the channel."""
    emoji = "📈" if pct_change > 0 else "📉"
    direction = "up" if pct_change > 0 else "down"
    
    embed = discord.Embed(
        title=f"{emoji} Price Alert: {format_ticker(symbol)}",
        description=f"**{format_ticker(symbol)}** is {direction} **{format_percentage(abs(pct_change))}** today!",
        color=0x00FF00 if pct_change > 0 else 0xFF0000
    )
    
    embed.add_field(name="Current Price", value=format_price(current_price), inline=True)
    embed.add_field(name="Previous Close", value=format_price(close_price), inline=True)
    embed.add_field(name="Change", value=format_percentage(pct_change), inline=True)
    
    await channel.send(embed=embed)
    logger.info(f"Price alert sent for {symbol}: {pct_change:.2f}% change")


async def send_daily_report():
    """Send daily market closing report to all configured channels."""
    eastern = pytz.timezone(DAILY_REPORT_TIMEZONE)
    now = datetime.datetime.now(eastern)
    
    # Check if we've already sent a report today
    if market_monitor.last_report_date == now.date():
        logger.debug("Daily report already sent today")
        return
    
    logger.info("Sending daily market report")
    channels = load_channels()
    
    for guild in bot.guilds:
        try:
            channel_id = channels.get(str(guild.id))
            if not channel_id:
                continue
            
            channel = guild.get_channel(channel_id)
            if not channel:
                logger.warning(f"Channel {channel_id} not found in guild {guild.name}")
                continue
            
            # Get guild's tracked tickers
            guild_tickers = get_guild_tickers(guild.id)
            if not guild_tickers:
                logger.info(f"No tickers configured for guild {guild.name} - skipping daily report")
                continue
            
            # Fetch market data
            stocks_data = await fetch_market_data(guild_tickers)
            
            if stocks_data:
                # Create and send report embed
                embed = create_market_report_embed(stocks_data, report_type="daily")
                await channel.send(embed=embed)
                logger.info(f"Daily report sent to guild {guild.name}")
            else:
                logger.warning(f"No market data available for guild {guild.name}")
        
        except Exception as e:
            logger.error(f"Error sending report to guild {guild.name}: {e}", exc_info=True)
    
    # Mark report as sent
    market_monitor.last_report_date = now.date()
    market_monitor.daily_report_sent = True


async def fetch_market_data(tickers: list) -> Dict[str, Dict]:
    """Fetch market data for multiple tickers."""
    data = {}
    
    for ticker in tickers:
        try:
            price, _ = fetch_closing_price(ticker)
            
            # Try to get previous day's close for change calculation
            # This is simplified - in production you'd want proper previous close data
            change = 0
            change_percent = 0
            
            data[ticker] = {
                'price': price,
                'change': change,
                'change_percent': change_percent
            }
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
    
    return data


@bot.event
async def on_ready():
    """Initialize bot when ready."""
    logger.info(f'Bot logged in as {bot.user}')
    
    # Log timezone information for debugging
    eastern = pytz.timezone(MARKET_TIMEZONE)
    now_eastern = datetime.datetime.now(eastern)
    logger.info(f"Current Eastern time: {now_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"Day of week: {now_eastern.strftime('%A')}")
    
    # Schedule daily report
    scheduler.add_job(
        send_daily_report,
        'cron',
        hour=DAILY_REPORT_HOUR,
        minute=DAILY_REPORT_MINUTE,
        timezone=DAILY_REPORT_TIMEZONE,
        id='daily_market_report',
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started with daily report job")
    
    # Start price monitoring task
    bot.loop.create_task(monitor_price_changes())
    logger.info("Price monitoring task started")


@bot.event
async def on_guild_join(guild):
    """Handle bot joining a new guild."""
    logger.info(f"Bot joined new guild: {guild.name} (ID: {guild.id})")
    
    # Try to send a welcome message to the first available text channel
    try:
        # Find the first text channel where the bot can send messages
        welcome_channel = None
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                welcome_channel = channel
                break
        
        if welcome_channel:
            welcome_embed = discord.Embed(
                title="🎉 Welcome to VertBot!",
                description="Your personal stock market monitoring assistant",
                color=0x00FF00
            )
            
            welcome_embed.add_field(
                name="🚀 Getting Started",
                value=(
                    "**1.** Set up your report channel: `!setreportchannel`\n"
                    "**2.** Add stocks to monitor: `!addticker AAPL`\n"
                    "**3.** View your list: `!listtickers`\n"
                    "**4.** Get help: `!tickerhelp`"
                ),
                inline=False
            )
            
            welcome_embed.add_field(
                name="📊 Available Commands",
                value=(
                    "• `!price SYMBOL` - Get stock price\n"
                    "• `!current SYMBOL` - Get live price\n"
                    "• `!news SYMBOL` - Get stock news\n"
                    "• `!chart SYMBOL` - Get price chart\n"
                    "• `!ask QUESTION` - Ask AI about stocks"
                ),
                inline=False
            )
            
            welcome_embed.set_footer(text="Configure your tickers to start receiving daily reports!")
            
            await welcome_channel.send(embed=welcome_embed)
            logger.info(f"Welcome message sent to {guild.name}")
        
    except Exception as e:
        logger.error(f"Failed to send welcome message to {guild.name}: {e}")


@bot.event
async def on_guild_remove(guild):
    """Handle bot being removed from a guild."""
    logger.info(f"Bot removed from guild: {guild.name} (ID: {guild.id})")


# Load all command modules
async def setup():
    """Load all command extensions."""
    command_modules = [
        'bot.commands.price',
        'bot.commands.news',
        'bot.commands.report',
        'bot.commands.tickers',
        'bot.commands.ai',
        'bot.commands.chart'
    ]
    
    for module in command_modules:
        try:
            await bot.load_extension(module)
            logger.info(f"Loaded extension: {module}")
        except Exception as e:
            logger.error(f"Failed to load extension {module}: {e}")


async def main():
    """Main entry point."""
    async with bot:
        await setup()
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)