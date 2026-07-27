# Databricks Data Upload Commands
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
