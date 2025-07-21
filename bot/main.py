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

from config.constants import STOCK_SYMBOLS

from bot.commands.report import load_channels

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
    # Get yesterday's close for each stock (one time at bot start; you may want to refresh this daily for best accuracy)
    yesterdays_closes = {}
    for symbol in STOCK_SYMBOLS:
        try:
            price,_ = fetch_closing_price(symbol)
            yesterdays_closes[symbol] = price
        except Exception as e:
            print(f"Could not fetch closing price for {symbol}: {e}")

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
                for symbol in STOCK_SYMBOLS:
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
    scheduler.start()
    bot.loop.create_task(monitor_big_stock_changes())




# Scheduled job function
def send_market_close_report():
    # Run in event loop because Discord API is async
    bot.loop.create_task(report_market_close())

async def report_market_close():
    await bot.wait_until_ready()
    reported_today = set()
    last_report_date = None
    while not bot.is_closed():
        import pytz, datetime
        eastern = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(eastern)

        # Reset the reported_today set at the start of a new day
        if last_report_date != now.date():
            reported_today = set()
            last_report_date = now.date()

        # 4:00 PM market close, Mon–Fri only
        if now.hour == 16 and now.minute == 0 and now.weekday() < 5:
            channels = load_channels()
            for guild in bot.guilds:
                channel_id = channels.get(str(guild.id))
                if not channel_id:
                    continue
                channel = guild.get_channel(channel_id)
                if not channel:
                    continue
                for symbol in STOCK_SYMBOLS:
                    # Only report if not already reported today
                    if (guild.id, symbol) in reported_today:
                        continue
                    try:
                        price, date = fetch_closing_price(symbol)
                        msg = format_closing_price_report(symbol, price, date)
                        await channel.send(msg)
                        reported_today.add((guild.id, symbol))
                        await asyncio.sleep(2)  # Shorter sleep since news is removed
                    except Exception as e:
                        await channel.send(f"⚠️ Could not fetch closing price for {symbol.upper()}. Error: {e}")
                        continue
                await asyncio.sleep(1)  # Prevent rate limits between guilds
            # After sending reports, sleep until the minute is no longer 16:00 to avoid duplicate sends
            while True:
                now = datetime.datetime.now(eastern)
                if not (now.hour == 16 and now.minute == 0):
                    break
                await asyncio.sleep(5)
            await asyncio.sleep(1)  # Small buffer before next loop
        else:
            await asyncio.sleep(20)

    

# Schedule the task for 4pm US/Eastern every day
scheduler.add_job(
    send_market_close_report,
    'cron',
    hour=16, minute=0,
    timezone=timezone('US/Eastern')
)





# Add commands here for now
from bot.commands.price import get_price
from bot.commands.price import get_current_price
from bot.commands.news import get_news
from bot.commands.report import set_report_channel
from bot.commands.report import report
from bot.commands.ai import ask_ai
from bot.commands.news import get_general_news
from bot.commands.chart import get_stock_chart



# Register commands
bot.add_command(get_stock_chart)
bot.add_command(get_general_news)
bot.add_command(ask_ai)
bot.add_command(report)
bot.add_command(get_price)
bot.add_command(get_news)
bot.add_command(get_current_price)
bot.add_command(set_report_channel)



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