"""
Flask application for Crude Assay.

Entry point: create_app(), run via `python app.py` or `uv run python app.py`.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# src layout: domain_pkg lives under ./src
_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

logger = logging.getLogger(__name__)

from core.error_handlers import register_error_handlers
from core.logging import setup_logging

from routes.api.v1 import assay_api_bp
from routes.web import main_web_bp, assay_web_bp, genie_web_bp

try:
    from routes.websocket_routes import register_websocket_events
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("WebSocket routes not available")

logging.basicConfig(level=logging.INFO)
try:
    setup_logging()
except Exception as e:
    logger.debug("setup_logging failed: %s", e, exc_info=True)


class AppContext:
    """Container for application-level state and services."""

    def __init__(self):
        self.socketio: Optional[SocketIO] = None
        self.streaming_service: Optional[object] = None
        self.spark_services_initialized: bool = False


app_context = AppContext()


def _cors_allowed_origins() -> str | list[str]:
    """
    CORS allowed origins for SocketIO/API.
    In debug mode allow all; in production use CORS_ALLOWED_ORIGINS (comma-separated).
    """
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    if debug:
        return '*'
    raw = os.environ.get('CORS_ALLOWED_ORIGINS', '').strip()
    origins = [o.strip() for o in raw.split(',') if o.strip()]
    return origins if origins else []


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    logger.info("Creating Flask application...")
    cors_origins = _cors_allowed_origins()
    if cors_origins == '*':
        CORS(app, origins='*')
    elif cors_origins:
        CORS(app, origins=cors_origins)
    # else: production with no CORS_ALLOWED_ORIGINS → same-origin only (no CORS headers)
    register_error_handlers(app)
    logger.info("Error handlers registered")

    try:
        app.register_blueprint(assay_api_bp)
        logger.info("API routes registered")
    except Exception as e:
        logger.error("Failed to register API routes: %s", e)

    @app.route('/api')
    def api_info() -> dict:
        """API information endpoint."""
        return {
            'name': 'Crude Assay API',
            'version': '2.0.0',
            'description': 'Crude assay data and analytics',
            'endpoints': {'health': '/health', 'assay': '/api/v1/assay'},
        }

    web_blueprints = [
        (main_web_bp, "Main Web"),
        (assay_web_bp, "Assay Web"),
        (genie_web_bp, "Genie chat"),
    ]
    for blueprint, name in web_blueprints:
        try:
            app.register_blueprint(blueprint)
            logger.info("%s registered", name)
        except Exception as e:
            logger.error("Failed to register %s: %s", name, e)

    try:
        app_context.socketio = SocketIO(
            app,
            cors_allowed_origins=cors_origins,
            async_mode=None,
            logger=False,
            engineio_logger=False
        )
        if WEBSOCKET_AVAILABLE:
            register_websocket_events(app_context.socketio)
            logger.info("SocketIO initialized with WebSocket events")
        else:
            logger.warning("SocketIO initialized; WebSocket routes not available")
    except Exception as e:
        logger.warning("SocketIO initialization failed: %s", e)
        class MockSocketIO:
            def run(self, app, **kwargs):
                app.run(**kwargs)
        app_context.socketio = MockSocketIO()

    app.socketio = app_context.socketio

    @app.route('/health')
    def health() -> dict:
        """Global health check endpoint."""
        return {
            'status': 'healthy',
            'version': '2.0',
            'message': 'Application is running'
        }

    logger.info("Flask application created successfully")
    return app


def run_app(host: str = '0.0.0.0', port: int = 4242, debug: bool = False) -> None:
    """Run the Flask application."""
    app = create_app()
    logger.info("Starting server on %s:%s", host, port)
    logger.info("Debug mode: %s", debug)
    app_context.socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )


if __name__ == "__main__":
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 8888))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    run_app(host=host, port=port, debug=debug)
