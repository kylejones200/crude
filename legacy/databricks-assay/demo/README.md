# 🛢️ Crude Assay Regression Demo

An interactive machine learning demonstration for predicting crude oil properties and valuations based on assay characteristics.

![Regression Demo](../075D0F49-67FB-4407-AF59-B7A9D4262090.jpg.png)

## Overview

This demo showcases advanced regression modeling for crude oil analysis, providing real-time predictions of:

- **Gross Value**: Revenue potential per barrel based on product yields
- **Netback Value**: Value after transportation costs  
- **Quality Score**: Overall crude quality rating (0-10 scale)
- **Processing Index**: Refinery processing complexity score (0-100 scale)

## Features

### 🎛️ Interactive Controls
- **API Gravity**: Adjust crude density (15-45°API)
- **Sulfur Content**: Control sweetness/sourness (0.1-5.0 wt%)
- **Distillation Cuts**: Set light/middle/heavy fraction yields

### 📊 Real-time Visualizations
- API gravity vs gross value scatter plot with regression line
- Sulfur content vs quality score relationship
- Dynamic distillation cut pie chart
- Live prediction updates as you adjust parameters

### 🧠 Machine Learning Models
- **Linear Regression**: Baseline predictions
- **Polynomial Features**: Captures non-linear relationships  
- **Random Forest**: Complex feature interactions
- **Ridge Regression**: Regularized predictions

### 📋 Sample Data
Pre-loaded crude oil samples:
- **Arab Light**: Medium sweet Saudi crude
- **West African Blend**: Light sweet crude
- **Mars**: Medium sour US Gulf crude  
- **WTI**: Light sweet benchmark crude
- **Maya Heavy**: Heavy sour Mexican crude

## Quick Start

### Option 1: Standalone Demo (Recommended)
```bash
# From the project root directory
python run_regression_demo.py

# The demo will open automatically in your browser at:
# http://localhost:5000
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Train models (first time only)
python -c "from src.regression_models import *; main()"

# Start the API server
python src/regression_api.py

# Open demo/crude_assay_regression_demo.html in your browser
```

## Usage Guide

### 1. Basic Interaction
1. **Adjust Parameters**: Use the sliders to modify crude properties
2. **View Predictions**: Watch real-time updates in the prediction cards
3. **Analyze Charts**: Observe how your inputs relate to historical data
4. **Load Samples**: Click sample crude buttons to explore known crude types

### 2. Understanding the Predictions

#### Gross Value ($/bbl)
- Calculated from: `light_cuts × light_price + middle_cuts × middle_price + heavy_cuts × heavy_price`
- Typical range: $75-$90/bbl
- Higher API gravity and better cut distribution = higher value

#### Netback Value ($/bbl)  
- Gross value minus transportation costs
- Accounts for geographic freight differentials
- Real metric used by traders and refiners

#### Quality Score (0-10)
- Composite metric of crude desirability
- Factors: API gravity (higher is better) + sulfur content (lower is better)
- Benchmark: WTI ≈ 9.5, Maya Heavy ≈ 3.2

#### Processing Index (0-100)
- Refinery processing complexity requirement
- Higher index = more complex/expensive processing
- Considers API, sulfur, and yield distribution

### 3. Advanced Features

#### API Endpoints
The demo includes a REST API for programmatic access:

```bash
# Get predictions
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "api_gravity": 33.0,
    "sulfur_content": 1.8, 
    "light_cuts": 0.35,
    "middle_cuts": 0.45,
    "heavy_cuts": 0.20
  }'

# Batch predictions
curl -X POST http://localhost:5000/api/batch_predict \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [
      {"name": "Crude A", "api_gravity": 35.0, ...},
      {"name": "Crude B", "api_gravity": 28.0, ...}
    ]
  }'

# Model information
curl http://localhost:5000/api/model_info

# Sample crude data
curl http://localhost:5000/api/sample_crudes
```

## Technical Details

### Model Architecture
The regression system uses ensemble modeling:

1. **Data Generation**: 1500+ synthetic but realistic crude samples
2. **Feature Engineering**: Polynomial features for non-linear relationships
3. **Model Selection**: Best performing algorithm per target variable
4. **Cross-Validation**: 5-fold CV for robust performance estimation

### Model Performance
Typical R² scores achieved:
- Gross Value: 0.95+ (strong linear relationship)  
- Quality Score: 0.88+ (API-sulfur correlation)
- Processing Index: 0.82+ (complex multi-factor)
- Netback Value: 0.89+ (freight variations)

### Data Pipeline
```
Raw Assay Properties → Feature Scaling → Polynomial Features → 
Model Prediction → Post-processing → JSON Response
```

## Customization

### Adding New Models
```python
# In regression_models.py, modify models_to_train dict:
models_to_train = {
    'linear': LinearRegression(),
    'ridge': Ridge(alpha=1.0), 
    'lasso': Lasso(alpha=0.1),     # Add Lasso
    'svr': SVR(kernel='rbf'),      # Add Support Vector Regression
    'gradient_boosting': GradientBoostingRegressor()  # Add GBM
}
```

### Updating Price Assumptions
```python
# Modify product prices in regression_models.py:
self.product_prices = {
    'lights': 95.0,   # Update gasoline price
    'middles': 87.0,  # Update diesel price  
    'heavies': 78.0   # Update fuel oil price
}
```

### Custom Crude Samples
Add new samples to the HTML file:
```javascript
const customCrudes = {
    'my-crude': {
        name: 'My Custom Crude',
        api: 31.5,
        sulfur: 2.2,
        light: 0.32,
        middle: 0.48, 
        heavy: 0.20,
        description: 'Custom crude description'
    }
};
```

## File Structure
```
demo/
├── README.md                           # This file
├── crude_assay_regression_demo.html    # Main web interface
└── screenshots/                        # Demo screenshots

src/
├── regression_models.py                # ML models and training
├── regression_api.py                   # Flask REST API
└── valuation_engine.py                 # Original valuation logic

models/
├── crude_regression_models.pkl         # Trained models (auto-generated)
└── model_summary.json                  # Model performance metrics

run_regression_demo.py                  # Demo launcher script
requirements.txt                        # Updated dependencies
```

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Use different port
python run_regression_demo.py --port 5001
```

#### Missing Dependencies
```bash
# Reinstall requirements
pip install -r requirements.txt
```

#### Model Training Fails
```bash
# Force model retraining
python run_regression_demo.py --train-models
```

#### Browser Doesn't Open
```bash
# Start without browser, then manually open
python run_regression_demo.py --no-browser
# Then navigate to http://localhost:5000
```

## Integration with Databricks

This demo can be extended to work with your Databricks environment:

1. **Replace synthetic data** with real assay data from your Delta tables
2. **Update the DLT pipeline** to include regression model predictions
3. **Deploy as Databricks web app** using the provided Flask API
4. **Schedule model retraining** using Databricks Jobs

## Next Steps

- **Live Data Integration**: Connect to real crude price feeds
- **Advanced Models**: Add deep learning for complex relationships  
- **Batch Processing**: Handle multiple crude evaluations
- **Historical Analysis**: Time series analysis of crude values
- **Optimization**: Integrate with blend optimization models

## Support

For questions or issues:
1. Check the logs: `regression_demo.log`
2. Verify model training completed successfully  
3. Ensure all dependencies are installed
4. Test API endpoints individually

---

*This demo showcases the power of machine learning in crude oil trading and refining operations. The models and predictions are for demonstration purposes and should be validated with real market data before commercial use.*
