import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
import pytz
import datetime
import os
import json
from dotenv import load_dotenv
import asyncio

from bot.commands.report import load_channels
from bot.commands.tickers import get_guild_tickers

# Fallback stock symbols if config file is not available
try:
    from config.constants import STOCK_SYMBOLS
except ImportError:
    STOCK_SYMBOLS = ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "TSLA", "META", "NFLX", "COST", "KO"]

from api.news_data import fetch_news

from api.market_data import fetch_closing_price
from api.market_data import fetch_current_price

from bot.utils.formatters import format_closing_price_report

# STOCK_SYMBOLS = ["AAPL", "NVDA", "MSFT", "AMZN", "CRWV", "KO", "GOOGL", "COST", "BTC"]  # Example symbols, can be extended or made dynamic

BIG_CHANGE_THRESHOLD = 2.5  # Percentage change threshold for significant price changes


# This dictionary will store the last announced "big change" to avoid spamming
announced_changes = {}


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Define the channel ID where the bot will send messages
CHANNEL_ID = 1376697868731027596  # Replace with your channel ID

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


# Initialize scheduler
scheduler = AsyncIOScheduler()






async def monitor_big_stock_changes():
    # Run periodic check during market hours
    eastern = pytz.timezone('US/Eastern')
    while True:
        now = datetime.datetime.now(eastern)
        # Market hours: 9:30am - 4:00pm Eastern, Monday-Friday
        if now.weekday() < 5 and (
            (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and
            (now.hour < 16)
        ):
            channels = load_channels()  # {guild_id: channel_id}
            for guild in bot.guilds:
                channel_id = channels.get(str(guild.id))
                if not channel_id:
                    continue  # Skip if no channel set for this guild
                channel = guild.get_channel(channel_id)
                if not channel:
                    continue
                
                # Get user-defined tickers for this guild
                guild_tickers = get_guild_tickers(guild.id)
                if not guild_tickers:
                    continue  # Skip if no tickers configured for this guild
                
                # Get yesterday's close for each stock (refresh daily for best accuracy)
                yesterdays_closes = {}
                for symbol in guild_tickers:
                    try:
                        price,_ = fetch_closing_price(symbol)
                        yesterdays_closes[symbol] = price
                    except Exception as e:
                        print(f"Could not fetch closing price for {symbol}: {e}")
                
                for symbol in guild_tickers:
                    try:
                        curr_price,_ = fetch_current_price(symbol)
                        close_price = yesterdays_closes.get(symbol)
                        if close_price:
                            pct_change = ((curr_price - close_price) / close_price) * 100
                            if abs(pct_change) >= BIG_CHANGE_THRESHOLD:
                                last_announcement = announced_changes.get((guild.id, symbol))
                                if not last_announcement or abs(pct_change) > abs(last_announcement):
                                    change_type = "up" if pct_change > 0 else "down"
                                    await channel.send(
                                        f"🚨 **{symbol.upper()}** is {change_type} {pct_change:.2f}% today!\n"
                                        f"Current price: ${curr_price:.2f} (Prev. close: ${close_price:.2f})"
                                    )
                                    announced_changes[(guild.id, symbol)] = pct_change
                        await asyncio.sleep(1)  # Slight delay to avoid rate limits
                    except Exception as e:
                        print(f"Error fetching current price for {symbol} in guild {guild.name}: {e}")
            await asyncio.sleep(600)  # Check every 10 minutes
        else:
            await asyncio.sleep(600)



# Load commands from commands/ directory
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    
    # Log current time in different timezones for debugging
    eastern = pytz.timezone('US/Eastern')
    utc = pytz.UTC
    now_eastern = datetime.datetime.now(eastern)
    now_utc = datetime.datetime.now(utc)
    
    print(f"Current time - UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Current time - Eastern: {now_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Day of week: {now_eastern.strftime('%A')} (weekday: {now_eastern.weekday()})")
    
    # Start scheduler
    scheduler.start()
    print("Scheduler started successfully")
    
    # Log scheduled jobs
    jobs = scheduler.get_jobs()
    print(f"Active scheduled jobs: {len(jobs)}")
    for job in jobs:
        next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z') if job.next_run_time else "Not scheduled"
        print(f"  - {job.id}: Next run at {next_run}")
    
    # Start the big stock changes monitor
    bot.loop.create_task(monitor_big_stock_changes())
    print("Big stock changes monitor started")


# Track if we've already sent a report today to avoid duplicates
daily_report_sent = False
last_report_date = None


# Scheduled job function for market close report
async def send_market_close_report():
    """Send market close report at 4:00 PM Eastern time"""
    global daily_report_sent, last_report_date
    
    await bot.wait_until_ready()
    
    # Check if it's a weekday
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    
    if now.weekday() >= 5:  # Weekend
        print(f"Market close report skipped - weekend ({now.strftime('%A')})")
        return
    
    # Reset daily flag if it's a new day
    if last_report_date != now.date():
        daily_report_sent = False
        last_report_date = now.date()
        print(f"Reset daily report flag for {now.date()}")
    
    # Check if we've already sent a report today
    if daily_report_sent:
        print(f"Market close report already sent today ({now.date()})")
        return
    
    print(f"Sending market close report at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    try:
        channels = load_channels()
        if not channels:
            print("No channels configured for market close reports")
            return
        
        for guild_id, channel_id in channels.items():
            guild = bot.get_guild(int(guild_id))
            if not guild:
                print(f"Guild {guild_id} not found")
                continue
                
            channel = guild.get_channel(channel_id)
            if not channel:
                print(f"Channel {channel_id} not found in guild {guild.name}")
                continue
            
            print(f"Sending market close report to {guild.name} - {channel.name}")
            
            # Get user-defined tickers for this guild
            guild_tickers = get_guild_tickers(guild.id)
            if not guild_tickers:
                print(f"No tickers configured for guild {guild.name}")
                continue
            
            # Send header message
            await channel.send("📊 **Daily Market Close Report** 📊\n━━━━━━━━━━━━━━━━━━━━━━")
            
            # Send report for each symbol
            for symbol in guild_tickers:
                try:
                    price, date = fetch_closing_price(symbol)
                    # Use the same format as the /price command
                    message = (
                        f"📈 **Stock Price Report** 📈\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"**Symbol:** `{symbol.upper()}`\n"
                        f"**Last Close:** **${price:.2f}**\n"
                        f"**Date:** `{date}`\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━"
                    )
                    await channel.send(message)
                    await asyncio.sleep(2)  # Rate limiting
                except Exception as e:
                    error_msg = f"⚠️ Could not fetch closing price for {symbol.upper()}. Error: {e}"
                    await channel.send(error_msg)
                    print(f"Error fetching {symbol}: {e}")
                    await asyncio.sleep(2)
            
            # Send footer
            await channel.send("━━━━━━━━━━━━━━━━━━━━━━\n📈 *Market close report complete*")
        
        # Mark as sent for today
        daily_report_sent = True
        print(f"Market close report completed successfully for {now.date()}")
        
    except Exception as e:
        print(f"Error in market close report: {e}")


# Schedule the task for 4pm US/Eastern every weekday
scheduler.add_job(
    send_market_close_report,
    'cron',
    day_of_week='mon-fri',
    hour=16, 
    minute=0,
    timezone=timezone('US/Eastern'),
    id='market_close_report'
)

print("Scheduled market close report for 4:00 PM Eastern time, weekdays only")



@bot.command(name="schedulerstatus")
@commands.has_permissions(administrator=True)
async def scheduler_status(ctx):
    """Check the status of scheduled jobs. Admin only."""
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    jobs = scheduler.get_jobs()
    if jobs:
        status_msg = "📅 **Scheduled Jobs:**\n"
        for job in jobs:
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z') if job.next_run_time else "Not scheduled"
            status_msg += f"• **{job.id}**: Next run at {next_run}\n"
    else:
        status_msg = "📅 No scheduled jobs found."
    
    await ctx.send(status_msg)


@bot.command(name="resetreport")
@commands.has_permissions(administrator=True)
async def reset_daily_report(ctx):
    """Manually reset the daily report flag. Admin only."""
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    global daily_report_sent, last_report_date
    daily_report_sent = False
    last_report_date = None
    
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    
    await ctx.send(f"🔄 Daily report flag reset. Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Daily report flag manually reset by {ctx.author.name} at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")


@bot.command(name="testchannel")
@commands.has_permissions(administrator=True)
async def test_channel(ctx):
    """Test if the bot can send messages to the configured report channel. Admin only."""
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    channels = load_channels()
    guild_id = str(ctx.guild.id)
    channel_id = channels.get(guild_id)
    
    if not channel_id:
        await ctx.send("❌ No report channel configured for this server. Use `!setreportchannel` first.")
        return
    
    channel = ctx.guild.get_channel(channel_id)
    if not channel:
        await ctx.send(f"❌ Configured channel {channel_id} not found in this server.")
        return
    
    # Check bot permissions
    bot_member = ctx.guild.get_member(bot.user.id)
    permissions = channel.permissions_for(bot_member)
    
    if not permissions.send_messages:
        await ctx.send(f"❌ Bot doesn't have permission to send messages in {channel.mention}")
        return
    
    if not permissions.view_channel:
        await ctx.send(f"❌ Bot doesn't have permission to view {channel.mention}")
        return
    
    # Test sending a message
    try:
        test_msg = await channel.send("🧪 **Test Message** - Bot is working correctly!")
        await ctx.send(f"✅ Successfully sent test message to {channel.mention}")
        
        # Delete test message after 5 seconds
        await asyncio.sleep(5)
        await test_msg.delete()
        
    except Exception as e:
        await ctx.send(f"❌ Failed to send test message: {e}")


# Add commands here for now
from bot.commands.price import get_price
from bot.commands.price import get_current_price
from bot.commands.news import get_news
from bot.commands.report import set_report_channel
from bot.commands.report import report
from bot.commands.ai import ask_ai
from bot.commands.news import get_general_news
from bot.commands.chart import get_stock_chart
from bot.commands.tickers import add_ticker, remove_ticker, list_tickers, reset_tickers, clear_tickers, ticker_help



# Register commands
bot.add_command(get_stock_chart)
bot.add_command(get_general_news)
bot.add_command(ask_ai)
bot.add_command(report)
bot.add_command(get_price)
bot.add_command(get_news)
bot.add_command(get_current_price)
bot.add_command(set_report_channel)
bot.add_command(add_ticker)
bot.add_command(remove_ticker)
bot.add_command(list_tickers)
bot.add_command(reset_tickers)
bot.add_command(clear_tickers)
bot.add_command(ticker_help)



"""ERROR HANDLING
   - Add error handling for commands to catch exceptions and send user-friendly messages.
   - Use `@bot.event` to handle errors globally or per command.
"""
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Missing required argument. Usage: `!price SYMBOL`")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❓ Unknown command. Please check your command or type `!help`.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ Invalid argument. Please check your input and try again.")
    elif isinstance(error, commands.CommandInvokeError):
        # This error wraps the actual error inside "original"
        original = getattr(error, "original", error)
        await ctx.send(f"🚨 Error: {original}")
    else:
        await ctx.send(f"🚨 An unexpected error occurred: {str(error)}")




if __name__ == "__main__":
    bot.run(TOKEN)