import discord
from discord.ext import commands
import matplotlib.pyplot as plt
import io
import requests
from datetime import datetime, timedelta
import os

# Alpha Vantage API key - you'll need to set this as an environment variable
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

# This is the function that sends the chart to the user
@commands.command(name="chart")
async def get_stock_chart(ctx, symbol: str, period: str = "1mo", interval: str = "1d"):
    """
    Fetches and sends a price chart for the given stock symbol using Alpha Vantage API.
    Usage: !chart SYMBOL [period] [interval]
    Example: !chart AAPL 6mo 1d
    """
    if not ALPHA_VANTAGE_API_KEY:
        await ctx.send("❌ Alpha Vantage API key not configured. Please set the ALPHA_VANTAGE_API_KEY environment variable.")
        return

    try:
        await ctx.message.delete()
    except Exception:
        pass

    symbol = symbol.upper()
    await ctx.send(f"📈 Fetching chart for `{symbol}` ({period}, {interval})...")

    try:
        # Convert period to appropriate time range for Alpha Vantage
        if period == "1mo":
            time_range = "1month"
        elif period == "6mo":
            time_range = "6month"
        elif period == "1y":
            time_range = "1year"
        else:
            time_range = "1month"  # default to 1 month

        # Convert interval to appropriate output size
        if interval == "1d":
            output_size = "full"
        else:
            output_size = "compact"

        # Make API request to Alpha Vantage
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize={output_size}&apikey={ALPHA_VANTAGE_API_KEY}"
        response = requests.get(url)
        data = response.json()

        if "Error Message" in data:
            await ctx.send(f"❌ Error fetching data for `{symbol}`: {data['Error Message']}")
            return

        if "Time Series (Daily)" not in data:
            await ctx.send(f"❌ No data found for `{symbol}`.")
            return

        # Process the data
        time_series = data["Time Series (Daily)"]
        dates = []
        prices = []
        
        # Convert string dates to datetime objects and sort them
        for date_str in time_series.keys():
            date = datetime.strptime(date_str, "%Y-%m-%d")
            if period == "1mo" and date < datetime.now() - timedelta(days=30):
                continue
            elif period == "6mo" and date < datetime.now() - timedelta(days=180):
                continue
            elif period == "1y" and date < datetime.now() - timedelta(days=365):
                continue
            dates.append(date)
            prices.append(float(time_series[date_str]["4. close"]))

        # Sort the data by date
        dates, prices = zip(*sorted(zip(dates, prices)))

        # Create the chart
        plt.figure(figsize=(10, 5))
        plt.plot(dates, prices, label="Close Price")
        plt.title(f"{symbol} Price Chart ({period}, {interval})")
        plt.xlabel("Date")
        plt.ylabel("Price (USD)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()

        file = discord.File(buf, filename=f"{symbol}_chart.png")
        await ctx.send(file=file)
    except Exception as e:
        await ctx.send(f"❌ Error fetching chart for `{symbol}`: {e}")

# This is the function that generates the chart image for the AI to use (not used yet)
async def generate_chart_image(symbol: str, period: str = "1mo", interval: str = "1d") -> io.BytesIO:
    """
    Generates a price chart for the given stock symbol using Alpha Vantage API and returns it as a BytesIO object.
    Does NOT send any Discord messages.
    """
    if not ALPHA_VANTAGE_API_KEY:
        raise ValueError("Alpha Vantage API key not configured")

    symbol = symbol.upper()
    
    # Convert period to appropriate time range
    if period == "1mo":
        time_range = "1month"
    elif period == "6mo":
        time_range = "6month"
    elif period == "1y":
        time_range = "1year"
    else:
        time_range = "1month"

    # Convert interval to appropriate output size
    if interval == "1d":
        output_size = "full"
    else:
        output_size = "compact"

    # Make API request
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize={output_size}&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Error Message" in data:
        raise ValueError(f"Error fetching data: {data['Error Message']}")

    if "Time Series (Daily)" not in data:
        raise ValueError(f"No data found for {symbol}")

    # Process the data
    time_series = data["Time Series (Daily)"]
    dates = []
    prices = []
    
    # Convert string dates to datetime objects and sort them
    for date_str in time_series.keys():
        date = datetime.strptime(date_str, "%Y-%m-%d")
        if period == "1mo" and date < datetime.now() - timedelta(days=30):
            continue
        elif period == "6mo" and date < datetime.now() - timedelta(days=180):
            continue
        elif period == "1y" and date < datetime.now() - timedelta(days=365):
            continue
        dates.append(date)
        prices.append(float(time_series[date_str]["4. close"]))

    # Sort the data by date
    dates, prices = zip(*sorted(zip(dates, prices)))

    # Create the chart
    plt.figure(figsize=(10, 5))
    plt.plot(dates, prices, label="Close Price")
    plt.title(f"{symbol} Price Chart ({period}, {interval})")
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    return buf