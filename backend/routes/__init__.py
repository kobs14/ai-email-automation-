"""Flask route blueprints for the REST API."""

from .auth_routes import auth_bp
from .calendar_routes import calendar_bp
from .config_routes import config_bp
from .email_routes import email_bp
from .health_routes import health_bp
from .response_routes import response_bp
from .stats_routes import stats_bp

ALL_BLUEPRINTS = [
    auth_bp,
    health_bp,
    email_bp,
    response_bp,
    stats_bp,
    calendar_bp,
    config_bp,
]
