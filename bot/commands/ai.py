from discord.ext import commands
from ai.deepseek_llm import query_deepseek
from api.news_data import fetch_news  # Adjust path as needed
import re

def extract_tickers_from_message(msg):
    # This regex finds words that look like tickers (2-5 alphanum, not all numbers)
    # Allows tickers like "BRK.A" (Berkshire) or "GOOG", etc.
    pattern = r'\b[a-zA-Z]{1,5}\d{0,3}(?:\.[A-Za-z])?\b'
    tickers = re.findall(pattern, msg, flags=re.IGNORECASE)
    # Remove duplicates, and ignore pure numbers or single-letter matches (optional)
    unique_tickers = []
    for t in tickers:
        if t.isdigit() or len(t) < 2:
            continue
        t = t.upper()
        if t not in unique_tickers:
            unique_tickers.append(t)
    return unique_tickers

@commands.command(name="askai")
async def ask_ai(ctx, *, question: str):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    tickers = extract_tickers_from_message(question)
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
            f"Based on the following real news headlines, give an investor-friendly summary and analysis for these stocks:\n"
            f"{news_prompt}"
        )
    else:
        prompt = question  # Fallback: just use the user's question
    
    await ctx.send("💬 Thinking with DeepSeek...")

    try:
        response = query_deepseek(prompt)
        if response:
            if len(response) > 1990:
                response = response[:1990] + "…"
            await ctx.send(response)
        else:
            await ctx.send("🤔 I didn't get a response from DeepSeek.")
    except Exception as e:
        await ctx.send(f"❌ LLM error: {e}")