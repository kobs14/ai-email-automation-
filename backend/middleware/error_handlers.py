"""Global error handlers and APIError exception class."""

import logging
import traceback

from flask import Flask, jsonify

logger = logging.getLogger(__name__)


class APIError(Exception):
    """
    Custom API exception that renders as JSON.

    Usage:
        raise APIError('Not found', status_code=404)
        raise APIError('Validation failed', status_code=400, details={'field': 'error'})
    """

    def __init__(
        self,
        message: str = 'Internal server error',
        status_code: int = 500,
        details: dict = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers on the Flask app.

    Args:
        app: Flask application instance
    """

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        response = {
            'error': error.message,
            'status': error.status_code,
        }
        if error.details:
            response['details'] = error.details
        return jsonify(response), error.status_code

    @app.errorhandler(400)
    def handle_bad_request(error):
        return jsonify({
            'error': 'Bad request',
            'status': 400,
        }), 400

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            'error': 'Resource not found',
            'status': 404,
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            'error': 'Method not allowed',
            'status': 405,
        }), 405

    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error(f"Internal server error: {error}\n{traceback.format_exc()}")
        return jsonify({
            'error': 'Internal server error',
            'status': 500,
        }), 500
