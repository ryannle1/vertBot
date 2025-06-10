from discord.ext import commands
from ai.deepseek_llm import query_deepseek
from api.news_data import fetch_news, fetch_general_market_news  # Adjust path as needed
import re
import csv
import re
from collections import defaultdict, deque
from api.market_data import fetch_current_price  # Adjust path as needed
from bot.commands.chart import get_stock_chart  # Adjust path as needed

# Memory for each channel: channel_id -> deque of (role, message) tuples
chat_memory = defaultdict(lambda: deque(maxlen=10))  # keep last 10 exchanges per channel



def remove_chain_of_thought(text):
    # Try to find the end of the chain-of-thought marker
    marker = "</think>"
    idx = text.find(marker)
    if idx != -1:
        # Return everything after the marker
        return text[idx + len(marker):].lstrip()
    # Fallback: try to find first ticker or bullet
    # For example, look for 'NVDA:' or a dash/bullet
    ticker_match = re.search(r"\b[A-Z]{2,5}:\b", text)
    bullet_match = re.search(r"^-", text, re.MULTILINE)
    if ticker_match:
        return text[ticker_match.start():]
    elif bullet_match:
        return text[bullet_match.start():]
    return text  # No marker found, return as-is


def load_valid_tickers(csv_path="data/tickers.csv"):
    tickers = set()
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ticker = row["Symbol"].strip().upper()
            tickers.add(ticker)
    return tickers

VALID_TICKERS = load_valid_tickers()

def extract_tickers_from_message(msg):
    # Find all words starting with $, followed by 1–5 alphanumeric chars (case-insensitive)
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
    try:
        await ctx.message.delete()
    except Exception:
        pass
    channel_id = ctx.channel.id

    # Add user's message to history
    chat_memory[channel_id].append(("user", question))

    # Build prompt with history
    history_lines = []
    for role, msg in chat_memory[channel_id]:
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
                price, date = fetch_current_price(ticker)
                price_line = f"Current price for {ticker}: ${price:.2f} (as of {date})"
            except Exception:
                price_line = f"Current price for {ticker}: unavailable"

            # Fetch news
            news_items = fetch_news(ticker)
            if news_items:
                news_headlines = "\n".join(
                    f"- {item.get('headline', '[No headline]')}" for item in news_items
                )
                news_blocks.append(f"{ticker}:\n{price_line}\n{news_headlines}")
            else:
                news_blocks.append(f"{ticker}:\n{price_line}\nNo recent news found.")

            # Automatically generate and send chart for each ticker
            try:
                await get_stock_chart(ctx, ticker)
                chart_mentions.append(f"A price chart for {ticker} is attached above.")
            except Exception as e:
                chart_mentions.append(f"Could not generate chart for {ticker}: {e}")

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
        # No tickers detected: just answer the question directly
        news_items = fetch_general_market_news()
        news_headlines = "\n".join(f"- {item.get('headline', '[No headline]')}" for item in news_items)
        prompt = (
            f"{news_headlines}\n"
            "You are a helpful financial assistant. Below is the recent conversation:\n"
            f"{chr(10).join(history_lines)}\n"
            "Continue the conversation and answer the last question in a concise, investor-focused way.\n"
        )

    await ctx.send("💬 Thinking with DeepSeek...")
    await ctx.send(f"━━━━━━━━━━━━━━━━━━━━━━\n")

    try:
        response = query_deepseek(prompt)
        response = remove_chain_of_thought(response)
        if response:
            # Send in safe 1900-character chunks
            for i in range(0, len(response), 1900):
                await ctx.send(response[i:i+1900])
        else:
            await ctx.send("🤔 I didn't get a response from DeepSeek.")
    except Exception as e:
        await ctx.send(f"❌ LLM error: {e}")
    await ctx.send(f"━━━━━━━━━━━━━━━━━━━━━━\n")