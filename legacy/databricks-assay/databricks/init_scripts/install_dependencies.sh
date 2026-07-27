#!/bin/bash

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
