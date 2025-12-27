"""
Report commands for VertBot.
Handles daily market reports and report channel configuration.
"""

import json
import asyncio
from discord.ext import commands
from api.market_data import fetch_closing_price, fetch_current_price
from api.news_data import fetch_news
from bot.commands.tickers import get_guild_tickers
from config.settings import CHANNELS_FILE


def load_channels():
    """Load channel configuration from JSON file."""
    if CHANNELS_FILE.exists():
        with open(CHANNELS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_channels(data):
    """Save channel configuration to JSON file."""
    with open(CHANNELS_FILE, "w") as f:
        json.dump(data, f)


def get_report_channel_id(guild_id):
    """Get the report channel ID for a guild."""
    channels = load_channels()
    return channels.get(str(guild_id), None)


@commands.command(name="setreportchannel")
@commands.has_permissions(administrator=True)
async def set_report_channel(ctx):
    """
    Set the current channel as the stock report channel for scheduled reports.
    Admins only.
    """
    try:
        await ctx.message.delete()
    except Exception:
        pass

    channels = load_channels()
    guild_id = str(ctx.guild.id)
    current_channel = channels.get(guild_id)

    if current_channel == ctx.channel.id:
        await ctx.send("This channel is already set for daily stock reports.")
    else:
        channels[guild_id] = ctx.channel.id
        save_channels(channels)
        if current_channel:
            await ctx.send("Updated! This channel is now set for daily stock reports (replacing the previous one).")
        else:
            await ctx.send("This channel has been set for daily stock reports.")


@commands.command(name="report")
async def report(ctx):
    """Send a manual market close report for all tracked symbols."""
    try:
        await ctx.message.delete()
    except Exception:
        pass

    # Get user-defined tickers for this guild
    guild_tickers = get_guild_tickers(ctx.guild.id)
    if not guild_tickers:
        await ctx.send("No tickers configured for this server. Use `!addticker SYMBOL` to add some!")
        return

    for symbol in guild_tickers:
        try:
            close_price, date = await fetch_closing_price(symbol)
            current_price, _ = await fetch_current_price(symbol)
            pct_change = ((current_price - close_price) / close_price) * 100 if close_price else 0
            change_str = f"{pct_change:+.2f}%"
            message = (
                f"**Market Close Report**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**Symbol:** `{symbol.upper()}`\n"
                f"**Last Close:** **${close_price:.2f}** (`{date}`)\n"
                f"**Current Price:** **${current_price:.2f}**\n"
                f"**Change:** `{change_str}` from last close\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            )
            await ctx.send(message)
            await asyncio.sleep(2)
        except Exception as e:
            await ctx.send(f"Could not fetch price for {symbol.upper()}. Error: {e}")
            await asyncio.sleep(2)
            continue

        # Send news
        try:
            articles = await fetch_news(symbol)
            if articles:
                news_lines = [f"- [{art['headline']}]({art['url']})" for art in articles[:5]]
                news_message = f"Latest news for {symbol.upper()}:\n" + "\n".join(news_lines)
            else:
                news_message = f"No recent news found for {symbol.upper()}."
            await ctx.send(news_message)
            await asyncio.sleep(2)
        except Exception as e:
            await ctx.send(f"Could not fetch news for {symbol.upper()}. Error: {e}")
            await asyncio.sleep(2)


async def setup(bot):
    """Add report commands to the bot."""
    bot.add_command(set_report_channel)
    bot.add_command(report)
