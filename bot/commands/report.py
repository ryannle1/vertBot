import json
import os
from discord.ext import commands
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from api.market_data import fetch_closing_price, fetch_current_price
from api.news_data import fetch_news
from config.constants import STOCK_SYMBOLS

CHANNELS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'channels.json')


def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_channels(data):
    with open(CHANNELS_FILE, "w") as f:
        json.dump(data, f)

def get_report_channel_id(guild_id):
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
        await ctx.send("ℹ️ This channel is already set for daily stock reports.")
    else:
        channels[guild_id] = ctx.channel.id
        save_channels(channels)
        if current_channel:
            await ctx.send("✅ Updated! This channel is now set for daily stock reports (replacing the previous one).")
        else:
            await ctx.send("✅ This channel has been set for daily stock reports.")



@commands.command(name="report")
async def report(ctx):
    """
    Send a manual market close report for all tracked symbols.
    """
    try:
        await ctx.message.delete()
    except Exception:
        pass

    for symbol in STOCK_SYMBOLS:
        try:
            close_price, date = fetch_closing_price(symbol)
            current_price, _ = fetch_current_price(symbol)
            pct_change = ((current_price - close_price) / close_price) * 100 if close_price else 0
            change_str = f"{pct_change:+.2f}%"
            message = (
                f"📊 **Market Close Report** 📊\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**Symbol:** `{symbol.upper()}`\n"
                f"**Last Close:** **${close_price:.2f}** (`{date}`)\n"
                f"**Current Price:** **${current_price:.2f}**\n"
                f"**Change:** `{change_str}` from last close\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            )
            await ctx.send(message)
        except Exception as e:
            await ctx.send(f"⚠️ Could not fetch price for {symbol.upper()}. Error: {e}")
            continue

        # Send news
        try:
            articles = fetch_news(symbol)
            if articles:
                news_lines = [f"- [{art['title']}]({art['url']})" for art in articles[:5]]
                news_message = f"Latest news for {symbol.upper()}:\n" + "\n".join(news_lines)
            else:
                news_message = f"No recent news found for {symbol.upper()}."
            await ctx.send(news_message)
        except Exception as e:
            await ctx.send(f"⚠️ Could not fetch news for {symbol.upper()}. Error: {e}")

        await ctx.channel.typing()
        await ctx.bot.loop.run_in_executor(None, lambda: None)  # Small async pause to avoid rate limits
