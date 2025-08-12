#!/usr/bin/env python3
"""
Test script to verify VertBot startup and scheduler initialization.
This script tests the core components without actually connecting to Discord.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.main import scheduler, market_monitor, send_daily_report, monitor_price_changes
from bot.utils.logger import get_logger

logger = get_logger(__name__)

async def test_scheduler():
    """Test the scheduler functionality."""
    print("🧪 Testing scheduler functionality...")
    
    try:
        # Test scheduler initialization
        if not scheduler.running:
            print("📅 Starting scheduler...")
            scheduler.start()
        
        # Add a test job
        scheduler.add_job(
            lambda: print("✅ Test job executed successfully!"),
            'interval',
            seconds=5,
            id='test_job',
            replace_existing=True
        )
        
        print(f"📋 Scheduler running: {scheduler.running}")
        print(f"📋 Jobs scheduled: {len(scheduler.get_jobs())}")
        
        # Wait for test job to execute
        print("⏳ Waiting for test job to execute...")
        await asyncio.sleep(6)
        
        # Clean up test job
        scheduler.remove_job('test_job')
        print("🧹 Test job cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Scheduler test failed: {e}")
        return False

async def test_market_monitor():
    """Test the market monitor functionality."""
    print("\n🧪 Testing market monitor functionality...")
    
    try:
        # Test basic functionality
        print(f"📊 Price monitoring active: {market_monitor.is_price_monitoring_active()}")
        print(f"📈 Daily report active: {market_monitor.is_daily_report_active()}")
        
        # Test time tracking
        market_monitor.update_price_check_time()
        market_monitor.update_daily_report_time()
        
        print(f"📊 Price monitoring active (after update): {market_monitor.is_price_monitoring_active()}")
        print(f"📈 Daily report active (after update): {market_monitor.is_daily_report_active()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Market monitor test failed: {e}")
        return False

async def test_task_creation():
    """Test creating background tasks."""
    print("\n🧪 Testing task creation...")
    
    try:
        # Test creating a simple task
        async def test_task():
            print("✅ Test task executed successfully!")
            await asyncio.sleep(1)
        
        task = asyncio.create_task(test_task())
        await task
        
        print("✅ Task creation test passed")
        return True
        
    except Exception as e:
        print(f"❌ Task creation test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting VertBot startup tests...\n")
    
    tests = [
        ("Scheduler", test_scheduler),
        ("Market Monitor", test_market_monitor),
        ("Task Creation", test_task_creation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print results
    print("\n📊 Test Results:")
    print("=" * 40)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if not result:
            all_passed = False
    
    print("=" * 40)
    
    if all_passed:
        print("🎉 All tests passed! Bot should start up properly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
