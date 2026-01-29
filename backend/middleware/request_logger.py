"""Structured request logging middleware."""

import logging
import time
import uuid

from flask import Flask, g, request

logger = logging.getLogger(__name__)


def register_request_logger(app: Flask) -> None:
    """
    Register request logging hooks on the Flask app.

    Logs each request with a correlation ID, method, path,
    status code, and duration.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def before_request():
        g.request_id = str(uuid.uuid4())[:8]
        g.request_start = time.time()

    @app.after_request
    def after_request(response):
        duration_ms = (time.time() - g.get('request_start', time.time())) * 1000
        logger.info(
            "request_id=%s method=%s path=%s status=%d duration=%.1fms",
            g.get('request_id', '-'),
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        response.headers['X-Request-ID'] = g.get('request_id', '')
        return response
