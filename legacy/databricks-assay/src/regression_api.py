"""
Flask API for Crude Assay Regression Demo

This module provides a REST API for the regression demo, allowing the web interface
to make real-time predictions using trained machine learning models.
"""

from flask import Flask, request, jsonify, send_from_directory, render_template_string, render_template
from flask_cors import CORS
import os
import sys
import json
import logging
from typing import Dict, Any
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.regression_models import CrudeAssayRegressor
from src.market_data.yahoo_finance_connector import YahooFinanceConnector
from src.market_data.price_scheduler import PriceScheduler
import pandas as pd
import numpy as np

# Optional: statsmodels for ARIMA
try:
    from statsmodels.tsa.arima.model import ARIMA
    _HAS_STATSMODELS = True
except Exception:
    _HAS_STATSMODELS = False

# Resolve project root (repo root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configure Flask with templates directory at project root
app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, 'templates'),
    static_folder=os.path.join(PROJECT_ROOT, 'static')
)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
regressor = None
price_connector = None
price_scheduler = None


def initialize_regressor():
    """Initialize and train the regression models."""
    global regressor
    
    try:
        regressor = CrudeAssayRegressor()
        
        # Check if pre-trained models exist
        model_path = "/Users/k.jones/Desktop/assay/models/crude_regression_models.pkl"
        
        if os.path.exists(model_path):
            logger.info("Loading pre-trained models...")
            regressor.load_models(model_path)
        else:
            logger.info("No pre-trained models found. Training new models...")
            
            # Generate training data and train models
            training_data = regressor.generate_synthetic_data(n_samples=1000)
            results = regressor.train_models(training_data)
            
            # Save the trained models
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            regressor.save_models(model_path)
            
            logger.info("Models trained and saved successfully!")
            
    except Exception as e:
        logger.error(f"Failed to initialize regressor: {e}")
        # Create a basic regressor for fallback
        regressor = CrudeAssayRegressor()


def initialize_market_data():
    """Initialize market data components."""
    global price_connector, price_scheduler
    
    try:
        price_connector = YahooFinanceConnector()
        price_scheduler = PriceScheduler()
        
        logger.info("Market data components initialized successfully!")
        
        # Start price scheduler if configured
        # price_scheduler.start_scheduler()  # Uncomment to auto-start
        
    except Exception as e:
        logger.error(f"Failed to initialize market data: {e}")


# ===================== PI DATA (CSV) =====================
def _pi_csv_path() -> str:
    return os.path.join(PROJECT_ROOT, 'resources', 'sample_data', 'pi_system_data.csv')


def _load_pi_dataframe() -> pd.DataFrame:
    """Load PI CSV into a DataFrame with parsed timestamps."""
    path = _pi_csv_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"PI data file not found: {path}")
    df = pd.read_csv(path)
    # Normalize column names just in case
    expected_cols = {'timestamp','tag_name','value','unit','quality','crude_tank','crude_id'}
    missing = expected_cols - set(df.columns)
    if missing:
        raise ValueError(f"PI CSV missing columns: {missing}")
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    return df


def _simulate_pi_dataframe(days: int = 90, freq: str = '15min') -> pd.DataFrame:
    """Generate simulated PI-like data for trailing N days.

    Produces tags per tank (LEVEL, TEMP, VOLUME) and some unit tags.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    idx = pd.date_range(start=start, end=end, freq=freq, tz='UTC')

    tanks = [
        ('TK101', 'WTI'),
        ('TK102', 'BRENT'),
        ('TK103', 'MAYA'),
        ('TK104', 'ARB'),
        ('TK105', 'URALS'),
    ]

    rows = []
    rng = np.random.default_rng(42)
    for tank, crude in tanks:
        base_level = rng.uniform(60, 90)
        level = (
            base_level
            + 10 * np.sin(np.linspace(0, 12 * np.pi, len(idx)))
            + rng.normal(0, 1.0, len(idx))
        )
        temp = 85 + 10 * np.sin(np.linspace(0, 2 * np.pi, len(idx))) + rng.normal(0, 0.5, len(idx))
        volume = level * 500  # simple proportionality

        for ts, lv, tp, vol in zip(idx, level, temp, volume):
            rows.append((ts, f"{tank}_LEVEL", float(max(0, min(100, lv))), 'PCT', 'Good', tank, crude))
            rows.append((ts, f"{tank}_TEMP", float(tp), 'DEGF', 'Good', tank, crude))
            rows.append((ts, f"{tank}_VOLUME", float(vol), 'BBL', 'Good', tank, crude))

    # Unit/feed tags (single set)
    unit_tags = [
        ('CDU001', 'BLEND_A', 'CDU_FEED_RATE', 45000, 5000),
        ('CDU001', 'BLEND_A', 'CDU_FEED_TEMP', 480, 10),
        ('VDU001', 'BLEND_B', 'VDU_FEED_RATE', 18500, 2500),
    ]
    for unit, blend, tag, base, amp in unit_tags:
        signal = base + amp * np.sin(np.linspace(0, 6 * np.pi, len(idx))) + rng.normal(0, amp * 0.05, len(idx))
        unit_map = {'CDU_FEED_RATE': 'BPD', 'CDU_FEED_TEMP': 'DEGF', 'VDU_FEED_RATE': 'BPD'}
        unit_str = unit_map.get(tag, '')
        for ts, val in zip(idx, signal):
            rows.append((ts, tag, float(max(0, val)), unit_str, 'Good', unit, blend))

    df = pd.DataFrame(rows, columns=['timestamp','tag_name','value','unit','quality','crude_tank','crude_id'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    return df


@app.route('/api/pi/data', methods=['GET'])
def api_pi_data():
    """Return PI time-series data filtered by optional tags/tanks and time window.

    Query params:
      - tags: comma-separated tag_name values (optional)
      - tanks: comma-separated crude_tank values (optional)
      - start, end: ISO datetimes (optional)
      - limit: max rows (default 5000)
    """
    try:
        df = _load_pi_dataframe()

        tags = request.args.get('tags')
        tanks = request.args.get('tanks')
        start = request.args.get('start')
        end = request.args.get('end')
        limit = int(request.args.get('limit', '5000'))

        if tags:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]
            df = df[df['tag_name'].isin(tag_list)]
        if tanks:
            tank_list = [t.strip() for t in tanks.split(',') if t.strip()]
            df = df[df['crude_tank'].isin(tank_list)]
        if start:
            df = df[df['timestamp'] >= pd.to_datetime(start, utc=True)]
        if end:
            df = df[df['timestamp'] <= pd.to_datetime(end, utc=True)]

        df = df.sort_values('timestamp').head(limit)

        records = [
            {
                'timestamp': ts.isoformat(),
                'tag_name': row.tag_name,
                'value': float(row.value),
                'unit': row.unit,
                'quality': row.quality,
                'crude_tank': row.crude_tank,
                'crude_id': row.crude_id,
            }
            for ts, row in zip(df['timestamp'], df.itertuples(index=False))
        ]

        return jsonify({
            'count': len(records),
            'records': records,
            'tags': sorted(df['tag_name'].unique().tolist()),
            'tanks': sorted(df['crude_tank'].unique().tolist()),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"PI data error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/pi/simulate', methods=['POST'])
def api_pi_simulate():
    """Regenerate PI CSV with trailing 90 days of simulated data.

    Body JSON (optional): {"days": 90, "freq": "15min"}
    """
    try:
        body = request.get_json(silent=True) or {}
        days = int(body.get('days', 90))
        freq = body.get('freq', '15min')
        df = _simulate_pi_dataframe(days=days, freq=freq)
        path = _pi_csv_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)
        return jsonify({'status': 'success', 'rows': int(len(df)), 'file': path})
    except Exception as e:
        logger.error(f"PI simulate error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/pi/forecast', methods=['GET'])
def api_pi_forecast():
    """ARIMA forecast per tag for the provided tags/tanks.

    Query params:
      - tags: comma-separated tag_name
      - tanks: comma-separated crude_tank
      - horizon_hours: forecast horizon in hours (default 24)
      - freq: sampling frequency for forecast (default '15min')
    """
    try:
        if not _HAS_STATSMODELS:
            return jsonify({'error': 'statsmodels not installed for ARIMA', 'status': 'error'}), 500

        df = _load_pi_dataframe()
        tags = request.args.get('tags')
        tanks = request.args.get('tanks')
        horizon_hours = int(request.args.get('horizon_hours', '24'))
        freq = request.args.get('freq', '15min')

        if tags:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]
            df = df[df['tag_name'].isin(tag_list)]
        if tanks:
            tank_list = [t.strip() for t in tanks.split(',') if t.strip()]
            df = df[df['crude_tank'].isin(tank_list)]

        out = {}
        for tag, g in df.groupby('tag_name'):
            g = g.sort_values('timestamp')
            ts = g.set_index('timestamp')['value'].astype(float).asfreq(freq)
            ts = ts.interpolate().fillna(method='bfill').fillna(method='ffill')
            # Simple ARIMA(1,1,1) as default
            try:
                model = ARIMA(ts, order=(1,1,1))
                fit = model.fit()
                step_seconds = pd.Timedelta(freq).total_seconds()
                steps = max(1, int((horizon_hours * 3600) / step_seconds))
                fc = fit.forecast(steps=steps)
                out[tag] = {
                    'timestamps': [t.isoformat() for t in fc.index.to_pydatetime()],
                    'values': [float(v) for v in fc.values]
                }
            except Exception as ex:
                out[tag] = {'error': str(ex)}

        return jsonify({'status': 'success', 'forecast': out, 'freq': freq, 'horizon_hours': horizon_hours})
    except Exception as e:
        logger.error(f"PI forecast error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


# ===================== BLISS / ASPENTECH PLANNING =====================
def _bliss_csv_path() -> str:
    return os.path.join(PROJECT_ROOT, 'resources', 'sample_data', 'aspentech_planning.csv')


def _load_bliss_dataframe() -> pd.DataFrame:
    path = _bliss_csv_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"AspenTech planning file not found: {path}")
    df = pd.read_csv(path)
    # Parse datetimes
    if 'run_date' in df.columns:
        df['run_date'] = pd.to_datetime(df['run_date'], utc=True, errors='coerce')
        # Derive planning_period from actual run_date to keep periods current
        df['planning_period'] = df['run_date'].dt.strftime('%b%Y')
    return df


@app.route('/api/bliss/planning', methods=['GET'])
def api_bliss_planning():
    """Return planning scenarios with optional filters.

    Query params:
      - scenarios: comma-separated scenario_id
      - period: planning_period filter
    """
    try:
        df = _load_bliss_dataframe()
        scenarios = request.args.get('scenarios')
        period = request.args.get('period')
        if period:
            df = df[df['planning_period'] == period]
        if scenarios:
            lst = [s.strip() for s in scenarios.split(',') if s.strip()]
            df = df[df['scenario_id'].isin(lst)]
        df = df.sort_values(['planning_period','run_date','scenario_id'])
        records = df.to_dict(orient='records')
        # Ensure native types
        for r in records:
            if isinstance(r.get('run_date'), pd.Timestamp):
                r['run_date'] = r['run_date'].isoformat()
        return jsonify({'count': len(records), 'records': records, 'status': 'success'})
    except Exception as e:
        logger.error(f"Bliss planning error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/pi/snapshot', methods=['GET'])
def api_pi_snapshot():
    """Return the latest value per tag (optionally filtered by tanks)."""
    try:
        df = _load_pi_dataframe()
        tanks = request.args.get('tanks')
        if tanks:
            tank_list = [t.strip() for t in tanks.split(',') if t.strip()]
            df = df[df['crude_tank'].isin(tank_list)]
        # Latest per tag_name
        idx = df.groupby('tag_name')['timestamp'].idxmax()
        latest = df.loc[idx].sort_values('tag_name')
        snapshot = [
            {
                'timestamp': row.timestamp.isoformat(),
                'tag_name': row.tag_name,
                'value': float(row.value),
                'unit': row.unit,
                'crude_tank': row.crude_tank,
                'crude_id': row.crude_id,
                'quality': row.quality,
            }
            for _, row in latest.iterrows()
        ]
        return jsonify({'count': len(snapshot), 'records': snapshot, 'status': 'success'})
    except Exception as e:
        logger.error(f"PI snapshot error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/')
def index():
    """Home page with navigation to unified features."""
    try:
        return render_template('home.html', title='Crude Assay Platform', active='home')
    except Exception as e:
        logger.error(f"Error rendering home page: {e}")
        return jsonify({'error': 'Failed to render home page', 'status': 'error'}), 500


@app.route('/predict')
def predict_page():
    """Serve the original standalone prediction demo (no navbar wrapper)."""
    demo_path = os.path.join(PROJECT_ROOT, 'demo', 'crude_assay_regression_demo.html')
    if os.path.exists(demo_path):
        with open(demo_path, 'r') as f:
            return f.read()
    return "Demo page not found", 404


@app.route('/predict/raw')
def predict_page_raw():
    """Serve the legacy standalone demo HTML (no navbar)."""
    demo_path = os.path.join(PROJECT_ROOT, 'demo', 'crude_assay_regression_demo.html')
    if os.path.exists(demo_path):
        with open(demo_path, 'r') as f:
            return f.read()
    return "Demo page not found", 404


@app.route('/market')
def market_page():
    """Market data dashboard page."""
    return render_template('market.html', title='Market Data', active='market')


@app.route('/optimization')
def optimization_page():
    """Optimization scenarios page."""
    return render_template('optimization.html', title='Optimization', active='optimization')


@app.route('/about')
def about_page():
    """About and diagnostics page."""
    return render_template('about.html', title='About', active='about')


@app.route('/pi')
def pi_page():
    """PI System data visualization page."""
    return render_template('pi.html', title='PI Data', active='pi')


@app.route('/bliss')
def bliss_page():
    """Bliss blend recipes visualization page (AspenTech planning)."""
    # e.g., 'Sep2025'
    try:
        current_period = datetime.now(timezone.utc).strftime('%b%Y')
    except Exception:
        current_period = ''
    return render_template('bliss.html', title='Bliss Recipes', active='bliss', default_period=current_period)


@app.route('/dashboard')
def dashboard_page():
    """Unified analytics dashboard (Flask version of Streamlit dashboard)."""
    return render_template('dashboard.html', title='Dashboard', active='dashboard')


@app.route('/api/dashboard/sample_crudes', methods=['GET'])
def api_dashboard_sample_crudes():
    """Provide sample crude dataset for dashboard visualizations (local/demo)."""
    data = {
        'crude_id': ['WTI', 'BRENT', 'ARB', 'MAYA', 'URALS', 'SAHARA', 'CANADIAN_HEAVY', 'NIGERIAN_LIGHT'],
        'name': ['West Texas Intermediate', 'Brent', 'Arab Light', 'Maya Heavy', 'Urals', 'Sahara Blend', 'Canadian Heavy', 'Nigerian Light'],
        'api': [39.6, 38.3, 33.0, 22.0, 31.7, 44.1, 20.5, 37.4],
        'sulfur_wt': [0.24, 0.37, 1.8, 3.4, 1.3, 0.10, 3.8, 0.14],
        'current_price': [78.45, 82.30, 76.20, 66.50, 74.80, 84.60, 63.25, 81.45],
        'quality_score': [9.2, 8.8, 7.4, 4.2, 7.1, 9.6, 3.8, 9.0],
        'processing_index': [25.4, 28.2, 45.6, 78.9, 52.3, 18.7, 85.4, 22.1],
        'enhanced_gross_value': [89.2, 88.5, 84.7, 71.2, 82.1, 92.8, 68.4, 87.9],
        'crude_category': ['Light Sweet', 'Light Sweet', 'Medium Sour', 'Heavy Sour', 'Medium Sour', 'Light Sweet', 'Heavy Sour', 'Light Sweet']
    }
    df = pd.DataFrame(data)
    # compute value_enhancement like Streamlit view
    df['value_enhancement'] = df['enhanced_gross_value'] - df['current_price']
    return jsonify({'count': len(df), 'records': df.to_dict(orient='records'), 'status': 'success'})


# ===================== HAVERLY OPTIMIZATION =====================
def _haverly_csv_path() -> str:
    return os.path.join(PROJECT_ROOT, 'resources', 'sample_data', 'haverly_optimization.csv')


def _load_haverly_dataframe() -> pd.DataFrame:
    path = _haverly_csv_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Haverly optimization file not found: {path}")
    df = pd.read_csv(path)
    if 'run_timestamp' in df.columns:
        df['run_timestamp'] = pd.to_datetime(df['run_timestamp'], utc=True, errors='coerce')
    return df


@app.route('/api/haverly/runs', methods=['GET'])
def api_haverly_runs():
    """Return Haverly optimization runs with optional filters.

    Query params:
      - models: comma-separated model_name
      - from, to: ISO time window for run_timestamp
    """
    try:
        df = _load_haverly_dataframe()
        models = request.args.get('models')
        from_ts = request.args.get('from')
        to_ts = request.args.get('to')
        if models:
            names = [m.strip() for m in models.split(',') if m.strip()]
            df = df[df['model_name'].isin(names)]
        if from_ts:
            df = df[df['run_timestamp'] >= pd.to_datetime(from_ts, utc=True)]
        if to_ts:
            df = df[df['run_timestamp'] <= pd.to_datetime(to_ts, utc=True)]
        df = df.sort_values(['run_timestamp','model_name'])
        recs = df.to_dict(orient='records')
        for r in recs:
            if isinstance(r.get('run_timestamp'), pd.Timestamp):
                r['run_timestamp'] = r['run_timestamp'].isoformat()
        return jsonify({'count': len(recs), 'records': recs, 'status': 'success'})
    except Exception as e:
        logger.error(f"Haverly runs error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


# ===================== INTERTEK LAB REPORTS =====================
def _intertek_csv_path() -> str:
    return os.path.join(PROJECT_ROOT, 'resources', 'sample_data', 'intertek_lab_reports.csv')


def _load_intertek_dataframe() -> pd.DataFrame:
    path = _intertek_csv_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Intertek lab reports file not found: {path}")
    df = pd.read_csv(path)
    if 'report_date' in df.columns:
        df['report_date'] = pd.to_datetime(df['report_date'], utc=True, errors='coerce')
    return df


@app.route('/api/intertek/reports', methods=['GET'])
def api_intertek_reports():
    """Return lab report rows with filters.

    Query params:
      - crudes: comma-separated crude_id
      - labs: comma-separated lab_location
      - from, to: ISO date window for report_date
    """
    try:
        df = _load_intertek_dataframe()
        crudes = request.args.get('crudes')
        labs = request.args.get('labs')
        from_dt = request.args.get('from')
        to_dt = request.args.get('to')
        if crudes:
            ids = [c.strip() for c in crudes.split(',') if c.strip()]
            df = df[df['crude_id'].isin(ids)]
        if labs:
            locs = [l.strip() for l in labs.split(',') if l.strip()]
            df = df[df['lab_location'].isin(locs)]
        if from_dt:
            df = df[df['report_date'] >= pd.to_datetime(from_dt, utc=True)]
        if to_dt:
            df = df[df['report_date'] <= pd.to_datetime(to_dt, utc=True)]
        df = df.sort_values(['report_date','crude_id'])
        recs = df.to_dict(orient='records')
        for r in recs:
            if isinstance(r.get('report_date'), pd.Timestamp):
                r['report_date'] = r['report_date'].date().isoformat()
        return jsonify({'count': len(recs), 'records': recs, 'status': 'success'})
    except Exception as e:
        logger.error(f"Intertek reports error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/haverly')
def haverly_page():
    return render_template('haverly.html', title='Haverly Optimization', active='haverly')


@app.route('/intertek')
def intertek_page():
    return render_template('intertek.html', title='Intertek Lab Reports', active='intertek')


@app.route('/api/predict', methods=['POST'])
def predict():
    """
    Make regression predictions based on crude assay inputs.
    
    Expected JSON payload:
    {
        "api_gravity": 33.0,
        "sulfur_content": 1.8,
        "light_cuts": 0.35,
        "middle_cuts": 0.45,
        "heavy_cuts": 0.20
    }
    
    Returns:
    {
        "predictions": {
            "gross_value": 84.50,
            "netback_value": 82.75,
            "quality_score": 7.8,
            "processing_index": 85.2
        },
        "inputs": {...},
        "status": "success"
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['api_gravity', 'sulfur_content', 'light_cuts', 'middle_cuts', 'heavy_cuts']
        
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': f'Missing required field: {field}',
                    'status': 'error'
                }), 400
        
        # Extract and validate inputs
        api_gravity = float(data['api_gravity'])
        sulfur_content = float(data['sulfur_content'])
        light_cuts = float(data['light_cuts'])
        middle_cuts = float(data['middle_cuts'])
        heavy_cuts = float(data['heavy_cuts'])
        
        # Validate ranges
        if not (10 <= api_gravity <= 50):
            return jsonify({'error': 'API gravity must be between 10-50°', 'status': 'error'}), 400
        
        if not (0 <= sulfur_content <= 10):
            return jsonify({'error': 'Sulfur content must be between 0-10%', 'status': 'error'}), 400
        
        if not (0 <= light_cuts <= 1):
            return jsonify({'error': 'Light cuts must be between 0-1', 'status': 'error'}), 400
        
        if not (0 <= middle_cuts <= 1):
            return jsonify({'error': 'Middle cuts must be between 0-1', 'status': 'error'}), 400
            
        if not (0 <= heavy_cuts <= 1):
            return jsonify({'error': 'Heavy cuts must be between 0-1', 'status': 'error'}), 400
        
        # Ensure cuts sum to approximately 1.0
        total_cuts = light_cuts + middle_cuts + heavy_cuts
        if not (0.95 <= total_cuts <= 1.05):
            return jsonify({
                'error': f'Distillation cuts must sum to ~1.0 (got {total_cuts:.3f})',
                'status': 'error'
            }), 400
        
        # Make predictions
        if regressor is None:
            return jsonify({'error': 'Regression models not initialized', 'status': 'error'}), 500
        
        predictions = regressor.predict(
            api_gravity, sulfur_content, light_cuts, middle_cuts, heavy_cuts
        )
        
        # Round predictions for display
        formatted_predictions = {
            key: round(value, 2) if 'value' in key else round(value, 1)
            for key, value in predictions.items()
        }
        
        return jsonify({
            'predictions': formatted_predictions,
            'inputs': {
                'api_gravity': api_gravity,
                'sulfur_content': sulfur_content,
                'light_cuts': light_cuts,
                'middle_cuts': middle_cuts,
                'heavy_cuts': heavy_cuts
            },
            'status': 'success'
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid input values: {e}', 'status': 'error'}), 400
    
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({'error': 'Internal server error', 'status': 'error'}), 500


@app.route('/api/batch_predict', methods=['POST'])
def batch_predict():
    """
    Make predictions for multiple crude samples at once.
    
    Expected JSON payload:
    {
        "samples": [
            {
                "name": "Arab Light",
                "api_gravity": 33.0,
                "sulfur_content": 1.8,
                "light_cuts": 0.35,
                "middle_cuts": 0.45,
                "heavy_cuts": 0.20
            },
            ...
        ]
    }
    """
    try:
        data = request.json
        
        if 'samples' not in data:
            return jsonify({'error': 'Missing samples array', 'status': 'error'}), 400
        
        results = []
        
        for i, sample in enumerate(data['samples']):
            try:
                # Make prediction for this sample
                predictions = regressor.predict(
                    sample['api_gravity'],
                    sample['sulfur_content'], 
                    sample['light_cuts'],
                    sample['middle_cuts'],
                    sample['heavy_cuts']
                )
                
                results.append({
                    'name': sample.get('name', f'Sample {i+1}'),
                    'inputs': {k: v for k, v in sample.items() if k != 'name'},
                    'predictions': predictions
                })
                
            except Exception as e:
                results.append({
                    'name': sample.get('name', f'Sample {i+1}'),
                    'error': str(e)
                })
        
        return jsonify({
            'results': results,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        return jsonify({'error': 'Internal server error', 'status': 'error'}), 500


@app.route('/api/model_info', methods=['GET'])
def model_info():
    """Get information about the trained models."""
    try:
        if regressor is None:
            return jsonify({'error': 'Models not initialized', 'status': 'error'}), 500
        
        summary = regressor.get_model_summary()
        
        return jsonify({
            'model_summary': summary,
            'feature_names': regressor.feature_names,
            'target_names': regressor.target_names,
            'product_prices': regressor.product_prices,
            'freight_rates': regressor.freight_rates,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Model info error: {e}")
        return jsonify({'error': 'Internal server error', 'status': 'error'}), 500


@app.route('/api/sample_crudes', methods=['GET'])
def sample_crudes():
    """Get sample crude oil data for testing."""
    samples = {
        'arab-light': {
            'name': 'Arab Light',
            'api_gravity': 33.0,
            'sulfur_content': 1.8,
            'light_cuts': 0.35,
            'middle_cuts': 0.45,
            'heavy_cuts': 0.20,
            'description': 'Medium sweet crude from Saudi Arabia'
        },
        'west-african': {
            'name': 'West African Blend',
            'api_gravity': 36.5,
            'sulfur_content': 0.25,
            'light_cuts': 0.40,
            'middle_cuts': 0.45,
            'heavy_cuts': 0.15,
            'description': 'Light sweet crude from West Africa'
        },
        'mars': {
            'name': 'Mars',
            'api_gravity': 29.0,
            'sulfur_content': 2.0,
            'light_cuts': 0.25,
            'middle_cuts': 0.45,
            'heavy_cuts': 0.30,
            'description': 'Medium sour crude from US Gulf'
        },
        'wti': {
            'name': 'West Texas Intermediate',
            'api_gravity': 39.6,
            'sulfur_content': 0.24,
            'light_cuts': 0.45,
            'middle_cuts': 0.40,
            'heavy_cuts': 0.15,
            'description': 'Light sweet US benchmark crude'
        },
        'heavy-maya': {
            'name': 'Maya Heavy',
            'api_gravity': 22.0,
            'sulfur_content': 3.4,
            'light_cuts': 0.20,
            'middle_cuts': 0.35,
            'heavy_cuts': 0.45,
            'description': 'Heavy sour crude from Mexico'
        }
    }
    
    return jsonify({
        'samples': samples,
        'status': 'success'
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'models_loaded': regressor is not None,
        'market_data_available': price_connector is not None,
        'price_scheduler_available': price_scheduler is not None,
        'api_version': '1.0'
    })


@app.route('/api/market/live_prices', methods=['GET'])
def get_live_prices():
    """
    Get current live crude oil prices from Yahoo Finance.
    
    Query parameters:
    - crude_ids: Comma-separated list of crude IDs (optional)
    """
    try:
        if price_connector is None:
            return jsonify({'error': 'Market data connector not available', 'status': 'error'}), 503
        
        # Get crude IDs from query parameters
        crude_ids_param = request.args.get('crude_ids')
        crude_ids = crude_ids_param.split(',') if crude_ids_param else None
        
        # Fetch live prices
        prices = price_connector.get_crude_prices(crude_ids)
        
        # Format response
        price_data = {}
        for crude_id, price_obj in prices.items():
            price_data[crude_id] = {
                'current_price': price_obj.current_price,
                'change': price_obj.change,
                'change_percent': price_obj.change_percent,
                'volume': price_obj.volume,
                'day_high': price_obj.day_high,
                'day_low': price_obj.day_low,
                'market_status': price_obj.market_status,
                'timestamp': price_obj.timestamp.isoformat(),
                'ticker': price_obj.ticker
            }
        
        return jsonify({
            'prices': price_data,
            'count': len(price_data),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error fetching live prices: {e}")
        return jsonify({'error': 'Failed to fetch live prices', 'status': 'error'}), 500


@app.route('/api/market/historical_prices', methods=['GET'])
def get_historical_prices():
    """
    Get historical crude oil prices.
    
    Query parameters:
    - crude_ids: Comma-separated list of crude IDs (required)
    - period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
    - interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
    """
    try:
        if price_connector is None:
            return jsonify({'error': 'Market data connector not available', 'status': 'error'}), 503
        
        # Get parameters
        crude_ids_param = request.args.get('crude_ids')
        if not crude_ids_param:
            return jsonify({'error': 'crude_ids parameter required', 'status': 'error'}), 400
        
        crude_ids = crude_ids_param.split(',')
        period = request.args.get('period', '30d')
        interval = request.args.get('interval', '1d')
        
        # Fetch historical data
        historical_df = price_connector.get_historical_prices(crude_ids, period, interval)
        
        if historical_df.empty:
            return jsonify({
                'historical_data': [],
                'count': 0,
                'message': 'No historical data available',
                'status': 'success'
            })
        
        # Convert to JSON format
        historical_data = historical_df.to_dict('records')
        
        return jsonify({
            'historical_data': historical_data,
            'count': len(historical_data),
            'period': period,
            'interval': interval,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error fetching historical prices: {e}")
        return jsonify({'error': 'Failed to fetch historical prices', 'status': 'error'}), 500


@app.route('/api/market/summary', methods=['GET'])
def get_market_summary():
    """Get overall crude oil market summary."""
    try:
        if price_connector is None:
            return jsonify({'error': 'Market data connector not available', 'status': 'error'}), 503
        
        summary = price_connector.get_market_summary()
        
        return jsonify({
            'market_summary': summary,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error fetching market summary: {e}")
        return jsonify({'error': 'Failed to fetch market summary', 'status': 'error'}), 500


@app.route('/api/market/scheduler/start', methods=['POST'])
def start_price_scheduler():
    """Start the automated price update scheduler."""
    try:
        if price_scheduler is None:
            return jsonify({'error': 'Price scheduler not available', 'status': 'error'}), 503
        
        if price_scheduler.is_running:
            return jsonify({
                'message': 'Price scheduler is already running',
                'status': 'success'
            })
        
        price_scheduler.start_scheduler()
        
        return jsonify({
            'message': 'Price scheduler started successfully',
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error starting price scheduler: {e}")
        return jsonify({'error': 'Failed to start price scheduler', 'status': 'error'}), 500


@app.route('/api/market/scheduler/stop', methods=['POST'])
def stop_price_scheduler():
    """Stop the automated price update scheduler."""
    try:
        if price_scheduler is None:
            return jsonify({'error': 'Price scheduler not available', 'status': 'error'}), 503
        
        if not price_scheduler.is_running:
            return jsonify({
                'message': 'Price scheduler is not running',
                'status': 'success'
            })
        
        price_scheduler.stop_scheduler()
        
        return jsonify({
            'message': 'Price scheduler stopped successfully',
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error stopping price scheduler: {e}")
        return jsonify({'error': 'Failed to stop price scheduler', 'status': 'error'}), 500


@app.route('/api/market/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Get price scheduler status."""
    try:
        if price_scheduler is None:
            return jsonify({'error': 'Price scheduler not available', 'status': 'error'}), 503
        
        status = price_scheduler.get_status()
        
        return jsonify({
            'scheduler_status': status,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({'error': 'Failed to get scheduler status', 'status': 'error'}), 500


@app.route('/api/market/update_prices', methods=['POST'])
def manual_price_update():
    """Manually trigger a price update."""
    try:
        if price_scheduler is None:
            return jsonify({'error': 'Price scheduler not available', 'status': 'error'}), 503
        
        # Run price update
        price_scheduler.update_prices()
        
        return jsonify({
            'message': 'Price update completed successfully',
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in manual price update: {e}")
        return jsonify({'error': 'Failed to update prices', 'status': 'error'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found', 'status': 'error'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error', 'status': 'error'}), 500


def main():
    """Run the Flask development server."""
    
    # Initialize the regressor
    initialize_regressor()
    
    if regressor is None:
        logger.error("Failed to initialize regressor. Exiting.")
        return
    
    # Initialize market data components
    initialize_market_data()
    
    logger.info("Starting Flask API server...")
    logger.info("Demo available at: http://localhost:5000")
    logger.info("API endpoints available at: http://localhost:5000/api/")
    logger.info("Market data endpoints:")
    logger.info("  GET  /api/market/live_prices")
    logger.info("  GET  /api/market/historical_prices")
    logger.info("  GET  /api/market/summary")
    logger.info("  POST /api/market/scheduler/start")
    logger.info("  POST /api/market/scheduler/stop")
    logger.info("  GET  /api/market/scheduler/status")
    logger.info("  POST /api/market/update_prices")
    
    # Run the development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False  # Avoid reloading models
    )


if __name__ == "__main__":
    main()
