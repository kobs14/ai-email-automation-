"""Health check endpoint."""

import logging

import redis
from flask import Blueprint, jsonify

from config.settings import get_settings
from database.connection import get_database

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__, url_prefix="/api/health")


@health_bp.route("", methods=["GET"])
def health_check():
    """
    Check database and Redis connectivity.

    Returns JSON with status of each dependency.
    """
    settings = get_settings()
    checks = {
        "database": False,
        "redis": False,
    }

    # Check database
    try:
        db = get_database()
        checks["database"] = db.is_connected()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    try:
        r = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            password=settings.redis.password,
            socket_connect_timeout=2,
        )
        r.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return jsonify(
        {
            "status": "healthy" if all_healthy else "degraded",
            "checks": checks,
        }
    ), status_code
