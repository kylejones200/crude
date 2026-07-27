# 🚀 Databricks Deployment Guide

## Prerequisites
- Databricks workspace access
- Unity Catalog enabled (recommended)
- Appropriate permissions for cluster creation and data access

## 1. Upload Project to Databricks

### Option A: Git Integration (Recommended)
1. Go to Databricks workspace → Repos
2. Click "Add Repo"
3. Enter your Git repository URL
4. Clone the repository

### Option B: Manual Upload
1. Zip the entire project
2. Upload via Databricks workspace
3. Extract to `/Workspace/Users/{your-email}/crude_assay_analytics`

## 2. Upload Sample Data

### Using Databricks UI:
1. Go to Data → DBFS File Browser
2. Create folder: `/FileStore/crude_assay_data/`
3. Upload all CSV files from `resources/sample_data/`

### Using Databricks CLI:
```bash
databricks fs cp resources/sample_data/ dbfs:/FileStore/crude_assay_data/ --recursive
```

## 3. Create Databricks Cluster

### Cluster Configuration:
- **Runtime**: 13.3 LTS (includes Apache Spark 3.4.1, Scala 2.12)
- **Worker Type**: i3.xlarge (or similar)
- **Workers**: 2-4 (depending on data size)
- **Auto Termination**: 60 minutes

### Libraries to Install:
```json
{
  "pypi": {
    "package": "yfinance>=0.2.18"
  }
}
```

## 4. Setup Delta Live Tables Pipeline

1. Go to Workflows → Delta Live Tables
2. Click "Create Pipeline"
3. Configure:
   - **Name**: Crude Assay Analytics Pipeline
   - **Source Code**: `/Repos/{path}/dlt/assay_dlt.py`
   - **Storage Location**: `dbfs:/mnt/delta/crude_assay_analytics`
   - **Target Schema**: `crude_assay_development`

## 5. Run Initial Pipeline

1. Start the DLT pipeline
2. Verify tables are created:
   - Bronze: `bronze_assays`, `bronze_prices`, `bronze_freight`
   - Silver: `silver_assays`, `silver_prices`, `silver_freight` 
   - Gold: `gold_crude_analytics`, `gold_crude_predictions`

## 6. Setup Streamlit Dashboard

1. Navigate to the Streamlit app: `streamlit/crude_assay_dashboard.py`
2. Run in Databricks notebook:
   ```python
   import subprocess
   subprocess.run(["streamlit", "run", "streamlit/crude_assay_dashboard.py", "--server.port", "8501"])
   ```

## 7. Configure Market Data (Optional)

1. Test Yahoo Finance integration:
   ```python
   %run src/market_data/yahoo_finance_connector.py
   ```

2. Start price scheduler:
   ```python
   from src.market_data.price_scheduler import PriceScheduler
   scheduler = PriceScheduler()
   scheduler.start_scheduler()
   ```

## 8. Create Databricks SQL Dashboards

1. Use pre-built SQL views in `sql/dashboard_views.sql`
2. Create visualizations in Databricks SQL
3. Build interactive dashboards

## Verification Steps

### Test Data Pipeline:
```sql
-- Verify bronze tables
SELECT COUNT(*) FROM bronze_assays;
SELECT COUNT(*) FROM bronze_prices;

-- Check gold analytics
SELECT * FROM gold_crude_analytics LIMIT 5;
```

### Test Regression Models:
```python
# Run regression analysis notebook
%run notebooks/05_regression_analysis
```

### Test Optimization:
```python  
# Run optimization notebook
%run notebooks/06_enhanced_optimization
```

## Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure all libraries are installed on cluster
2. **Data Not Found**: Verify DBFS file paths
3. **Permission Denied**: Check workspace and data access permissions
4. **Memory Issues**: Increase cluster size or optimize data partitioning

### Support Resources:
- Databricks Documentation: docs.databricks.com
- Project Repository: [Your Git Repo URL]
- Support Contact: [Your Contact Info]
