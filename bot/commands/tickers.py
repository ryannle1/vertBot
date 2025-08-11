import json
import os
from discord.ext import commands
from api.market_data import fetch_current_price

TICKERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'tickers.json')

def load_tickers():
    """Load tickers from JSON file"""
    if os.path.exists(TICKERS_FILE):
        with open(TICKERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_tickers(data):
    """Save tickers to JSON file"""
    with open(TICKERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_guild_tickers(guild_id):
    """Get tickers for a specific guild"""
    tickers = load_tickers()
    return tickers.get(str(guild_id), [])

def set_guild_tickers(guild_id, ticker_list):
    """Set tickers for a specific guild"""
    tickers = load_tickers()
    tickers[str(guild_id)] = ticker_list
    save_tickers(tickers)

@commands.command(name="addticker")
@commands.has_permissions(administrator=True)
async def add_ticker(ctx, symbol: str):
    """
    Add a stock ticker to the monitoring list.
    Usage: !addticker AAPL
    """
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    symbol = symbol.upper().strip()
    
    # Validate ticker format (basic validation)
    if not symbol.isalpha() or len(symbol) > 5:
        await ctx.send("❌ Invalid ticker symbol. Please use a valid stock symbol (1-5 letters).")
        return
    
    # Test if ticker exists by trying to fetch current price
    try:
        price, _ = fetch_current_price(symbol)
        if price <= 0:
            await ctx.send(f"❌ Could not validate ticker `{symbol}`. Please check the symbol and try again.")
            return
    except Exception:
        await ctx.send(f"❌ Could not validate ticker `{symbol}`. Please check the symbol and try again.")
        return
    
    guild_id = str(ctx.guild.id)
    current_tickers = get_guild_tickers(guild_id)
    
    if symbol in current_tickers:
        await ctx.send(f"ℹ️ `{symbol}` is already in your monitoring list.")
        return
    
    current_tickers.append(symbol)
    set_guild_tickers(guild_id, current_tickers)
    
    await ctx.send(f"✅ Added `{symbol}` to your monitoring list! You now have {len(current_tickers)} ticker(s).")

@commands.command(name="removeticker")
@commands.has_permissions(administrator=True)
async def remove_ticker(ctx, symbol: str):
    """
    Remove a stock ticker from the monitoring list.
    Usage: !removeticker AAPL
    """
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    symbol = symbol.upper().strip()
    guild_id = str(ctx.guild.id)
    current_tickers = get_guild_tickers(guild_id)
    
    if symbol not in current_tickers:
        await ctx.send(f"ℹ️ `{symbol}` is not in your monitoring list.")
        return
    
    current_tickers.remove(symbol)
    set_guild_tickers(guild_id, current_tickers)
    
    await ctx.send(f"✅ Removed `{symbol}` from your monitoring list! You now have {len(current_tickers)} ticker(s).")

@commands.command(name="listtickers")
async def list_tickers(ctx):
    """
    List all stock tickers currently being monitored.
    """
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    guild_id = str(ctx.guild.id)
    current_tickers = get_guild_tickers(guild_id)
    
    if not current_tickers:
        await ctx.send("📋 **Your Monitoring List**\n━━━━━━━━━━━━━━━━━━━━━━\nNo tickers configured. Use `!addticker SYMBOL` to add some!")
        return
    
    ticker_list = "\n".join([f"• `{ticker}`" for ticker in sorted(current_tickers)])
    message = (
        f"📋 **Your Monitoring List**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{ticker_list}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Total:** {len(current_tickers)} ticker(s)"
    )
    
    await ctx.send(message)

@commands.command(name="resettickers")
@commands.has_permissions(administrator=True)
async def reset_tickers(ctx):
    """
    Reset your monitoring list to the default tickers.
    """
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    # Fallback stock symbols if config file is not available
    try:
        from config.constants import DEFAULT_STOCK_SYMBOLS
    except ImportError:
        STOCK_SYMBOLS = ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "TSLA", "META", "NFLX", "COST", "KO"]
    
    guild_id = str(ctx.guild.id)
    
    set_guild_tickers(guild_id, STOCK_SYMBOLS.copy())
    
    await ctx.send(
        f"✅ Reset to default tickers!\n"
        f"Your monitoring list now contains: {', '.join([f'`{ticker}`' for ticker in STOCK_SYMBOLS])}"
    )

@commands.command(name="cleartickers")
@commands.has_permissions(administrator=True)
async def clear_tickers(ctx):
    """
    Clear all tickers from your monitoring list.
    """
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    guild_id = str(ctx.guild.id)
    set_guild_tickers(guild_id, [])
    
    await ctx.send("🗑️ Cleared all tickers from your monitoring list. Use `!addticker SYMBOL` to add new ones.") 

@commands.command(name="tickerhelp")
async def ticker_help(ctx):
    """
    Show help for ticker management commands.
    """
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    help_message = (
        "📋 **Ticker Management Commands**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "**!addticker SYMBOL** - Add a stock to monitor\n"
        "**!removeticker SYMBOL** - Remove a stock from monitoring\n"
        "**!listtickers** - Show all monitored stocks\n"
        "**!resettickers** - Reset to default stocks\n"
        "**!cleartickers** - Clear all stocks\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "**Examples:**\n"
        "• `!addticker AAPL` - Add Apple\n"
        "• `!addticker TSLA` - Add Tesla\n"
        "• `!removeticker KO` - Remove Coca-Cola\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 **Note:** Only administrators can add/remove tickers."
    )
    
    await ctx.send(help_message) 