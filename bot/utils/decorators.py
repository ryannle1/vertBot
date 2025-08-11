import functools
import logging
from typing import Callable, Any

try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    # Create mock classes for testing
    class MockContext:
        def __init__(self):
            self.author = type('obj', (object,), {'guild_permissions': type('obj', (object,), {'administrator': True})})()
            self.message = type('obj', (object,), {})()
        
        async def send(self, *args, **kwargs):
            pass
    
    class MockCommands:
        class MissingRequiredArgument(Exception):
            def __init__(self, param):
                self.param = type('obj', (object,), {'name': 'test_param'})()
        
        class BadArgument(Exception):
            pass
        
        Context = MockContext
    
    class MockDiscord:
        Forbidden = Exception
        NotFound = Exception
        HTTPException = Exception
    
    commands = MockCommands()
    discord = MockDiscord()

logger = logging.getLogger(__name__)


def delete_command_message(func: Callable) -> Callable:
    """
    Decorator that automatically deletes the command message after processing.
    Used to keep Discord channels clean by removing command invocations.
    """
    @functools.wraps(func)
    async def wrapper(ctx: commands.Context, *args, **kwargs):
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException) as e:
            logger.debug(f"Could not delete command message: {e}")
        except Exception as e:
            logger.debug(f"Unexpected error deleting message: {e}")
        
        return await func(ctx, *args, **kwargs)
    
    return wrapper


def handle_errors(
    error_message: str = "An error occurred while processing your command.",
    log_errors: bool = True,
    delete_after: int = 10
) -> Callable:
    """
    Decorator for consistent error handling across bot commands.
    
    Args:
        error_message: Default error message to send to user
        log_errors: Whether to log errors to console/file
        delete_after: Seconds before error message is deleted (0 = don't delete)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(ctx: commands.Context, *args, **kwargs):
            try:
                return await func(ctx, *args, **kwargs)
            except commands.MissingRequiredArgument as e:
                error_msg = f"❌ Missing required argument: {e.param.name}"
                if log_errors:
                    logger.warning(f"Missing argument in {func.__name__}: {e}")
            except commands.BadArgument as e:
                error_msg = f"❌ Invalid argument: {str(e)}"
                if log_errors:
                    logger.warning(f"Bad argument in {func.__name__}: {e}")
            except discord.Forbidden:
                error_msg = "❌ I don't have permission to perform this action."
                if log_errors:
                    logger.error(f"Permission error in {func.__name__}")
            except Exception as e:
                error_msg = f"❌ {error_message}\n`Error: {str(e)}`"
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            
            # Send error message to Discord
            if delete_after > 0:
                await ctx.send(error_msg, delete_after=delete_after)
            else:
                await ctx.send(error_msg)
        
        return wrapper
    return decorator


def admin_only(func: Callable) -> Callable:
    """
    Decorator that restricts command usage to administrators only.
    """
    @functools.wraps(func)
    async def wrapper(ctx: commands.Context, *args, **kwargs):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ This command requires administrator permissions.", delete_after=5)
            return
        return await func(ctx, *args, **kwargs)
    
    return wrapper


def market_hours_only(func: Callable) -> Callable:
    """
    Decorator that checks if market is open before executing command.
    Useful for live price commands.
    """
    @functools.wraps(func)
    async def wrapper(ctx: commands.Context, *args, **kwargs):
        from api.market_data import is_market_open
        
        if not is_market_open():
            await ctx.send(
                "📊 **Market is closed**\n"
                "Trading hours: Monday-Friday, 9:30 AM - 4:00 PM ET\n"
                "Use `!price` for the last closing price.",
                delete_after=10
            )
            return
        return await func(ctx, *args, **kwargs)
    
    return wrapper