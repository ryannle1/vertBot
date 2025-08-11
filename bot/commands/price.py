"""
Price commands for fetching stock prices.
Refactored to use centralized utilities and consistent error handling.
"""

from discord.ext import commands
from api.market_data import fetch_closing_price, fetch_current_price
from bot.utils.decorators import delete_command_message, handle_errors, market_hours_only
from bot.utils.formatters import create_price_embed, format_ticker
from bot.utils.logger import get_logger, log_command
from bot.utils.exceptions import MarketDataException, InvalidTickerException

logger = get_logger(__name__)


@commands.command(name='price')
@delete_command_message
@handle_errors(error_message="Failed to fetch stock price")
async def get_price(ctx, symbol: str):
    """Returns the latest closing price for the given stock symbol."""
    log_command("price", ctx.author.name, ctx.guild.name if ctx.guild else "DM", symbol)
    
    symbol = format_ticker(symbol)
    
    try:
        price, date = fetch_closing_price(symbol)
        
        # Create embed with price information
        embed = create_price_embed(
            ticker=symbol,
            price=price,
            is_live=False
        )
        embed.set_footer(text=f"Closing price as of {date}")
        
        await ctx.send(embed=embed)
        logger.info(f"Price fetched successfully for {symbol}: ${price}")
        
    except ValueError as e:
        # Invalid ticker symbol
        raise InvalidTickerException(symbol)
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        raise MarketDataException(symbol, str(e))


@commands.command(name='current')
@delete_command_message
@market_hours_only
@handle_errors(error_message="Failed to fetch current price")
async def get_current_price(ctx, symbol: str):
    """Returns the current live price for the given stock symbol."""
    log_command("current", ctx.author.name, ctx.guild.name if ctx.guild else "DM", symbol)
    
    symbol = format_ticker(symbol)
    
    try:
        price, timestamp = fetch_current_price(symbol)
        
        # Create embed with live price information
        embed = create_price_embed(
            ticker=symbol,
            price=price,
            is_live=True
        )
        embed.set_footer(text=f"Live price as of {timestamp}")
        
        await ctx.send(embed=embed)
        logger.info(f"Current price fetched successfully for {symbol}: ${price}")
        
    except ValueError as e:
        # Invalid ticker symbol
        raise InvalidTickerException(symbol)
    except Exception as e:
        logger.error(f"Error fetching current price for {symbol}: {e}")
        raise MarketDataException(symbol, str(e))


async def setup(bot):
    """Add price commands to the bot."""
    bot.add_command(get_price)
    bot.add_command(get_current_price)