"""
Ticker management commands for VertBot.
Allows users to add/remove/list stock tickers for monitoring.
"""

import json
from discord.ext import commands
from api.market_data import fetch_current_price
from config.settings import TICKERS_FILE

def load_tickers():
    """Load tickers from JSON file."""
    if TICKERS_FILE.exists():
        with open(TICKERS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_tickers(data):
    """Save tickers to JSON file."""
    with open(TICKERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_guild_tickers(guild_id):
    """Get tickers for a specific guild."""
    tickers = load_tickers()
    return tickers.get(str(guild_id), [])


def set_guild_tickers(guild_id, ticker_list):
    """Set tickers for a specific guild."""
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

    # Validate ticker format
    if not symbol.isalpha() or len(symbol) > 5:
        await ctx.send("Invalid ticker symbol. Please use a valid stock symbol (1-5 letters).")
        return

    # Test if ticker exists by trying to fetch current price
    try:
        price, _ = await fetch_current_price(symbol)
        if price <= 0:
            await ctx.send(f"Could not validate ticker `{symbol}`. Please check the symbol and try again.")
            return
    except Exception:
        await ctx.send(f"Could not validate ticker `{symbol}`. Please check the symbol and try again.")
        return

    guild_id = str(ctx.guild.id)
    current_tickers = get_guild_tickers(guild_id)

    if symbol in current_tickers:
        await ctx.send(f"`{symbol}` is already in your monitoring list.")
        return

    current_tickers.append(symbol)
    set_guild_tickers(guild_id, current_tickers)

    await ctx.send(f"Added `{symbol}` to your monitoring list! You now have {len(current_tickers)} ticker(s).")


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
        await ctx.send(f"`{symbol}` is not in your monitoring list.")
        return

    current_tickers.remove(symbol)
    set_guild_tickers(guild_id, current_tickers)

    await ctx.send(f"Removed `{symbol}` from your monitoring list! You now have {len(current_tickers)} ticker(s).")


@commands.command(name="listtickers")
async def list_tickers(ctx):
    """List all stock tickers currently being monitored."""
    try:
        await ctx.message.delete()
    except Exception:
        pass

    guild_id = str(ctx.guild.id)
    current_tickers = get_guild_tickers(guild_id)

    if not current_tickers:
        await ctx.send(
            "**Your Monitoring List**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "No tickers configured yet!\n\n"
            "**To get started:**\n"
            "- Use `!addticker AAPL` to add Apple\n"
            "- Use `!addticker TSLA` to add Tesla\n"
            "- Use `!addticker GOOGL` to add Google\n\n"
            "**Then:**\n"
            "- Use `!setreportchannel` to set up daily reports\n"
            "- Use `!price SYMBOL` to check prices\n"
            "- Use `!tickerhelp` for more commands"
        )
        return

    ticker_list = "\n".join([f"- `{ticker}`" for ticker in sorted(current_tickers)])
    message = (
        f"**Your Monitoring List**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{ticker_list}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Total:** {len(current_tickers)} ticker(s)"
    )

    await ctx.send(message)


@commands.command(name="resettickers")
@commands.has_permissions(administrator=True)
async def reset_tickers(ctx):
    """Clear your monitoring list and start fresh."""
    try:
        await ctx.message.delete()
    except Exception:
        pass

    guild_id = str(ctx.guild.id)
    set_guild_tickers(guild_id, [])

    await ctx.send(
        "Cleared all tickers!\n"
        "Use `!addticker SYMBOL` to add stocks to monitor."
    )


@commands.command(name="tickerhelp")
async def ticker_help(ctx):
    """Show help for ticker management commands."""
    try:
        await ctx.message.delete()
    except Exception:
        pass

    help_message = (
        "**Ticker Management Commands**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "**!addticker SYMBOL** - Add a stock to monitor\n"
        "**!removeticker SYMBOL** - Remove a stock from monitoring\n"
        "**!listtickers** - Show all monitored stocks\n"
        "**!resettickers** - Clear all stocks and start fresh\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "**Examples:**\n"
        "- `!addticker AAPL` - Add Apple\n"
        "- `!addticker TSLA` - Add Tesla\n"
        "- `!removeticker KO` - Remove Coca-Cola\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Note: Only administrators can add/remove tickers.\n"
        "Tip: Start by adding a few stocks you want to monitor!"
    )

    await ctx.send(help_message)


async def setup(bot):
    """Add ticker management commands to the bot."""
    bot.add_command(add_ticker)
    bot.add_command(remove_ticker)
    bot.add_command(list_tickers)
    bot.add_command(reset_tickers)
    bot.add_command(ticker_help)
