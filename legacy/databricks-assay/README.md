# 🛢️ Advanced Crude Assay Analytics on Databricks

A comprehensive Databricks-native crude assay analytics platform featuring machine learning regression models, advanced optimization, and interactive visualizations. This project integrates traditional crude oil valuation with cutting-edge analytics for enhanced decision-making in crude oil trading and refining operations.

## 🚀 Key Features

### 📊 **Regression Analytics Engine**
- **Quality Score Predictions**: ML-based crude quality assessment (0-10 scale)
- **Processing Complexity Index**: Refinery processing requirements (0-100 scale)  
- **Enhanced Valuations**: Improved pricing models incorporating regression insights
- **Refinery Margin Estimation**: Predictive margin analysis for optimization

### 🔧 **Advanced Optimization**
- **Multi-Strategy Blending**: Traditional cost minimization + enhanced value maximization
- **Quality-Aware Constraints**: API gravity, sulfur content, and regression-based quality scores
- **Processing Complexity Limits**: Optimize based on refinery processing capabilities
- **Comprehensive Sensitivity Analysis**: Constraint impact assessment

### 📈 **Interactive Visualizations**
- **Standalone Regression Demo**: Browser-based interface requiring no setup
- **Real-time Predictions**: Interactive sliders with live regression updates
- **Comprehensive Dashboards**: Quality distributions, processing complexity, value analysis

## 🏗️ Architecture Overview

### Data Pipeline (Delta Live Tables)
```
Raw CSVs → Bronze Tables → Silver Tables → Gold Tables
                                        ↓
                              Regression Predictions
                                        ↓
                              Enhanced Analytics
```

### Component Structure
```
📁 dlt/
├── assay_dlt.py                      # Enhanced DLT pipeline with regression

📁 src/
├── regression_engine_spark.py        # Spark-compatible ML models  
├── regression_models.py              # Advanced scikit-learn models
├── regression_api.py                 # Flask REST API
├── valuation_engine.py              # Traditional valuation logic
├── optimization/
│   ├── blend_pyomo.py                # Original optimization
│   └── enhanced_blend_optimization.py # ML-enhanced optimization

📁 notebooks/
├── 01_explore_valuations.py          # Enhanced with regression analytics
├── 05_regression_analysis.py         # Comprehensive ML analysis  
└── 06_enhanced_optimization.py       # Advanced optimization demos

📁 demo/
├── crude_assay_regression_demo.html   # Full ML-powered interface
├── simple_regression_demo.html        # Standalone browser demo
└── README.md                          # Detailed demo documentation

📁 sql/
└── dashboard_views.sql               # Pre-built dashboard views
```

## 🎯 Gold Tables (Enhanced)

### Traditional Tables
- **Bronze**: `bronze_assays`, `bronze_prices`, `bronze_freight`
- **Silver**: `silver_assays`, `silver_prices`, `silver_freight` 
- **Gold**: `gold_crude_catalog`, `gold_crude_valuations`

### 🧠 **NEW: Regression-Enhanced Tables**
- **`gold_crude_predictions`**: ML predictions (quality scores, processing indices, margins)
- **`gold_crude_rankings`**: Composite rankings based on multiple regression factors
- **`gold_regression_summary`**: Statistical summaries of prediction performance
- **`gold_crude_analytics`**: Comprehensive analytics combining traditional + ML insights

### 📋 **Dashboard Views**
- `crude_portfolio_overview`: Complete portfolio view with regression analytics
- `quality_distribution_analysis`: Quality score distributions and insights
- `sweet_sour_comparison`: Sweetness vs sourness analysis 
- `value_enhancement_analysis`: Traditional vs enhanced valuation comparison
- `optimization_readiness`: Crude suitability for blending optimization

## ⚡ Quick Start Options

### Option 1: Interactive Demo (Immediate Use)
```bash
# No setup required - works in any browser
open demo/simple_regression_demo.html
```

### Option 2: Full ML-Powered Demo
```bash
# Comprehensive machine learning capabilities
python run_regression_demo.py
# Opens at http://localhost:5000
```

### Option 3: Databricks Deployment
1. Upload the repo to your Databricks Workspace (Repos) or sync via Git
2. Create a DLT Pipeline pointing to `dlt/assay_dlt.py` 
3. Configure storage location and catalog/schema (Unity Catalog recommended)
4. Start the pipeline to create all bronze/silver/gold tables with regression analytics
5. Import and run notebooks for analysis and optimization
6. Use SQL dashboard views for reporting and visualization

## 🔬 Advanced Analytics Capabilities

### Regression Predictions
- **API Gravity ↔ Quality Score**: Strong positive correlation for crude desirability
- **Sulfur Content ↔ Processing Cost**: Inverse relationship modeling
- **Cut Distribution ↔ Refinery Margins**: Yield-based profitability analysis
- **Multi-Factor Composite Scoring**: Holistic crude ranking system

### Optimization Strategies
1. **Traditional Netback Maximization**: Classic approach using market prices
2. **Enhanced Value Maximization**: ML-augmented valuation optimization
3. **Cost Minimization**: Quality-constrained cost optimization
4. **Processing-Aware Optimization**: Complexity-limited blending

### Quality Constraints
- API gravity ranges (light/medium/heavy crude requirements)
- Sulfur content limits (sweet/sour crude specifications)  
- Distillation cut requirements (gasoline/diesel/fuel oil yields)
- **NEW**: ML-based quality scores and processing complexity limits

## 📊 Sample Analytics Queries

```sql
-- Top 10 crudes by composite regression score
SELECT crude_id, name, composite_score, quality_score, enhanced_gross_value
FROM gold_crude_analytics
ORDER BY composite_score DESC
LIMIT 10;

-- Sweet vs Sour performance with regression insights
SELECT 
  CASE WHEN sulfur_wt < 0.5 THEN 'Sweet' ELSE 'Sour' END as crude_type,
  COUNT(*) as count,
  AVG(quality_score) as avg_quality_score,
  AVG(enhanced_gross_value) as avg_enhanced_value,
  AVG(processing_index) as avg_processing_complexity
FROM gold_crude_analytics
GROUP BY CASE WHEN sulfur_wt < 0.5 THEN 'Sweet' ELSE 'Sour' END;

-- Optimization readiness assessment
SELECT crude_id, name, 
  quality_score, processing_index, enhanced_gross_value,
  CASE 
    WHEN quality_score >= 7 AND processing_index <= 70 THEN 'Excellent'
    WHEN quality_score >= 5 AND processing_index <= 80 THEN 'Good'
    ELSE 'Needs Review'
  END as optimization_readiness
FROM gold_crude_analytics
ORDER BY quality_score DESC;
```

## 🎛️ Configuration & Customization

### Regression Model Parameters
```python
# In regression_engine_spark.py
product_prices = {
    'lights': 88.0,    # Gasoline/naphtha pricing
    'middles': 82.0,   # Diesel/jet fuel pricing  
    'heavies': 75.0    # Fuel oil/residuals pricing
}

# Quality scoring weights
ranking_weights = {
    'quality_score': 0.3,      # Crude desirability
    'enhanced_gross_value': 0.4, # Economic value
    'refinery_margin': 0.2,    # Processing profitability
    'processing_index': -0.1   # Complexity penalty
}
```

### Optimization Constraints
```python
# Quality requirements
quality_constraints = {
    'min_api': 28.0,           # Minimum API gravity
    'max_sulfur': 2.0,         # Maximum sulfur content
    'min_quality_score': 6.0,  # ML-based quality threshold
}

# Processing limitations  
processing_constraints = {
    'max_processing_index': 75.0,  # Complexity limit
    'min_refinery_margin': 8.0     # Minimum margin requirement
}
```

## 🔧 Development & Extension

### Adding New Regression Models
```python
# In regression_models.py
models_to_train = {
    'linear': LinearRegression(),
    'ridge': Ridge(alpha=1.0),
    'lasso': Lasso(alpha=0.1),        # Add regularization
    'random_forest': RandomForestRegressor(),
    'gradient_boosting': GradientBoostingRegressor() # Add ensemble
}
```

### Custom Optimization Strategies
```python
# In enhanced_blend_optimization.py
def optimize_custom_strategy(crude_analytics, constraints):
    # Implement domain-specific optimization logic
    # Can incorporate sustainability metrics, transport costs, etc.
    pass
```

### Real-Time Data Integration
- Replace sample CSVs with Auto Loader for streaming ingestion
- Integrate with Argus/Platts pricing feeds
- Add real-time freight and logistics data
- Implement MLOps for continuous model retraining

## 📋 Dependencies

Core requirements (see `requirements.txt`):
- **Data Processing**: `pandas>=2.2.2`, `pyarrow>=16.1.0`
- **Machine Learning**: `scikit-learn>=1.3.0`, `numpy>=1.24.0,<2.0.0`
- **Optimization**: `pyomo>=6.7.1`, `highspy>=1.6.0`  
- **Web Interface**: `flask>=2.3.0`, `flask-cors>=4.0.0`
- **Databricks**: `pyspark` (included in Databricks runtime)

## 🎯 Business Value

### For Traders
- **Enhanced crude ranking** with ML-driven quality scores
- **Real-time valuation models** incorporating market dynamics
- **Risk assessment** through processing complexity analysis

### For Refiners  
- **Optimized blend selection** considering processing constraints
- **Margin prediction** for different crude compositions
- **Quality-aware procurement** strategies

### For Analysts
- **Comprehensive dashboards** with pre-built SQL views
- **Advanced correlation analysis** between crude properties
- **Sensitivity testing** for constraint optimization

## 🚀 Next Steps & Extensions

- **Advanced ML Models**: Deep learning for complex property relationships
- **Time Series Forecasting**: Crude price and quality predictions
- **Sustainability Metrics**: Carbon footprint and environmental impact modeling
- **Portfolio Optimization**: Multi-period blending with inventory constraints
- **Real-Time Streaming**: Live market data integration and continuous optimization
- **API Development**: RESTful services for external system integration

## 📞 Support & Documentation

- **Demo Documentation**: `demo/README.md` - Comprehensive regression demo guide
- **SQL Reference**: `sql/dashboard_views.sql` - Pre-built analytical views
- **Optimization Guide**: `notebooks/06_enhanced_optimization.py` - Advanced optimization examples
- **API Reference**: `src/regression_api.py` - REST API documentation

---

*This platform showcases the power of combining traditional crude oil analytics with modern machine learning techniques. The regression models and optimization strategies provide enhanced decision-making capabilities for crude oil trading, refining, and blending operations.*
