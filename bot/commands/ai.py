from discord.ext import commands
from ai.deepseek_llm import query_deepseek
from api.news_data import fetch_news  # Adjust path as needed
import re
import csv
import re


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

    tickers = extract_tickers_from_message(question)
    if not tickers:
        await ctx.send("No tickers detected. Please use the `$TICKER` format (e.g., `$AAPL`).")
        return
    news_blocks = []
    if tickers:
        for ticker in tickers:
            news_items = fetch_news(ticker)
            if news_items:
                news_headlines = "\n".join(
                    f"- {item.get('headline', '[No headline]')}" for item in news_items
                )
                news_blocks.append(f"{ticker}:\n{news_headlines}")
            else:
                news_blocks.append(f"{ticker}: No recent news found.")
        news_prompt = "\n\n".join(news_blocks)
        prompt = (
            "IMPORTANT: Do NOT include any explanation, preamble, thinking steps, or chain-of-thought."
            " Only output the final summary or analysis below, starting with the summary for each ticker."
            "\n\n"
            f"{news_prompt}"
        )
    else:
        prompt = (
            "Answer the user's question as an investor-focused summary or analysis. "
            "Do NOT show your reasoning or chain-of-thought, just the answer.\n"
            f"{question}"
        )

    await ctx.send("💬 Thinking with DeepSeek...")

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