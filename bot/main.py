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
        self.price_monitoring_task: Optional[asyncio.Task] = None
        self.last_price_check: Optional[datetime.datetime] = None
        self.last_daily_report: Optional[datetime.datetime] = None
        self.scheduler_watchdog_task: Optional[asyncio.Task] = None
    
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
    
    def update_price_check_time(self):
        """Update the last price check timestamp."""
        self.last_price_check = datetime.datetime.now()
    
    def update_daily_report_time(self):
        """Update the last daily report timestamp."""
        self.last_daily_report = datetime.datetime.now()
    
    def is_price_monitoring_active(self) -> bool:
        """Check if price monitoring is actively running."""
        if not self.last_price_check:
            return False
        
        # Check if price monitoring has been active in the last 10 minutes
        time_since_last_check = datetime.datetime.now() - self.last_price_check
        return time_since_last_check.total_seconds() < 600  # 10 minutes
    
    def is_daily_report_active(self) -> bool:
        """Check if daily report is actively running."""
        if not self.last_daily_report:
            return False
        
        # Check if daily report has been sent in the last 24 hours
        time_since_last_report = datetime.datetime.now() - self.last_daily_report
        return time_since_last_report.total_seconds() < 86400  # 24 hours
    
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
    
    async def restart_scheduler_if_needed(self):
        """Restart the scheduler if it's not running."""
        try:
            if not scheduler.running:
                logger.warning("Scheduler is not running, attempting to restart...")
                
                # Stop any existing scheduler
                try:
                    scheduler.shutdown()
                except:
                    pass
                
                # Schedule daily report
                scheduler.add_job(
                    send_daily_report,
                    'cron',
                    hour=DAILY_REPORT_HOUR,
                    minute=DAILY_REPORT_MINUTE,
                    timezone=DAILY_REPORT_TIMEZONE,
                    id='daily_market_report',
                    replace_existing=True,
                    misfire_grace_time=3600
                )
                
                # Schedule daily reset at midnight
                scheduler.add_job(
                    self.reset_daily_tracking,
                    'cron',
                    hour=0,
                    minute=0,
                    timezone=DAILY_REPORT_TIMEZONE,
                    id='daily_reset',
                    replace_existing=True,
                    misfire_grace_time=3600
                )
                
                # Start scheduler
                scheduler.start()
                logger.info("✅ Scheduler restarted successfully")
                
                # Verify it's running
                if scheduler.running:
                    jobs = scheduler.get_jobs()
                    logger.info(f"Scheduler running with {len(jobs)} jobs")
                else:
                    logger.error("❌ Scheduler failed to start after restart attempt")
                    
        except Exception as e:
            logger.error(f"Failed to restart scheduler: {e}", exc_info=True)

# Initialize market monitor
market_monitor = MarketMonitor()


async def monitor_price_changes():
    """Monitor stocks for significant price changes during market hours."""
    logger.info("Price monitoring task started")
    
    while True:
        try:
            # Update the last check time
            market_monitor.update_price_check_time()
            
            if not is_market_open():
                logger.debug("Market is closed, waiting for next check")
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
            # Don't exit the loop, just wait and try again
            await asyncio.sleep(PRICE_CHECK_INTERVAL)
            continue
        
        await asyncio.sleep(PRICE_CHECK_INTERVAL)


async def scheduler_watchdog():
    """Periodically check if the scheduler is running and restart if needed."""
    logger.info("Scheduler watchdog started")
    
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            
            # Check if scheduler is running
            if not scheduler.running:
                logger.warning("Scheduler watchdog detected scheduler is not running")
                await market_monitor.restart_scheduler_if_needed()
            else:
                logger.debug("Scheduler watchdog: scheduler is running normally")
                
        except Exception as e:
            logger.error(f"Error in scheduler watchdog: {e}", exc_info=True)
            await asyncio.sleep(300)  # Wait before next check


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
    try:
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
        market_monitor.update_daily_report_time()
        logger.info("Daily report completed successfully")
        
    except Exception as e:
        logger.error(f"Critical error in daily report: {e}", exc_info=True)
        # Update the time even on error to prevent infinite retries
        market_monitor.update_daily_report_time()


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
    
    # Debug: List all registered commands
    logger.info("=== REGISTERED COMMANDS ===")
    for cmd in bot.commands:
        logger.info(f"✓ {cmd.name}: {cmd.help or 'No help text'}")
    logger.info(f"Total commands: {len(bot.commands)}")
    logger.info("==========================")
    
    # Check if commands are properly loaded
    if len(bot.commands) == 0:
        logger.error("⚠️ NO COMMANDS LOADED! Bot will not respond to any commands!")
    else:
        logger.info(f"✅ {len(bot.commands)} commands loaded successfully")
    
    # Check bot permissions in each guild
    for guild in bot.guilds:
        logger.info(f"Guild: {guild.name} (ID: {guild.id})")
        
        # Check bot's permissions
        bot_member = guild.get_member(bot.user.id)
        if bot_member:
            permissions = bot_member.guild_permissions
            logger.info(f"  - Send Messages: {permissions.send_messages}")
            logger.info(f"  - Read Messages: {permissions.read_messages}")
            logger.info(f"  - Use Slash Commands: {permissions.use_slash_commands}")
    
    # Log timezone information for debugging
    eastern = pytz.timezone(MARKET_TIMEZONE)
    now_eastern = datetime.datetime.now(eastern)
    logger.info(f"Current Eastern time: {now_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"Day of week: {now_eastern.strftime('%A')}")
    
    # Initialize scheduler with error handling
    try:
        # Stop any existing scheduler
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Stopped existing scheduler")
        
        # Schedule daily report
        scheduler.add_job(
            send_daily_report,
            'cron',
            hour=DAILY_REPORT_HOUR,
            minute=DAILY_REPORT_MINUTE,
            timezone=DAILY_REPORT_TIMEZONE,
            id='daily_market_report',
            replace_existing=True,
            misfire_grace_time=3600  # Allow 1 hour grace period
        )
        
        # Schedule daily reset at midnight
        scheduler.add_job(
            market_monitor.reset_daily_tracking,
            'cron',
            hour=0,
            minute=0,
            timezone=DAILY_REPORT_TIMEZONE,
            id='daily_reset',
            replace_existing=True,
            misfire_grace_time=3600
        )
        
        # Start scheduler
        scheduler.start()
        logger.info("Scheduler started with daily report and reset jobs")
        
        # Verify scheduler is running
        if scheduler.running:
            logger.info("✅ Scheduler is running successfully")
            # List all scheduled jobs
            jobs = scheduler.get_jobs()
            logger.info(f"Scheduled jobs: {len(jobs)}")
            for job in jobs:
                logger.info(f"  - {job.id}: {job.next_run_time}")
        else:
            logger.error("❌ Scheduler failed to start")
            
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}", exc_info=True)
    
    # Start price monitoring task with better management
    try:
        # Cancel any existing task
        if market_monitor.price_monitoring_task and not market_monitor.price_monitoring_task.done():
            market_monitor.price_monitoring_task.cancel()
            logger.info("Cancelled existing price monitoring task")
        
        # Create new task
        market_monitor.price_monitoring_task = bot.loop.create_task(monitor_price_changes())
        logger.info("✅ Price monitoring task started")
        
    except Exception as e:
        logger.error(f"Failed to start price monitoring task: {e}", exc_info=True)
    
    # Start scheduler watchdog task
    try:
        # Cancel any existing watchdog task
        if market_monitor.scheduler_watchdog_task and not market_monitor.scheduler_watchdog_task.done():
            market_monitor.scheduler_watchdog_task.cancel()
            logger.info("Cancelled existing scheduler watchdog task")
        
        # Create new watchdog task
        market_monitor.scheduler_watchdog_task = bot.loop.create_task(scheduler_watchdog())
        logger.info("✅ Scheduler watchdog task started")
        
    except Exception as e:
        logger.error(f"Failed to start scheduler watchdog task: {e}", exc_info=True)


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


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors and provide helpful feedback."""
    if isinstance(error, commands.CommandNotFound):
        # Command not recognized
        logger.warning(f"Unknown command attempted: '{ctx.message.content}' by {ctx.author} in {ctx.guild}")
        
        # Send helpful message to user
        await ctx.send(
            f"❓ **Command not recognized:** `{ctx.message.content}`\n\n"
            f"**Available commands:**\n"
            f"• `!bothelp` - Show all commands\n"
            f"• `!help` - Show Discord.py built-in help\n"
            f"• `!price SYMBOL` - Get stock price\n"
            f"• `!addticker SYMBOL` - Add stock to monitor\n"
            f"• `!listtickers` - Show monitored stocks\n"
            f"• `!tickerhelp` - Get help with ticker commands"
        )
        
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ **Missing argument:** `{ctx.command}` requires `{error.param.name}`")
        logger.warning(f"Missing argument for {ctx.command}: {error.param.name}")
        
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"⚠️ **Invalid argument:** Please check your input for `{ctx.command}`")
        logger.warning(f"Bad argument for {ctx.command}: {error}")
        
    elif isinstance(error, commands.CommandInvokeError):
        # This wraps the actual error
        original_error = getattr(error, 'original', error)
        logger.error(f"Command {ctx.command} failed: {original_error}", exc_info=True)
        await ctx.send(f"🚨 **Error executing command:** {str(original_error)}")
        
    else:
        logger.error(f"Unhandled command error: {error}", exc_info=True)
        await ctx.send(f"🚨 **Unexpected error:** {str(error)}")


@bot.event
async def on_message(message):
    """Log all messages for debugging."""
    # Don't respond to bot's own messages
    if message.author == bot.user:
        return
    
    # Log message content (for debugging)
    if message.content.startswith('!'):
        logger.info(f"Command attempt: '{message.content}' by {message.author} in {message.guild}")
    
    # Process commands (required for on_message)
    await bot.process_commands(message)


@bot.event
async def on_command(ctx):
    """Log successful command usage."""
    logger.info(f"Command executed: {ctx.command.name} by {ctx.author} in {ctx.guild}")


@bot.event
async def on_command_completion(ctx):
    """Log successful command completion."""
    logger.info(f"Command completed: {ctx.command.name} by {ctx.author}")


@bot.command(name="ping")
async def ping(ctx):
    """Simple test command to verify bot is working."""
    await ctx.send("🏓 **Pong!** Bot is responding to commands!")
    logger.info("Ping command executed successfully")


@bot.command(name="bothelp")
async def bot_help_command(ctx):
    """Show help information and available commands."""
    help_embed = discord.Embed(
        title="🤖 VertBot Help",
        description="Your personal stock market monitoring assistant",
        color=0x00FF00
    )
    
    help_embed.add_field(
        name="📊 Stock Commands",
        value=(
            "• `!price SYMBOL` - Get stock closing price\n"
            "• `!current SYMBOL` - Get live stock price\n"
            "• `!chart SYMBOL` - Get price chart\n"
            "• `!news SYMBOL` - Get stock news"
        ),
        inline=False
    )
    
    help_embed.add_field(
        name="⚙️ Setup Commands",
        value=(
            "• `!setreportchannel` - Set daily report channel\n"
            "• `!addticker SYMBOL` - Add stock to monitor\n"
            "• `!removeticker SYMBOL` - Remove stock from monitoring\n"
            "• `!listtickers` - Show monitored stocks"
        ),
        inline=False
    )
    
    help_embed.add_field(
        name="🤖 AI Commands",
        value=(
            "• `!ask QUESTION` - Ask AI about stocks\n"
            "• `!tickerhelp` - Detailed ticker help"
        ),
        inline=False
    )
    
    help_embed.add_field(
        name="🔧 Utility Commands",
        value=(
            "• `!ping` - Test if bot is responding\n"
            "• `!bothelp` - Show this help message\n"
            "• `!help` - Show Discord.py built-in help\n"
            "• `!health` - Check bot health and task status\n"
            "• `!restart` - Restart scheduler (Admin only)"
        ),
        inline=False
    )
    
    help_embed.set_footer(text="Prefix: ! | Example: !price AAPL")
    
    await ctx.send(embed=help_embed)
    logger.info(f"Bot help command executed by {ctx.author}")


@bot.command(name="health")
async def health_check(ctx):
    """Check the health and status of the bot's scheduled tasks."""
    try:
        # Get current time in Eastern timezone
        eastern = pytz.timezone(MARKET_TIMEZONE)
        now_eastern = datetime.datetime.now(eastern)
        
        # Create health status embed
        health_embed = discord.Embed(
            title="🏥 VertBot Health Check",
            description=f"Status as of {now_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}",
            color=0x00FF00
        )
        
        # Check scheduler status
        scheduler_status = "✅ Running" if scheduler.running else "❌ Stopped"
        health_embed.add_field(
            name="📅 Scheduler Status",
            value=scheduler_status,
            inline=True
        )
        
        # Check scheduled jobs
        if scheduler.running:
            jobs = scheduler.get_jobs()
            job_info = f"**{len(jobs)} jobs scheduled**\n"
            for job in jobs:
                next_run = job.next_run_time
                if next_run:
                    next_run_eastern = next_run.astimezone(eastern)
                    job_info += f"• {job.id}: {next_run_eastern.strftime('%H:%M:%S')}\n"
                else:
                    job_info += f"• {job.id}: No next run time\n"
        else:
            job_info = "No jobs scheduled (scheduler not running)"
        
        health_embed.add_field(
            name="📋 Scheduled Jobs",
            value=job_info,
            inline=False
        )
        
        # Check price monitoring status
        price_monitoring_status = "✅ Active" if market_monitor.is_price_monitoring_active() else "❌ Inactive"
        health_embed.add_field(
            name="📊 Price Monitoring",
            value=price_monitoring_status,
            inline=True
        )
        
        # Check daily report status
        daily_report_status = "✅ Active" if market_monitor.is_daily_report_active() else "❌ Inactive"
        health_embed.add_field(
            name="📈 Daily Report",
            value=daily_report_status,
            inline=True
        )
        
        # Add last activity times
        if market_monitor.last_price_check:
            last_price_check_eastern = market_monitor.last_price_check.astimezone(eastern)
            health_embed.add_field(
                name="🕒 Last Price Check",
                value=last_price_check_eastern.strftime('%H:%M:%S'),
                inline=True
            )
        
        if market_monitor.last_daily_report:
            last_report_eastern = market_monitor.last_daily_report.astimezone(eastern)
            health_embed.add_field(
                name="🕒 Last Daily Report",
                value=last_report_eastern.strftime('%H:%M:%S'),
                inline=True
            )
        
        # Check market status
        market_status = "🟢 Open" if is_market_open() else "🔴 Closed"
        health_embed.add_field(
            name="🏛️ Market Status",
            value=market_status,
            inline=True
        )
        
        # Add overall health indicator
        overall_health = "🟢 Healthy"
        if not scheduler.running or not market_monitor.is_price_monitoring_active():
            overall_health = "🟡 Warning"
        if not scheduler.running and not market_monitor.is_price_monitoring_active():
            overall_health = "🔴 Critical"
        
        health_embed.add_field(
            name="🏥 Overall Health",
            value=overall_health,
            inline=False
        )
        
        await ctx.send(embed=health_embed)
        logger.info(f"Health check executed by {ctx.author}")
        
    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        await ctx.send(f"🚨 **Error during health check:** {str(e)}")


@bot.command(name="restart")
async def restart_scheduler(ctx):
    """Manually restart the scheduler if it's not working properly."""
    try:
        # Check if user has admin permissions
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ **Permission denied:** You need administrator permissions to restart the scheduler.")
            return
        
        await ctx.send("🔄 **Restarting scheduler...** Please wait.")
        
        # Restart the scheduler
        await market_monitor.restart_scheduler_if_needed()
        
        # Check if it's now running
        if scheduler.running:
            jobs = scheduler.get_jobs()
            await ctx.send(f"✅ **Scheduler restarted successfully!** Running with {len(jobs)} jobs.")
            logger.info(f"Scheduler manually restarted by {ctx.author}")
        else:
            await ctx.send("❌ **Scheduler restart failed.** Check the logs for more details.")
            logger.error(f"Manual scheduler restart failed for {ctx.author}")
            
    except Exception as e:
        logger.error(f"Error in manual scheduler restart: {e}", exc_info=True)
        await ctx.send(f"🚨 **Error during scheduler restart:** {str(e)}")


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