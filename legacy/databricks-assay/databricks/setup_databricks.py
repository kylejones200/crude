"""
Databricks Setup and Configuration Script

This script prepares the crude assay analytics platform for Databricks deployment,
including data upload, library installation, and configuration setup.
"""

import os
import json
from pathlib import Path
import shutil


def create_databricks_structure():
    """Create the recommended Databricks project structure."""
    
    # Create Databricks-specific directories
    databricks_dirs = [
        'databricks/notebooks',
        'databricks/dashboards', 
        'databricks/workflows',
        'databricks/init_scripts',
        'databricks/libraries',
        'databricks/configs'
    ]
    
    for dir_path in databricks_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")


def create_databricks_notebook_config():
    """Create databricks notebook configuration."""
    
    notebook_config = {
        "name": "crude_assay_analytics",
        "language": "python",
        "cluster_settings": {
            "spark_version": "13.3.x-scala2.12",
            "node_type_id": "i3.xlarge",
            "driver_node_type_id": "i3.xlarge",
            "num_workers": 2,
            "auto_termination_minutes": 60,
            "spark_conf": {
                "spark.databricks.delta.preview.enabled": "true",
                "spark.sql.adaptive.enabled": "true",
                "spark.sql.adaptive.coalescePartitions.enabled": "true"
            },
            "custom_tags": {
                "project": "crude-assay-analytics",
                "environment": "development"
            }
        },
        "libraries": [
            {"pypi": {"package": "yfinance>=0.2.18"}},
            {"pypi": {"package": "schedule>=1.2.0"}},
            {"pypi": {"package": "streamlit>=1.32.0"}},
            {"pypi": {"package": "pyomo>=6.7.1"}},
            {"pypi": {"package": "highspy>=1.6.0"}}
        ],
        "init_scripts": [
            {"dbfs": {"destination": "dbfs:/databricks/init_scripts/install_dependencies.sh"}}
        ]
    }
    
    with open('databricks/configs/notebook_config.json', 'w') as f:
        json.dump(notebook_config, f, indent=2)
    
    print("✅ Created Databricks notebook configuration")


def create_dlt_pipeline_config():
    """Create Delta Live Tables pipeline configuration for Databricks."""
    
    dlt_config = {
        "id": "crude-assay-analytics-pipeline",
        "name": "Crude Assay Analytics DLT Pipeline",
        "storage": "dbfs:/mnt/delta/crude_assay_analytics",
        "configuration": {
            "assay.data.base_path": "dbfs:/FileStore/crude_assay_data"
        },
        "clusters": [
            {
                "label": "default",
                "num_workers": 1,
                "spark_conf": {
                    "spark.databricks.cluster.profile": "singleNode",
                    "spark.master": "local[*]"
                },
                "custom_tags": {
                    "ResourceClass": "SingleNode",
                    "project": "crude-assay-analytics"
                }
            }
        ],
        "libraries": [
            {"notebook": {"path": "/Repos/crude_assay_analytics/dlt/assay_dlt"}},
            {"pypi": {"package": "yfinance>=0.2.18"}},
            {"pypi": {"package": "scikit-learn>=1.3.0"}}
        ],
        "target": "crude_assay_development",
        "continuous": False,
        "development": True
    }
    
    with open('databricks/configs/dlt_pipeline.json', 'w') as f:
        json.dump(dlt_config, f, indent=2)
    
    print("✅ Created DLT pipeline configuration")


def create_init_script():
    """Create initialization script for Databricks cluster."""
    
    init_script = '''#!/bin/bash

# Databricks Crude Assay Analytics Initialization Script
echo "Starting Databricks cluster initialization for Crude Assay Analytics..."

# Install system dependencies
apt-get update
apt-get install -y curl wget

# Install additional Python packages
/databricks/python/bin/pip install --upgrade pip
/databricks/python/bin/pip install yfinance>=0.2.18
/databricks/python/bin/pip install schedule>=1.2.0
/databricks/python/bin/pip install streamlit>=1.32.0
/databricks/python/bin/pip install pyomo>=6.7.1
/databricks/python/bin/pip install highspy>=1.6.0

# Set environment variables
export CRUDE_ASSAY_HOME="/Workspace/Repos/crude_assay_analytics"
export PYTHONPATH="${PYTHONPATH}:${CRUDE_ASSAY_HOME}"

# Create necessary directories
mkdir -p /tmp/crude_assay_cache
mkdir -p /tmp/market_data

echo "Databricks initialization complete!"
'''
    
    with open('databricks/init_scripts/install_dependencies.sh', 'w') as f:
        f.write(init_script)
    
    print("✅ Created Databricks initialization script")


def create_data_upload_script():
    """Create script to upload sample data to DBFS."""
    
    upload_script = '''# Databricks Data Upload Commands
# Run these commands in a Databricks notebook cell

# Create directories in DBFS
%fs mkdirs dbfs:/FileStore/crude_assay_data/

# Upload sample data files
# Note: You'll need to upload these files through the Databricks UI or CLI

# Expected file structure in DBFS:
# dbfs:/FileStore/crude_assay_data/
#   ├── assays.csv
#   ├── blend_supply.csv  
#   ├── freight_routes.csv
#   ├── prices.csv
#   ├── crude_regions.csv
#   ├── seasonal_prices.csv
#   ├── quality_premiums.csv
#   ├── pi_system_data.csv
#   ├── intertek_lab_reports.csv
#   ├── bliss_blend_recipes.csv
#   ├── lims_quality_tests.csv
#   ├── aspentech_planning.csv
#   └── haverly_optimization.csv

# Verify uploads
%fs ls dbfs:/FileStore/crude_assay_data/

# Create Delta Lake storage location
%fs mkdirs dbfs:/mnt/delta/crude_assay_analytics/

print("Data upload locations prepared!")
'''
    
    with open('databricks/workflows/upload_data.py', 'w') as f:
        f.write(upload_script)
    
    print("✅ Created data upload script")


def create_deployment_guide():
    """Create Databricks deployment guide."""
    
    deployment_guide = '''# 🚀 Databricks Deployment Guide

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
'''
    
    with open('databricks/DEPLOYMENT_GUIDE.md', 'w') as f:
        f.write(deployment_guide)
    
    print("✅ Created Databricks deployment guide")


def main():
    """Main setup function."""
    print("🔧 Setting up Databricks configuration...")
    
    create_databricks_structure()
    create_databricks_notebook_config()
    create_dlt_pipeline_config()
    create_init_script()
    create_data_upload_script()
    create_deployment_guide()
    
    print("\n🎯 Databricks setup complete!")
    print("\nNext steps:")
    print("1. Upload project to Databricks workspace")
    print("2. Follow databricks/DEPLOYMENT_GUIDE.md")
    print("3. Create cluster with provided configuration")
    print("4. Upload sample data to DBFS")
    print("5. Run DLT pipeline")
    print("6. Launch Streamlit dashboard")


if __name__ == "__main__":
    main()
