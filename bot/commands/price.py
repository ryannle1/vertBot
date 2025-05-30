from discord.ext import commands
from api.market_data import fetch_closing_price, fetch_current_price, is_market_open

@commands.command(name='price')
async def get_price(ctx, symbol: str):
    """Returns the latest closing price for the given stock symbol, with a distinctive message."""
    try:
        await ctx.message.delete()
    except Exception:
        pass
    symbol = symbol.upper()
    try:
        price, date = fetch_closing_price(symbol)
        message = (
            f"📈 **Stock Price Report** 📈\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Symbol:** `{symbol}`\n"
            f"**Last Close:** **${price:.2f}**\n"
            f"**Date:** `{date}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        await ctx.send(message)
    except Exception as e:
        await ctx.send(
            f"❌ Could not fetch closing price for `{symbol}`.\n"
            f"Error: `{e}`"
        )

@commands.command(name='current')
async def get_current_price(ctx, symbol: str):
    """Returns the current price for the given stock symbol, with a distinctive message."""
    try:
        await ctx.message.delete()
    except Exception:
        pass
    symbol = symbol.upper()
    if not is_market_open():
        await ctx.send(
            "⏰ The US stock market is currently closed. Please try again during open hours (9:30am–4:00pm Eastern, Mon–Fri)."
        )
        return
    try:
        price, date = fetch_current_price(symbol)
        message = (
            f"💹 **Live Price Update** 💹\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Symbol:** `{symbol}`\n"
            f"**Current Price:** **${price:.2f}**\n"
            f"**As of:** `{date}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        await ctx.send(message)
    except Exception as e:
        await ctx.send(
            f"❌ Could not fetch current price for `{symbol}`.\n"
            f"Error: `{e}`"
        )