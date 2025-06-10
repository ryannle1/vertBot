import discord
from discord.ext import commands
import yfinance as yf
import matplotlib.pyplot as plt
import io

@commands.command(name="chart")
async def get_stock_chart(ctx, symbol: str, period: str = "1mo", interval: str = "1d"):
    """
    Fetches and sends a price chart for the given stock symbol.
    Usage: !chart SYMBOL [period] [interval]
    Example: !chart AAPL 6mo 1d
    """
    try:
        await ctx.message.delete()
    except Exception:
        pass

    symbol = symbol.upper()
    await ctx.send(f"📈 Fetching chart for `{symbol}` ({period}, {interval})...")

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            await ctx.send(f"❌ No data found for `{symbol}`.")
            return

        plt.figure(figsize=(10, 5))
        plt.plot(hist.index, hist["Close"], label="Close Price")
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

async def generate_chart_image(symbol: str, period: str = "1mo", interval: str = "1d") -> io.BytesIO:
    """
    Generates a price chart for the given stock symbol and returns it as a BytesIO object.
    Does NOT send any Discord messages.
    """
    symbol = symbol.upper()
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period, interval=interval)
    if hist.empty:
        raise ValueError(f"No data found for {symbol}.")

    plt.figure(figsize=(10, 5))
    plt.plot(hist.index, hist["Close"], label="Close Price")
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