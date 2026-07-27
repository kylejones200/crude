# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 🚀 Databricks Setup for Crude Assay Analytics
# MAGIC 
# MAGIC This notebook sets up the Databricks environment for crude assay analytics including:
# MAGIC - Data upload to DBFS
# MAGIC - Library installation
# MAGIC - Configuration verification
# MAGIC - Initial data validation

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1️⃣ Environment Setup

# COMMAND ----------
# Install required packages
%pip install yfinance>=0.2.18 schedule>=1.2.0 streamlit>=1.32.0 pyomo>=6.7.1 highspy>=1.6.0

# COMMAND ----------
# Restart Python kernel to load new packages
dbutils.library.restartPython()

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2️⃣ Create DBFS Directories

# COMMAND ----------
# Create necessary directories in DBFS
dbutils.fs.mkdirs("dbfs:/FileStore/crude_assay_data/")
dbutils.fs.mkdirs("dbfs:/mnt/delta/crude_assay_analytics/")
dbutils.fs.mkdirs("dbfs:/FileStore/market_data/")

print("✅ Created DBFS directories:")
print("  - dbfs:/FileStore/crude_assay_data/ (for sample data)")
print("  - dbfs:/mnt/delta/crude_assay_analytics/ (for Delta tables)")
print("  - dbfs:/FileStore/market_data/ (for live market data)")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3️⃣ Upload Sample Data
# MAGIC 
# MAGIC **Note**: You'll need to upload the CSV files from `resources/sample_data/` to DBFS.
# MAGIC 
# MAGIC ### Expected Files:
# MAGIC - assays.csv (53 crude oils with properties)
# MAGIC - blend_supply.csv (cost and availability data)
# MAGIC - freight_routes.csv (transportation costs)
# MAGIC - prices.csv (product prices)
# MAGIC - crude_regions.csv (geographic data)
# MAGIC - seasonal_prices.csv (monthly price variations)
# MAGIC - quality_premiums.csv (quality-based pricing)
# MAGIC - pi_system_data.csv (operational data)
# MAGIC - intertek_lab_reports.csv (lab analysis)
# MAGIC - bliss_blend_recipes.csv (optimization recipes)
# MAGIC - lims_quality_tests.csv (quality control)
# MAGIC - aspentech_planning.csv (planning scenarios)
# MAGIC - haverly_optimization.csv (optimization results)

# COMMAND ----------
# List uploaded files
try:
    files = dbutils.fs.ls("dbfs:/FileStore/crude_assay_data/")
    print("📁 Files in crude_assay_data:")
    for file in files:
        print(f"  - {file.name} ({file.size} bytes)")
except Exception as e:
    print("⚠️ No files found. Please upload sample data files to dbfs:/FileStore/crude_assay_data/")
    print(f"Error: {e}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4️⃣ Validate Sample Data

# COMMAND ----------
# Test reading a sample file
try:
    df = spark.read.option("header", "true").option("inferSchema", "true").csv("dbfs:/FileStore/crude_assay_data/assays.csv")
    print("✅ Successfully read assays.csv")
    print(f"   Rows: {df.count()}")
    print(f"   Columns: {len(df.columns)}")
    print("   Sample data:")
    df.show(5)
except Exception as e:
    print("❌ Error reading assays.csv:")
    print(f"   {e}")
    print("   Please upload the assays.csv file to dbfs:/FileStore/crude_assay_data/")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5️⃣ Test Yahoo Finance Integration

# COMMAND ----------
# Test Yahoo Finance connectivity
try:
    import yfinance as yf
    
    # Test with WTI crude oil futures
    ticker = yf.Ticker("CL=F")
    info = ticker.info
    history = ticker.history(period="1d")
    
    if not history.empty:
        current_price = history['Close'].iloc[-1]
        print("✅ Yahoo Finance integration working!")
        print(f"   WTI Crude Oil: ${current_price:.2f}")
        print(f"   Market State: {info.get('marketState', 'Unknown')}")
    else:
        print("⚠️ Yahoo Finance connected but no price data available")
        
except Exception as e:
    print("❌ Yahoo Finance integration failed:")
    print(f"   {e}")
    print("   This may be due to network restrictions or API limitations")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6️⃣ Configure Spark Settings

# COMMAND ----------
# Configure Spark for optimal performance
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.databricks.delta.preview.enabled", "true")

# Set configuration for crude assay data location
spark.conf.set("assay.data.base_path", "dbfs:/FileStore/crude_assay_data")

print("✅ Spark configuration updated")
print("   - Adaptive Query Execution enabled")
print("   - Delta Lake preview features enabled")
print("   - Assay data path configured")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7️⃣ Create Sample Delta Table

# COMMAND ----------
# Create a sample Delta table to verify Delta Lake functionality
try:
    # Read assays data
    assays_df = spark.read.option("header", "true").option("inferSchema", "true").csv("dbfs:/FileStore/crude_assay_data/assays.csv")
    
    # Write as Delta table
    assays_df.write.format("delta").mode("overwrite").saveAsTable("crude_assay_development.sample_assays")
    
    print("✅ Successfully created Delta table: crude_assay_development.sample_assays")
    print(f"   Records: {assays_df.count()}")
    
    # Test reading from Delta table
    delta_df = spark.table("crude_assay_development.sample_assays")
    print("✅ Successfully read from Delta table")
    delta_df.show(3)
    
except Exception as e:
    print("❌ Delta table creation failed:")
    print(f"   {e}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8️⃣ Environment Summary

# COMMAND ----------
# Display environment summary
import sys
import os

print("🔧 DATABRICKS ENVIRONMENT SUMMARY")
print("=" * 50)

# Python environment
print(f"Python Version: {sys.version}")
print(f"Spark Version: {spark.version}")

# Available packages
try:
    import yfinance
    print(f"yfinance: ✅ {yfinance.__version__}")
except ImportError:
    print("yfinance: ❌ Not installed")

try:
    import schedule
    print(f"schedule: ✅ {schedule.__version__}")
except ImportError:
    print("schedule: ❌ Not installed")

try:
    import streamlit
    print(f"streamlit: ✅ {streamlit.__version__}")
except ImportError:
    print("streamlit: ❌ Not installed")

try:
    import pyomo
    print(f"pyomo: ✅ {pyomo.__version__}")
except ImportError:
    print("pyomo: ❌ Not installed")

# DBFS status
try:
    files = dbutils.fs.ls("dbfs:/FileStore/crude_assay_data/")
    print(f"\nData Files: ✅ {len(files)} files uploaded")
except:
    print("\nData Files: ❌ No files found")

# Delta Lake status
try:
    tables = spark.sql("SHOW TABLES IN crude_assay_development").collect()
    print(f"Delta Tables: ✅ {len(tables)} tables available")
except:
    print("Delta Tables: ❌ No tables found")

print("\n🎯 Setup Status:")
if len(files) > 5:
    print("   Ready for DLT Pipeline! ✅")
    print("   Next Steps:")
    print("   1. Run DLT Pipeline: dlt/assay_dlt.py")
    print("   2. Execute Notebooks: notebooks/")
    print("   3. Launch Streamlit: streamlit/crude_assay_dashboard.py")
else:
    print("   ⚠️ Please upload sample data files to proceed")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 9️⃣ Next Steps
# MAGIC 
# MAGIC ### If Setup is Complete:
# MAGIC 1. **Run DLT Pipeline**: Go to Workflows → Delta Live Tables and run the crude assay pipeline
# MAGIC 2. **Explore Notebooks**: Run the analysis notebooks in `notebooks/`
# MAGIC 3. **Launch Dashboard**: Execute the Streamlit dashboard
# MAGIC 4. **Setup Market Data**: Configure Yahoo Finance scheduler for live prices
# MAGIC 
# MAGIC ### If Setup Failed:
# MAGIC 1. **Upload Data**: Use Databricks UI to upload CSV files to `dbfs:/FileStore/crude_assay_data/`
# MAGIC 2. **Install Libraries**: Ensure all required packages are installed on the cluster
# MAGIC 3. **Check Permissions**: Verify access to DBFS and Delta Lake
# MAGIC 4. **Network Access**: Confirm Yahoo Finance API accessibility
# MAGIC 
# MAGIC ### Resources:
# MAGIC - **Deployment Guide**: `databricks/DEPLOYMENT_GUIDE.md`
# MAGIC - **API Documentation**: `docs/YAHOO_FINANCE_INTEGRATION.md`
# MAGIC - **Sample Data**: `resources/sample_data/`
