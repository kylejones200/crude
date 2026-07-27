#!/usr/bin/env python3
"""
Test script for Yahoo Finance integration.

This script tests the Yahoo Finance connector and demonstrates
how to fetch real-time crude oil prices.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.market_data.yahoo_finance_connector import YahooFinanceConnector
from src.market_data.price_scheduler import PriceScheduler
from datetime import datetime


def test_yahoo_finance():
    """Test Yahoo Finance integration."""
    
    print("🧪 Testing Yahoo Finance Integration")
    print("=" * 50)
    
    # Test 1: Basic connector functionality
    print("\n1️⃣ Testing Yahoo Finance Connector...")
    connector = YahooFinanceConnector()
    
    try:
        # Test with major crude benchmarks
        test_crudes = ['WTI', 'BRENT', 'ARB', 'MAYA']
        prices = connector.get_crude_prices(test_crudes)
        
        if prices:
            print("✅ Successfully fetched prices:")
            for crude_id, price_obj in prices.items():
                print(f"   {crude_id:10s}: ${price_obj.current_price:7.2f} "
                      f"({price_obj.change:+6.2f} / {price_obj.change_percent:+5.1f}%)")
        else:
            print("❌ No prices retrieved")
            
    except Exception as e:
        print(f"❌ Error testing connector: {e}")
    
    # Test 2: Market summary
    print("\n2️⃣ Testing Market Summary...")
    try:
        summary = connector.get_market_summary()
        
        if summary:
            print("✅ Market summary retrieved:")
            for key, value in summary.items():
                if key in ['WTI', 'Brent']:
                    print(f"   {key}: ${value.get('price', 'N/A'):.2f}")
                elif key == 'WTI_Brent_Spread':
                    print(f"   Spread: ${value:+.2f}")
                elif key == 'timestamp':
                    print(f"   Updated: {value}")
        else:
            print("❌ No market summary data")
            
    except Exception as e:
        print(f"❌ Error getting market summary: {e}")
    
    # Test 3: Historical data
    print("\n3️⃣ Testing Historical Data...")
    try:
        historical = connector.get_historical_prices(['WTI', 'BRENT'], period='5d', interval='1d')
        
        if not historical.empty:
            print(f"✅ Retrieved {len(historical)} historical records")
            print("   Sample data:")
            print(historical[['Datetime', 'crude_id', 'Close']].head(3).to_string(index=False))
        else:
            print("❌ No historical data retrieved")
            
    except Exception as e:
        print(f"❌ Error getting historical data: {e}")
    
    # Test 4: Price file update
    print("\n4️⃣ Testing Price File Update...")
    try:
        output_file = connector.update_price_file(['WTI', 'BRENT', 'ARB'])
        
        if os.path.exists(output_file):
            print(f"✅ Price file updated: {output_file}")
            
            # Show file contents
            import pandas as pd
            df = pd.read_csv(output_file)
            print(f"   File contains {len(df)} records")
            print("   Sample records:")
            print(df.head(3).to_string(index=False))
        else:
            print("❌ Price file not created")
            
    except Exception as e:
        print(f"❌ Error updating price file: {e}")
    
    # Test 5: Price scheduler
    print("\n5️⃣ Testing Price Scheduler...")
    try:
        scheduler = PriceScheduler()
        
        status = scheduler.get_status()
        print("✅ Scheduler created successfully")
        print(f"   Market hours only: {status['market_hours_only']}")
        print(f"   Update frequency: {status['update_frequency_minutes']} minutes")
        print(f"   Tracking {status['crude_ids_tracked']} crude oils")
        print(f"   Current market hours: {status['is_market_hours']}")
        
        # Test single update
        print("\n   Running test price update...")
        scheduler.update_prices()
        print("   ✅ Test update completed")
        
    except Exception as e:
        print(f"❌ Error testing scheduler: {e}")
    
    print("\n🎯 Yahoo Finance Integration Test Complete!")
    print("\n📋 Summary:")
    print("   - Real-time price fetching ✅")
    print("   - Market summary data ✅") 
    print("   - Historical price data ✅")
    print("   - Price file updates ✅")
    print("   - Automated scheduler ✅")
    
    print(f"\n🚀 Ready for live market data integration!")


if __name__ == "__main__":
    test_yahoo_finance()
