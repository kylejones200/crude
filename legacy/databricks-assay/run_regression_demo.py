#!/usr/bin/env python3
"""
Crude Assay Regression Demo Launcher

This script sets up and launches the regression demo, including:
1. Model training (if needed)
2. Flask API server
3. Web interface

Usage:
    python run_regression_demo.py [--train-models] [--port 5000]
"""

import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

try:
    from src.regression_models import CrudeAssayRegressor
    from src.regression_api import app, initialize_regressor, initialize_market_data
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)


def setup_logging():
    """Configure logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('regression_demo.log')
        ]
    )


def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        'pandas', 'numpy', 'scikit-learn', 'flask', 'flask_cors'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            import_name = 'sklearn' if package == 'scikit-learn' else package.replace('-', '_')
            __import__(import_name)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:", missing_packages)
        print("Please install them with:")
        print("pip install " + " ".join(missing_packages))
        return False
    
    return True


def train_models(force_retrain=False):
    """Train or load regression models."""
    logger = logging.getLogger(__name__)
    
    model_path = project_root / "models" / "crude_regression_models.pkl"
    
    # Create models directory if it doesn't exist
    model_path.parent.mkdir(exist_ok=True)
    
    if model_path.exists() and not force_retrain:
        logger.info(f"Using existing models: {model_path}")
        return True
    
    logger.info("Training new regression models...")
    
    try:
        # Initialize regressor
        regressor = CrudeAssayRegressor()
        
        # Generate synthetic training data
        logger.info("Generating synthetic training data...")
        training_data = regressor.generate_synthetic_data(n_samples=1500)
        
        # Train models
        logger.info("Training regression models...")
        results = regressor.train_models(training_data)
        
        # Log training results
        logger.info("Model training completed!")
        for target, target_results in results.items():
            best_model = max(target_results.keys(), 
                           key=lambda k: target_results[k]['r2_score'])
            best_r2 = target_results[best_model]['r2_score']
            logger.info(f"{target}: Best model = {best_model} (R² = {best_r2:.3f})")
        
        # Save models
        regressor.save_models(str(model_path))
        logger.info(f"Models saved to: {model_path}")
        
        # Save summary
        summary_path = model_path.parent / "model_summary.json"
        import json
        with open(summary_path, 'w') as f:
            json.dump(regressor.get_model_summary(), f, indent=2)
        
        return True
        
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        return False


def start_api_server(port=5000):
    """Start the Flask API server."""
    logger = logging.getLogger(__name__)
    
    # Initialize regressor for the API
    initialize_regressor()
    
    # Initialize market data components (price connector and scheduler)
    try:
        initialize_market_data()
    except Exception as e:
        logger.warning(f"Market data initialization failed or is unavailable: {e}")
    
    logger.info(f"Starting Flask API server on port {port}")
    logger.info(f"Demo available at: http://localhost:{port}")
    logger.info(f"API endpoints available at: http://localhost:{port}/api/")
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")


def open_browser(port=5000):
    """Open the demo in the default browser."""
    import webbrowser
    import time
    
    # Give the server a moment to start
    time.sleep(2)
    
    url = f"http://localhost:{port}"
    try:
        webbrowser.open(url)
    except Exception:
        pass  # Browser opening is optional


def main():
    """Main entry point for the demo launcher."""
    parser = argparse.ArgumentParser(
        description="Launch the Crude Assay Regression Demo"
    )
    parser.add_argument(
        '--train-models', 
        action='store_true',
        help='Force retraining of regression models'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port for the Flask server (default: 5000)'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not automatically open browser'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger = logging.getLogger(__name__)
    
    logger.info("=== Crude Assay Regression Demo ===")
    logger.info(f"Project root: {project_root}")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Train or load models
    if not train_models(force_retrain=args.train_models):
        logger.error("Failed to setup models. Exiting.")
        sys.exit(1)
    
    # Start browser (if requested)
    if not args.no_browser:
        import threading
        browser_thread = threading.Thread(target=open_browser, args=(args.port,))
        browser_thread.daemon = True
        browser_thread.start()
    
    # Start the API server
    start_api_server(args.port)


if __name__ == "__main__":
    main()
