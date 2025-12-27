"""
AI command module for VertBot.
Handles AI-powered stock analysis using DeepSeek/Ollama.
"""

import re
import csv
import time
from collections import OrderedDict
from typing import List, Set, Deque, Tuple
from collections import deque
from discord.ext import commands

from ai.deepseek_llm import query_deepseek
from api.news_data import fetch_news, fetch_general_market_news
from api.market_data import fetch_current_price
from bot.commands.chart import get_stock_chart
from config.constants import MAX_CHAT_CHANNELS
from config.settings import DATA_DIR


class LRUChatMemory:
    """LRU-based chat memory with maximum channel limit to prevent memory leaks."""

    def __init__(self, max_channels: int = MAX_CHAT_CHANNELS, max_messages: int = 10):
        self._cache: OrderedDict[int, Deque[Tuple[str, str]]] = OrderedDict()
        self._max_channels = max_channels
        self._max_messages = max_messages

    def get(self, channel_id: int) -> Deque[Tuple[str, str]]:
        """Get chat history for a channel, creating if needed."""
        if channel_id in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(channel_id)
            return self._cache[channel_id]

        # Evict oldest if at capacity
        if len(self._cache) >= self._max_channels:
            self._cache.popitem(last=False)

        # Create new deque for this channel
        self._cache[channel_id] = deque(maxlen=self._max_messages)
        return self._cache[channel_id]

    def append(self, channel_id: int, role: str, message: str) -> None:
        """Append a message to the channel's history."""
        history = self.get(channel_id)
        history.append((role, message))

    def clear_channel(self, channel_id: int) -> None:
        """Clear history for a specific channel."""
        if channel_id in self._cache:
            del self._cache[channel_id]

    @property
    def channel_count(self) -> int:
        """Return the number of channels being tracked."""
        return len(self._cache)


# Global chat memory with LRU eviction
chat_memory = LRUChatMemory(max_channels=MAX_CHAT_CHANNELS, max_messages=10)


def remove_chain_of_thought(text: str) -> str:
    """Remove chain-of-thought markers from AI response."""
    marker = "</think>"
    idx = text.find(marker)
    if idx != -1:
        return text[idx + len(marker):].lstrip()

    # Fallback: try to find first ticker or bullet
    ticker_match = re.search(r"\b[A-Z]{2,5}:\b", text)
    bullet_match = re.search(r"^-", text, re.MULTILINE)
    if ticker_match:
        return text[ticker_match.start():]
    elif bullet_match:
        return text[bullet_match.start():]
    return text


def load_valid_tickers(csv_path: str = None) -> Set[str]:
    """Load valid tickers from CSV file."""
    if csv_path is None:
        csv_path = DATA_DIR / "tickers.csv"

    tickers = set()
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                ticker = row["Symbol"].strip().upper()
                tickers.add(ticker)
    except FileNotFoundError:
        # Return empty set if file doesn't exist
        pass
    except Exception:
        pass

    return tickers


# Load valid tickers at startup (with graceful handling if file missing)
VALID_TICKERS = load_valid_tickers()


def extract_tickers_from_message(msg: str) -> List[str]:
    """Extract valid stock tickers from a message."""
    pattern = r'\$([a-zA-Z]{1,5}\d{0,3}(?:\.[A-Za-z])?)'
    candidates = re.findall(pattern, msg)
    tickers = set()
    for c in candidates:
        t = c.upper()
        if t in VALID_TICKERS:
            tickers.add(t)
    return list(tickers)


@commands.command(name="ask")
async def ask_ai(ctx, *, question: str):
    """Ask AI about stocks or financial topics."""
    try:
        await ctx.message.delete()
    except Exception:
        pass

    channel_id = ctx.channel.id

    # Add user's message to history
    chat_memory.append(channel_id, "user", question)

    # Build prompt with history
    history = chat_memory.get(channel_id)
    history_lines = []
    for role, msg in history:
        if role == "user":
            history_lines.append(f"User: {msg}")
        else:
            history_lines.append(f"Bot: {msg}")

    tickers = extract_tickers_from_message(question)
    chart_mentions = []

    if tickers:
        news_blocks = []
        for ticker in tickers:
            # Fetch current price
            try:
                price, date = await fetch_current_price(ticker)
                price_line = f"Current price for {ticker}: ${price:.2f} (as of {date})"
            except Exception:
                price_line = f"Current price for {ticker}: unavailable"

            # Fetch news
            try:
                news_items = await fetch_news(ticker)
                if news_items:
                    news_headlines = "\n".join(
                        f"- {item.get('headline', '[No headline]')}" for item in news_items
                    )
                    news_blocks.append(f"{ticker}:\n{price_line}\n{news_headlines}")
                else:
                    news_blocks.append(f"{ticker}:\n{price_line}\nNo recent news found.")
            except Exception:
                news_blocks.append(f"{ticker}:\n{price_line}\nNews unavailable.")

            # Generate chart for each ticker
            try:
                await get_stock_chart(ctx, ticker)
                chart_mentions.append(f"A price chart for {ticker} is attached above.")
            except Exception as e:
                chart_mentions.append(f"Could not generate chart for {ticker}: {e}")

        # Combine news blocks and chart mentions
        news_prompt = "\n\n".join(news_blocks)
        chart_prompt = "\n".join(chart_mentions)

        prompt = (
            f"{news_prompt}\n"
            f"{chart_prompt}\n"
            "You are a helpful financial assistant. Below is the recent conversation:\n"
            f"{chr(10).join(history_lines)}\n"
            "Continue the conversation and answer the last question, using the provided current prices, news headlines, and the attached price charts for each ticker. Do NOT include any chain-of-thought or step-by-step thinking.\n"
        )
    else:
        # No tickers detected: use general market news
        try:
            news_items = await fetch_general_market_news()
            news_headlines = "\n".join(
                f"- {item.get('headline', '[No headline]')}" for item in news_items
            )
        except Exception:
            news_headlines = "Market news unavailable."

        prompt = (
            f"{news_headlines}\n"
            "You are a helpful financial assistant. Below is the recent conversation:\n"
            f"{chr(10).join(history_lines)}\n"
            "Continue the conversation and answer the last question in a concise, investor-focused way.\n"
        )

    await ctx.send("Thinking with DeepSeek R1...")
    await ctx.send("━━━━━━━━━━━━━━━━━━━━━━\n")

    try:
        response = await query_deepseek(prompt)
        response = remove_chain_of_thought(response)
        if response:
            # Send in safe 1900-character chunks
            for i in range(0, len(response), 1900):
                await ctx.send(response[i:i+1900])

            # Add bot response to history
            chat_memory.append(channel_id, "bot", response[:500])  # Store truncated version
        else:
            await ctx.send("I didn't get a response from the AI.")
    except Exception as e:
        await ctx.send(f"LLM error: {e}")

    await ctx.send("━━━━━━━━━━━━━━━━━━━━━━\n")


async def setup(bot):
    """Add AI commands to the bot."""
    bot.add_command(ask_ai)
