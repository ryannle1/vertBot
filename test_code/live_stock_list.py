# Living List of stock that the user would like to monitor 
import pandas as pd
import discord
from discord.ext import commands
import yfinance as yf

# Just merged the updated main branch to this branch, now pushing to see if the changed went though


# Second Iterations, havent figured out what each line does as I havent been able to test
intents = discord.Intents.default()
intents.message_content = True  # Needed for user input handling

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command(name="stocks")
async def get_stocks(ctx, *, symbols):
    tickers = [symbol.strip().upper() for symbol in symbols.split(",")]

    await ctx.send(f"Fetching stock data for: {', '.join(tickers)}...")

    try:
        data = yf.download(tickers, period="1d", interval="1m", group_by='ticker', threads=True)
        for ticker in tickers:
            if ticker in data:
                last_price = data[ticker]['Close'].dropna().iloc[-1]
                await ctx.send(f"**{ticker}** latest price: ${last_price:.2f}")
            else:
                await ctx.send(f"Could not fetch data for `{ticker}`")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {str(e)}")

# Replace 'YOUR_BOT_TOKEN' with your actual token
bot.run("YOUR_BOT_TOKEN")


##### First iteration, doesnt allow
# # 1. Ask user what stocks to monitor
# user_input = input("Enter stock symbols to monitor (comma-separated, e.g., AAPL,MSFT,GOOG): ")
# stock_list = [symbol.strip().upper() for symbol in user_input.split(",")]

# # 2. Download stock data using yfinance
# data = yf.download(stock_list, period="1d", interval="1m", group_by='ticker', threads=True)

# # 3. Display latest data
# for ticker in stock_list:
#     print(f"\nLatest data for {ticker}:")
#     if ticker in data:
#         print(data[ticker].tail(5))  # Show last 5 rows
#     else:
#         print("No data found or ticker might be invalid.")

