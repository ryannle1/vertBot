"""
Centralized formatting utilities for VertBot.
Provides consistent message formatting across all commands.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import pytz

try:
    import discord
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    # Create mock discord.Embed for testing
    class MockEmbed:
        def __init__(self, **kwargs):
            self.title = kwargs.get('title')
            self.description = kwargs.get('description')
            self.color = kwargs.get('color')
            self.timestamp = kwargs.get('timestamp')
            self.fields = []
        
        def add_field(self, **kwargs):
            self.fields.append(kwargs)
            return self
        
        def set_footer(self, **kwargs):
            self.footer = kwargs
            return self
    
    class MockDiscord:
        Embed = MockEmbed
    
    discord = MockDiscord()

# Embed colors and timezone constants
class EmbedColors:
    """Default embed colors for Discord messages."""
    SUCCESS = 0x00FF00  # Green
    ERROR = 0xFF0000    # Red
    WARNING = 0xFFFF00  # Yellow
    INFO = 0x0000FF     # Blue
    PRICE_UP = 0x00FF00 # Green for price increase
    PRICE_DOWN = 0xFF0000 # Red for price decrease
    PRICE_NEUTRAL = 0x808080 # Gray for no change

MARKET_TIMEZONE = "US/Eastern"


def format_price(price: float, currency: str = "$") -> str:
    """Format a price value with proper currency and decimal places."""
    return f"{currency}{price:,.2f}"


def format_percentage(value: float, include_sign: bool = True) -> str:
    """Format a percentage value with proper sign and decimal places."""
    if include_sign and value > 0:
        return f"+{value:.2f}%"
    return f"{value:.2f}%"


def format_ticker(ticker: str) -> str:
    """Format a ticker symbol consistently."""
    return ticker.upper()


def get_price_emoji(change: float) -> str:
    """Get emoji based on price change."""
    if change > 0:
        return "📈"
    elif change < 0:
        return "📉"
    else:
        return "➡️"


def get_price_color(change: float) -> int:
    """Get embed color based on price change."""
    if change > 0:
        return EmbedColors.PRICE_UP
    elif change < 0:
        return EmbedColors.PRICE_DOWN
    else:
        return EmbedColors.PRICE_NEUTRAL


def format_closing_price_report(symbol: str, price: float, date: str) -> str:
    """
    Returns a formatted string for the closing price report.
    """
    return (
        f"\n==============================\n"
        f"  📈  {symbol.upper()} Market Close\n"
        f"------------------------------\n"
        f"  Price:      ${price:,.2f}\n"
        f"  Date:       {date}\n"
        f"=============================="
    )


def create_price_embed(
    ticker: str,
    price: float,
    change: Optional[float] = None,
    change_percent: Optional[float] = None,
    volume: Optional[int] = None,
    timestamp: Optional[datetime] = None,
    is_live: bool = False
) -> discord.Embed:
    """
    Create a formatted Discord embed for price information.
    
    Args:
        ticker: Stock ticker symbol
        price: Current/closing price
        change: Price change amount
        change_percent: Price change percentage
        volume: Trading volume
        timestamp: Time of the price
        is_live: Whether this is live or closing price
    """
    ticker = format_ticker(ticker)
    title = f"{ticker} - {'Live Price' if is_live else 'Closing Price'}"
    
    # Determine color based on change
    color = EmbedColors.INFO
    if change is not None:
        color = get_price_color(change)
        emoji = get_price_emoji(change)
        title = f"{emoji} {title}"
    
    embed = discord.Embed(title=title, color=color)
    
    # Add price field
    embed.add_field(
        name="💵 Price",
        value=format_price(price),
        inline=True
    )
    
    # Add change fields
    if change is not None and change_percent is not None:
        change_text = f"{format_price(abs(change))} ({format_percentage(change_percent)})"
        if change > 0:
            change_text = f"▲ {change_text}"
        elif change < 0:
            change_text = f"▼ {change_text}"
        else:
            change_text = f"→ {change_text}"
        
        embed.add_field(
            name="📊 Change",
            value=change_text,
            inline=True
        )
    
    # Add volume if available
    if volume:
        embed.add_field(
            name="📈 Volume",
            value=f"{volume:,}",
            inline=True
        )
    
    # Add timestamp
    if timestamp:
        embed.timestamp = timestamp
    else:
        embed.timestamp = datetime.now(pytz.timezone(MARKET_TIMEZONE))
    
    return embed


def create_news_embed(
    ticker: str,
    articles: List[Dict[str, Any]],
    max_articles: int = 5
) -> discord.Embed:
    """
    Create a formatted Discord embed for news articles.
    
    Args:
        ticker: Stock ticker symbol
        articles: List of news articles
        max_articles: Maximum number of articles to display
    """
    ticker = format_ticker(ticker)
    embed = discord.Embed(
        title=f"📰 Latest News for {ticker}",
        color=EmbedColors.INFO,
        timestamp=datetime.now(pytz.timezone(MARKET_TIMEZONE))
    )
    
    if not articles:
        embed.description = "No recent news found for this ticker."
        return embed
    
    # Add articles as fields
    for i, article in enumerate(articles[:max_articles], 1):
        title = article.get('headline', 'No title')[:100]  # Truncate long titles
        summary = article.get('summary', 'No summary available')[:200]  # Truncate summaries
        url = article.get('url', '')
        source = article.get('source', 'Unknown')
        
        # Format the article content
        if url:
            content = f"[{summary}...]({url})\n*Source: {source}*"
        else:
            content = f"{summary}...\n*Source: {source}*"
        
        embed.add_field(
            name=f"{i}. {title}",
            value=content,
            inline=False
        )
    
    if len(articles) > max_articles:
        embed.set_footer(text=f"Showing {max_articles} of {len(articles)} articles")
    
    return embed


def create_market_report_embed(
    stocks_data: Dict[str, Dict[str, Any]],
    report_type: str = "daily"
) -> discord.Embed:
    """
    Create a formatted Discord embed for market reports.
    
    Args:
        stocks_data: Dictionary of stock data {ticker: {price, change, change_percent}}
        report_type: Type of report (daily, weekly, etc.)
    """
    title = f"📊 {report_type.capitalize()} Market Report"
    embed = discord.Embed(
        title=title,
        color=EmbedColors.INFO,
        timestamp=datetime.now(pytz.timezone(MARKET_TIMEZONE))
    )
    
    if not stocks_data:
        embed.description = "No stock data available for this report."
        return embed
    
    # Group stocks by performance
    gainers = []
    losers = []
    unchanged = []
    
    for ticker, data in stocks_data.items():
        change_percent = data.get('change_percent', 0)
        if change_percent > 0:
            gainers.append((ticker, data))
        elif change_percent < 0:
            losers.append((ticker, data))
        else:
            unchanged.append((ticker, data))
    
    # Sort by absolute change percentage
    gainers.sort(key=lambda x: x[1].get('change_percent', 0), reverse=True)
    losers.sort(key=lambda x: x[1].get('change_percent', 0))
    
    # Add top gainers
    if gainers:
        gainers_text = []
        for ticker, data in gainers[:3]:
            price = data.get('price', 0)
            change_pct = data.get('change_percent', 0)
            gainers_text.append(
                f"**{format_ticker(ticker)}**: {format_price(price)} "
                f"(📈 {format_percentage(change_pct)})"
            )
        embed.add_field(
            name="🟢 Top Gainers",
            value="\n".join(gainers_text) or "None",
            inline=False
        )
    
    # Add top losers
    if losers:
        losers_text = []
        for ticker, data in losers[:3]:
            price = data.get('price', 0)
            change_pct = data.get('change_percent', 0)
            losers_text.append(
                f"**{format_ticker(ticker)}**: {format_price(price)} "
                f"(📉 {format_percentage(change_pct)})"
            )
        embed.add_field(
            name="🔴 Top Losers",
            value="\n".join(losers_text) or "None",
            inline=False
        )
    
    # Add summary
    total_stocks = len(stocks_data)
    embed.set_footer(
        text=f"Tracking {total_stocks} stocks | "
        f"↑ {len(gainers)} | ↓ {len(losers)} | → {len(unchanged)}"
    )
    
    return embed


def create_ai_response_embed(
    question: str,
    response: str,
    tickers: Optional[List[str]] = None
) -> discord.Embed:
    """
    Create a formatted Discord embed for AI responses.
    
    Args:
        question: User's question
        response: AI's response
        tickers: List of tickers mentioned in the question
    """
    embed = discord.Embed(
        title="🤖 AI Analysis",
        color=EmbedColors.INFO,
        timestamp=datetime.now()
    )
    
    # Add question
    embed.add_field(
        name="❓ Question",
        value=question[:200] + "..." if len(question) > 200 else question,
        inline=False
    )
    
    # Add response
    # Split response if it's too long
    if len(response) > 1024:
        # Split into multiple fields
        chunks = [response[i:i+1024] for i in range(0, len(response), 1024)]
        for i, chunk in enumerate(chunks[:3]):  # Max 3 chunks
            field_name = "💡 Analysis" if i == 0 else "​"  # Empty character for continuation
            embed.add_field(name=field_name, value=chunk, inline=False)
    else:
        embed.add_field(name="💡 Analysis", value=response, inline=False)
    
    # Add tickers if provided
    if tickers:
        embed.set_footer(text=f"Tickers analyzed: {', '.join(map(format_ticker, tickers))}")
    
    return embed


def create_error_embed(
    error_message: str,
    error_type: str = "Error",
    suggestions: Optional[List[str]] = None
) -> discord.Embed:
    """
    Create a formatted Discord embed for error messages.
    
    Args:
        error_message: The error message to display
        error_type: Type of error (Error, Warning, etc.)
        suggestions: List of suggestions to fix the error
    """
    embed = discord.Embed(
        title=f"❌ {error_type}",
        description=error_message,
        color=EmbedColors.ERROR,
        timestamp=datetime.now()
    )
    
    if suggestions:
        suggestions_text = "\n".join(f"• {s}" for s in suggestions)
        embed.add_field(
            name="💡 Suggestions",
            value=suggestions_text,
            inline=False
        )
    
    return embed


def format_simple_message(
    title: str,
    content: str,
    emoji: str = "📢",
    color: int = EmbedColors.INFO
) -> discord.Embed:
    """
    Create a simple formatted message embed.
    
    Args:
        title: Message title
        content: Message content
        emoji: Emoji to prefix the title
        color: Embed color
    """
    return discord.Embed(
        title=f"{emoji} {title}",
        description=content,
        color=color,
        timestamp=datetime.now()
    )


def format_ticker_list(tickers: List[str], columns: int = 3) -> str:
    """
    Format a list of tickers into a multi-column display.
    
    Args:
        tickers: List of ticker symbols
        columns: Number of columns to display
    """
    if not tickers:
        return "No tickers configured"
    
    tickers = [format_ticker(t) for t in tickers]
    
    # Calculate rows needed
    rows = (len(tickers) + columns - 1) // columns
    
    # Create grid
    lines = []
    for row in range(rows):
        row_tickers = []
        for col in range(columns):
            idx = row + col * rows
            if idx < len(tickers):
                row_tickers.append(f"`{tickers[idx]:6}`")
        lines.append(" ".join(row_tickers))
    
    return "\n".join(lines)