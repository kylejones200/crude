# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 📈 Daily Market Data Update Workflow
# MAGIC 
# MAGIC This notebook runs daily to:
# MAGIC - Update crude oil prices from Yahoo Finance
# MAGIC - Refresh market data tables
# MAGIC - Update regression models with new market conditions
# MAGIC - Generate market alerts for significant price changes

# COMMAND ----------
# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------
# Install required packages
%pip install yfinance>=0.2.18 schedule>=1.2.0

# COMMAND ----------
dbutils.library.restartPython()

# COMMAND ----------
# Import libraries
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from pyspark.sql import functions as F

# Add project path
sys.path.append("/Workspace/Repos/crude_assay_analytics/src")

try:
    from market_data.yahoo_finance_connector import YahooFinanceConnector
    from market_data.price_scheduler import PriceScheduler
    MARKET_DATA_AVAILABLE = True
    print("✅ Market data modules loaded successfully")
except Exception as e:
    print(f"⚠️ Market data modules not available: {e}")
    MARKET_DATA_AVAILABLE = False

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1️⃣ Update Market Prices

# COMMAND ----------
if MARKET_DATA_AVAILABLE:
    # Initialize Yahoo Finance connector
    connector = YahooFinanceConnector()
    
    # Define crude oils to track
    tracked_crudes = [
        'WTI', 'BRENT', 'ARB', 'MAYA', 'URALS', 'SAHARA', 
        'CANADIAN_HEAVY', 'NIGERIAN_LIGHT', 'RUSSIAN_EXPORT',
        'DUBAI', 'KUWAIT', 'IRANIAN_LIGHT', 'NORTH_SEA_EKOFISK'
    ]
    
    print(f"🔄 Fetching prices for {len(tracked_crudes)} crude oils...")
    
    try:
        # Get current prices
        prices = connector.get_crude_prices(tracked_crudes)
        
        if prices:
            print(f"✅ Successfully fetched {len(prices)} crude oil prices")
            
            # Convert to DataFrame
            price_data = []
            for crude_id, price_obj in prices.items():
                price_data.append({
                    'crude_id': crude_id,
                    'current_price': price_obj.current_price,
                    'change': price_obj.change,
                    'change_percent': price_obj.change_percent,
                    'volume': price_obj.volume,
                    'day_high': price_obj.day_high,
                    'day_low': price_obj.day_low,
                    'market_status': price_obj.market_status,
                    'update_timestamp': price_obj.timestamp,
                    'ticker': price_obj.ticker
                })
            
            # Create Spark DataFrame
            prices_df = spark.createDataFrame(price_data)
            
            # Save to Delta table
            (prices_df.write
             .format("delta")
             .mode("overwrite")
             .option("overwriteSchema", "true")
             .saveAsTable("crude_assay_development.live_crude_prices"))
            
            print("✅ Saved live prices to Delta table: crude_assay_development.live_crude_prices")
            
            # Show sample of updated prices
            print("\n📊 Sample of current prices:")
            prices_df.select("crude_id", "current_price", "change_percent", "market_status").show(10)
            
        else:
            print("❌ No prices retrieved from Yahoo Finance")
            
    except Exception as e:
        print(f"❌ Error fetching prices: {e}")
else:
    print("⚠️ Skipping market data update - modules not available")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2️⃣ Generate Market Alerts

# COMMAND ----------
if MARKET_DATA_AVAILABLE and 'prices_df' in locals():
    # Check for significant price movements
    significant_changes = prices_df.filter(F.abs(F.col("change_percent")) >= 2.0)
    
    if significant_changes.count() > 0:
        print("🚨 SIGNIFICANT PRICE MOVEMENTS (>2%)")
        print("=" * 50)
        
        changes = significant_changes.collect()
        for row in changes:
            direction = "📈" if row.change_percent > 0 else "📉"
            print(f"{direction} {row.crude_id}: {row.change_percent:+.1f}% to ${row.current_price:.2f}")
        
        # Save alerts to table
        (significant_changes.select(
            "crude_id", "current_price", "change", "change_percent", "update_timestamp"
        ).withColumn("alert_type", F.lit("PRICE_MOVEMENT"))
         .withColumn("alert_threshold", F.lit(2.0))
         .write.format("delta").mode("append").saveAsTable("crude_assay_development.market_alerts"))
        
        print(f"\n✅ Saved {significant_changes.count()} alerts to market_alerts table")
    else:
        print("📊 No significant price movements today (threshold: 2%)")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3️⃣ Update Historical Data

# COMMAND ----------
if MARKET_DATA_AVAILABLE:
    try:
        # Get 30 days of historical data
        print("📈 Updating historical price data...")
        
        historical_df = connector.get_historical_prices(
            crude_ids=tracked_crudes,
            period='30d',
            interval='1d'
        )
        
        if not historical_df.empty:
            # Convert to Spark DataFrame
            historical_spark_df = spark.createDataFrame(historical_df)
            
            # Save historical data
            (historical_spark_df.write
             .format("delta")
             .mode("overwrite")
             .option("overwriteSchema", "true")
             .saveAsTable("crude_assay_development.historical_crude_prices"))
            
            print(f"✅ Updated historical data: {len(historical_df)} records")
            print(f"   Date range: {historical_df['Datetime'].min()} to {historical_df['Datetime'].max()}")
            
        else:
            print("⚠️ No historical data available")
            
    except Exception as e:
        print(f"❌ Error updating historical data: {e}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4️⃣ Update Market Summary

# COMMAND ----------
if MARKET_DATA_AVAILABLE:
    try:
        # Get market summary
        market_summary = connector.get_market_summary()
        
        if market_summary:
            print("📊 Market Summary:")
            
            if 'WTI' in market_summary:
                wti = market_summary['WTI']
                print(f"   WTI: ${wti['price']:.2f} ({wti['change']:+.2f})")
            
            if 'Brent' in market_summary:
                brent = market_summary['Brent']
                print(f"   Brent: ${brent['price']:.2f} ({brent['change']:+.2f})")
            
            if 'WTI_Brent_Spread' in market_summary:
                spread = market_summary['WTI_Brent_Spread']
                print(f"   WTI-Brent Spread: ${spread:+.2f}")
            
            # Save market summary as JSON
            dbutils.fs.put(
                "dbfs:/FileStore/market_data/market_summary.json",
                json.dumps(market_summary, default=str),
                overwrite=True
            )
            
            print("✅ Market summary saved to DBFS")
            
    except Exception as e:
        print(f"❌ Error updating market summary: {e}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5️⃣ Workflow Summary

# COMMAND ----------
# Generate workflow summary
workflow_summary = {
    'workflow_name': 'daily_market_update',
    'execution_time': datetime.now(),
    'status': 'completed',
    'market_data_available': MARKET_DATA_AVAILABLE
}

if MARKET_DATA_AVAILABLE and 'prices_df' in locals():
    workflow_summary.update({
        'prices_updated': prices_df.count(),
        'significant_changes': significant_changes.count(),
        'historical_records': len(historical_df) if 'historical_df' in locals() and not historical_df.empty else 0
    })

print("📋 WORKFLOW SUMMARY")
print("=" * 30)
for key, value in workflow_summary.items():
    print(f"{key}: {value}")

# Save workflow log
workflow_log_df = spark.createDataFrame([workflow_summary])
(workflow_log_df.write
 .format("delta")
 .mode("append")
 .saveAsTable("crude_assay_development.workflow_logs"))

print("\n✅ Workflow completed successfully!")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6️⃣ Trigger Downstream Updates

# COMMAND ----------
# Optionally trigger DLT pipeline refresh
try:
    # Note: In production, you might trigger DLT pipeline via REST API
    print("🔄 Consider refreshing DLT pipeline to incorporate new market data")
    print("   Pipeline: crude-assay-analytics-pipeline")
    print("   Tables to refresh: gold_market_data, gold_crude_analytics")
    
    # Refresh specific tables if needed
    spark.sql("REFRESH TABLE crude_assay_development.live_crude_prices")
    print("✅ Refreshed live_crude_prices table")
    
except Exception as e:
    print(f"⚠️ Error refreshing tables: {e}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Next Steps
# MAGIC 
# MAGIC 1. **Schedule this notebook** to run daily using Databricks Jobs
# MAGIC 2. **Set up alerts** for significant price movements via email/Slack
# MAGIC 3. **Monitor data quality** and API rate limits
# MAGIC 4. **Update downstream dashboards** with fresh market data
# MAGIC 
# MAGIC ### Scheduling Options:
# MAGIC - **Databricks Jobs**: Create a scheduled job for this notebook
# MAGIC - **Workflow**: Include in broader ETL workflow
# MAGIC - **Triggers**: Set up event-driven execution based on market hours
