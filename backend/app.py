"""Flask application factory."""

import logging

from flask import Flask
from flask_cors import CORS

from config.settings import get_settings

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns:
        Configured Flask app instance
    """
    settings = get_settings()

    app = Flask(__name__)
    app.config['SECRET_KEY'] = settings.flask.secret_key
    app.config['JSON_SORT_KEYS'] = False

    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": [settings.flask.frontend_url],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
        }
    })

    # Register middleware
    from backend.middleware.error_handlers import register_error_handlers
    from backend.middleware.request_logger import register_request_logger
    from backend.middleware.rate_limiter import register_rate_limiter

    register_error_handlers(app)
    register_request_logger(app)
    register_rate_limiter(app)

    # Register blueprints
    from backend.routes import ALL_BLUEPRINTS
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)

    logger.info("Flask application created with %d blueprints", len(ALL_BLUEPRINTS))
    return app
