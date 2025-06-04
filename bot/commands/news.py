from discord.ext import commands
from api.news_data import fetch_news, fetch_general_market_news

@commands.command(name='stocknews')
async def get_news(ctx, symbol: str):
    """Returns recent news headlines for the given stock symbol."""
    try:
        await ctx.message.delete()
    except Exception as e:
        # Silently ignore if can't delete (missing perms, already deleted, etc)
        pass
    symbol = symbol.upper()
    try:
        articles = fetch_news(symbol)
        if not articles:
            await ctx.send(f"No news found for {symbol.upper()}.")
            return
        response = f"**Latest news for {symbol.upper()}:**\n"
        for art in articles[:5]:  # Show top 5
            response += f"- [{art['headline']}]({art['url']})\n"
        await ctx.send(response)
    except Exception as e:
        await ctx.send(f"Could not fetch news for {symbol.upper()}. Error: {e}")

@commands.command(name='news')
async def get_general_news(ctx):
    """Returns recent general market news headlines."""
    try:
        await ctx.message.delete()
    except Exception as e:
        # Silently ignore if can't delete (missing perms, already deleted, etc)
        pass
    try:
        articles = fetch_general_market_news()
        if not articles:
            await ctx.send("No general market news found.")
            return
        response = "**Latest general market news:**\n"
        for art in articles[:5]:  # Show top 5
            response += f"- [{art['headline']}]({art['url']})\n"
        await ctx.send(response)
    except Exception as e:
        await ctx.send(f"Could not fetch general market news. Error: {e}")