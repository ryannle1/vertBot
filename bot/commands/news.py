"""
News commands for fetching financial news.
Refactored to use centralized utilities and consistent error handling.
"""

from discord.ext import commands
from api.news_data import fetch_news, fetch_general_market_news
from bot.utils.decorators import delete_command_message, handle_errors
from bot.utils.formatters import create_news_embed, format_ticker
from bot.utils.logger import get_logger, log_command
from bot.utils.exceptions import NewsDataException, InvalidTickerException

logger = get_logger(__name__)


@commands.command(name='stocknews')
@delete_command_message
@handle_errors(error_message="Failed to fetch stock news")
async def get_news(ctx, symbol: str):
    """Returns recent news headlines for the given stock symbol."""
    log_command("stocknews", ctx.author.name, ctx.guild.name if ctx.guild else "DM", symbol)

    symbol = format_ticker(symbol)

    try:
        articles = fetch_news(symbol)

        # Create embed with news articles
        embed = create_news_embed(symbol, articles)

        await ctx.send(embed=embed)
        logger.info(f"News fetched successfully for {symbol}: {len(articles)} articles")

    except ValueError:
        # Invalid ticker symbol
        raise InvalidTickerException(symbol)
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        raise NewsDataException(symbol, str(e))


@commands.command(name='news')
@delete_command_message
@handle_errors(error_message="Failed to fetch market news")
async def get_general_news(ctx):
    """Returns recent general market news headlines."""
    log_command("news", ctx.author.name, ctx.guild.name if ctx.guild else "DM", "general")

    try:
        articles = fetch_general_market_news()

        # Create embed with general market news
        embed = create_news_embed("Market", articles)
        embed.title = "📰 Latest Market News"

        await ctx.send(embed=embed)
        logger.info(f"General market news fetched successfully: {len(articles)} articles")

    except Exception as e:
        logger.error(f"Error fetching general market news: {e}")
        raise NewsDataException("Market", str(e))


async def setup(bot):
    """Add news commands to the bot."""
    bot.add_command(get_news)
    bot.add_command(get_general_news)