#!/usr/bin/env python3
"""
Test script to verify the daily report functionality
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.commands.report import load_channels
from bot.commands.tickers import get_guild_tickers
from api.market_data import fetch_closing_price
import pytz
import datetime

async def test_daily_report():
    """Test the daily report functionality"""
    print("Testing daily report functionality...")
    
    # Test loading channels
    print("\n1. Testing channel loading...")
    channels = load_channels()
    print(f"Loaded channels: {channels}")
    
    if not channels:
        print("❌ No channels configured!")
        return False
    
    # Test loading tickers for each guild
    print("\n2. Testing ticker loading...")
    for guild_id, channel_id in channels.items():
        print(f"Testing guild {guild_id}...")
        tickers = get_guild_tickers(int(guild_id))
        print(f"  Tickers: {tickers}")
        
        if not tickers:
            print(f"  ❌ No tickers configured for guild {guild_id}")
            continue
        
        # Test fetching closing prices
        print(f"  Testing price fetching for {len(tickers)} tickers...")
        for symbol in tickers[:3]:  # Test first 3 tickers
            try:
                price, date = fetch_closing_price(symbol)
                print(f"    ✅ {symbol}: ${price:.2f} ({date})")
            except Exception as e:
                print(f"    ❌ {symbol}: Error - {e}")
    
    # Test timezone handling
    print("\n3. Testing timezone handling...")
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    print(f"Current time (Eastern): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Day of week: {now.strftime('%A')} (weekday: {now.weekday()})")
    print(f"Is weekday: {now.weekday() < 5}")
    print(f"Is 4 PM: {now.hour == 16 and now.minute == 0}")
    
    print("\n✅ Daily report test completed!")
    return True

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(test_daily_report()) 