# 📈 Yahoo Finance Real-Time Market Data Integration

## Overview

The Yahoo Finance integration provides real-time crude oil pricing data to enhance your crude assay analytics with live market conditions. This integration automatically fetches current prices, historical data, and market summaries to keep your analytics up-to-date with market movements.

## 🚀 Key Features

### Real-Time Price Data
- **Live crude oil futures prices** (WTI, Brent, etc.)
- **Automatic price adjustments** for regional crude differentials
- **Market status monitoring** (open/closed/pre-market)
- **Price change alerts** for significant movements

### Automated Updates
- **Scheduled price updates** every 15 minutes during market hours
- **Market hours detection** to avoid unnecessary API calls
- **Configurable update frequency** and alert thresholds
- **Automatic historical data archival**

### API Integration
- **REST API endpoints** for live market data
- **Historical price data** with flexible time periods
- **Market summary information** for benchmarks
- **Scheduler control** via API (start/stop/status)

## 📊 Supported Crude Oil Types

### Direct Futures Mapping
- **WTI Crude Oil**: `CL=F` (NYMEX)
- **Brent Crude Oil**: `BZ=F` (ICE)

### Regional Crude Proxies
Our system maps regional crudes to benchmark futures with appropriate differentials:

| Crude Oil | Benchmark | Typical Differential |
|-----------|-----------|---------------------|
| Arab Light | WTI | -$1.50/bbl |
| Maya Heavy | WTI | -$12.00/bbl |
| Urals | Brent | -$2.50/bbl |
| Nigerian Light | Brent | +$0.50/bbl |
| Canadian Heavy | WTI | -$15.00/bbl |
| Sahara Blend | Brent | +$1.25/bbl |

## 🔧 Configuration

### Price Scheduler Configuration (`conf/price_scheduler_config.json`)

```json
{
  "update_frequency_minutes": 15,
  "market_hours_only": true,
  "market_open_hour": 9,
  "market_close_hour": 17,
  "weekend_updates": false,
  "crude_ids": ["WTI", "BRENT", "ARB", "MAYA", "URALS"],
  "price_change_threshold": 2.0,
  "enable_alerts": true
}
```

### Customizable Parameters
- **Update Frequency**: 5-60 minutes (recommended: 15 minutes)
- **Market Hours**: Configurable by timezone and trading schedule
- **Alert Thresholds**: Set price change percentages for notifications
- **Crude Selection**: Choose which crude oils to track

## 🔌 API Endpoints

### Live Market Data

#### Get Current Prices
```http
GET /api/market/live_prices?crude_ids=WTI,BRENT,ARB
```

**Response:**
```json
{
  "prices": {
    "WTI": {
      "current_price": 78.45,
      "change": 1.23,
      "change_percent": 1.59,
      "volume": 125000,
      "day_high": 79.12,
      "day_low": 77.88,
      "market_status": "REGULAR",
      "timestamp": "2024-01-15T14:30:00Z",
      "ticker": "CL=F"
    }
  },
  "count": 1,
  "status": "success"
}
```

#### Get Historical Data
```http
GET /api/market/historical_prices?crude_ids=WTI,BRENT&period=30d&interval=1d
```

#### Get Market Summary
```http
GET /api/market/summary
```

### Scheduler Control

#### Start Automatic Updates
```http
POST /api/market/scheduler/start
```

#### Stop Automatic Updates
```http
POST /api/market/scheduler/stop
```

#### Get Scheduler Status
```http
GET /api/market/scheduler/status
```

#### Manual Price Update
```http
POST /api/market/update_prices
```

## 💻 Python Usage Examples

### Basic Price Fetching
```python
from src.market_data.yahoo_finance_connector import YahooFinanceConnector

connector = YahooFinanceConnector()

# Get current prices
prices = connector.get_crude_prices(['WTI', 'BRENT', 'ARB'])

for crude_id, price_obj in prices.items():
    print(f"{crude_id}: ${price_obj.current_price:.2f} "
          f"({price_obj.change_percent:+.1f}%)")
```

### Historical Data Analysis
```python
# Get 30 days of daily price data
historical = connector.get_historical_prices(
    crude_ids=['WTI', 'BRENT'],
    period='30d',
    interval='1d'
)

# Analyze price trends
import pandas as pd
for crude_id in ['WTI', 'BRENT']:
    crude_data = historical[historical['crude_id'] == crude_id]
    avg_price = crude_data['Close'].mean()
    volatility = crude_data['Close'].std()
    print(f"{crude_id}: Avg=${avg_price:.2f}, Vol={volatility:.2f}")
```

### Automated Scheduler
```python
from src.market_data.price_scheduler import PriceScheduler

scheduler = PriceScheduler()

# Start automatic updates
scheduler.start_scheduler()

# Check status
status = scheduler.get_status()
print(f"Running: {status['is_running']}")
print(f"Next update: {status['next_run']}")

# Stop when done
scheduler.stop_scheduler()
```

## 🔄 Integration with Regression Models

### Dynamic Price Updates
The Yahoo Finance integration automatically updates the product prices used in regression models:

```python
# Prices are automatically updated in valuation calculations
enhanced_value = calculate_enhanced_value_with_live_prices(
    api_gravity=33.0,
    sulfur_content=1.8,
    light_cuts=0.35,
    middle_cuts=0.45,
    heavy_cuts=0.20
)
```

### Market-Responsive Analytics
- **Real-time valuation updates** based on current market conditions
- **Price correlation analysis** using live market data
- **Dynamic optimization** with current price assumptions
- **Market timing insights** for crude purchasing decisions

## ⚡ Performance & Reliability

### Rate Limiting
- **Respectful API usage** with appropriate delays between requests
- **Efficient batch processing** for multiple crude oils
- **Error handling and retries** for network issues
- **Fallback mechanisms** when market data is unavailable

### Data Quality
- **Price validation** against reasonable ranges
- **Outlier detection** for erroneous data points
- **Quality scoring** based on data freshness and completeness
- **Alternative data sources** as backup options

### Monitoring & Alerts
- **Price change notifications** for significant movements
- **System health monitoring** for API connectivity
- **Data freshness tracking** with age indicators
- **Error logging and alerting** for troubleshooting

## 🛠️ Setup Instructions

### 1. Install Dependencies
```bash
pip install yfinance>=0.2.18 requests>=2.31.0 schedule>=1.2.0
```

### 2. Configure Settings
Edit `conf/price_scheduler_config.json` with your preferences:
- Update frequency (recommended: 15 minutes)
- Market hours for your timezone
- Crude oils to track
- Alert thresholds

### 3. Test Integration
```bash
python scripts/test_yahoo_finance.py
```

### 4. Start API Server with Market Data
```bash
python src/regression_api.py
```

### 5. Enable Automatic Updates (Optional)
Access the API endpoints to start the scheduler:
```bash
curl -X POST http://localhost:5000/api/market/scheduler/start
```

## 🚨 Troubleshooting

### Common Issues

#### No Price Data Retrieved
- **Check internet connection** and Yahoo Finance accessibility
- **Verify crude ID mappings** in the connector configuration
- **Check market hours** - some data may only be available during trading

#### Outdated Price Data
- **Check scheduler status** via `/api/market/scheduler/status`
- **Manual update trigger** via `/api/market/update_prices`
- **Review configuration** for appropriate update frequency

#### API Rate Limiting
- **Reduce update frequency** to avoid excessive requests
- **Implement exponential backoff** for failed requests
- **Use cached data** when live data is temporarily unavailable

### Data Quality Validation
```python
# Validate price data quality
prices = connector.get_crude_prices(['WTI', 'BRENT'])

for crude_id, price_obj in prices.items():
    # Check for reasonable price ranges
    if not (20.0 <= price_obj.current_price <= 200.0):
        print(f"⚠️ Unusual price for {crude_id}: ${price_obj.current_price}")
    
    # Check data freshness
    age_minutes = (datetime.now() - price_obj.timestamp).total_seconds() / 60
    if age_minutes > 30:
        print(f"⚠️ Stale data for {crude_id}: {age_minutes:.1f} minutes old")
```

## 📈 Market Data Files

### Generated Files
- **`live_prices.csv`**: Current market prices with metadata
- **`historical_prices.csv`**: Historical price data for analysis
- **`market_summary.json`**: Market overview and benchmark data

### File Formats
Live prices CSV structure:
```csv
crude_id,price_usd_bbl,change,change_percent,volume,timestamp,market_status
WTI,78.45,1.23,1.59,125000,2024-01-15T14:30:00Z,REGULAR
```

## 🔮 Advanced Features

### Price Prediction Enhancement
- **Historical volatility calculation** for risk analysis
- **Correlation analysis** between different crude types
- **Seasonal price pattern recognition**
- **Market trend indicators** for timing decisions

### Custom Differentials
Configure your own price differentials based on regional market conditions:
```python
# Custom price adjustments
CUSTOM_ADJUSTMENTS = {
    'LOCAL_CRUDE_A': -3.50,  # $3.50 discount to WTI
    'LOCAL_CRUDE_B': +2.25,  # $2.25 premium to Brent
}
```

### Market Event Detection
- **Significant price movement alerts** (>5% changes)
- **Volume spike detection** for market activity
- **Volatility monitoring** for risk management
- **Cross-commodity correlation** analysis

## 📊 Dashboard Integration

The Yahoo Finance data seamlessly integrates with your existing dashboard views:

### Real-Time Price Display
```sql
-- Current market prices with regression analytics
SELECT 
    c.crude_id,
    c.name,
    lp.price_usd_bbl as current_price,
    lp.change_percent as daily_change,
    p.enhanced_gross_value,
    (p.enhanced_gross_value - lp.price_usd_bbl) as enhancement_premium
FROM gold_crude_analytics c
JOIN live_prices lp ON c.crude_id = lp.crude_id
JOIN gold_crude_predictions p ON c.crude_id = p.crude_id
ORDER BY lp.change_percent DESC;
```

---

**🎯 The Yahoo Finance integration transforms your crude assay analytics from static analysis to dynamic, market-responsive intelligence!**
