"""Authentication and authorization decorators for Flask routes."""

import logging
from functools import wraps
from typing import Tuple

import redis
from flask import g, request

from backend.auth.jwt_utils import decode_token
from backend.middleware.error_handlers import APIError
from config.settings import get_settings

logger = logging.getLogger(__name__)


def _get_redis_client() -> redis.Redis:
    """Get Redis client for token blacklist checks."""
    settings = get_settings()
    return redis.Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        db=settings.redis.db,
        password=settings.redis.password,
        decode_responses=True,
    )


def _extract_token() -> Tuple[str, dict]:
    """
    Extract and validate JWT from Authorization header.

    Returns:
        Tuple of (raw_token_string, decoded_payload)

    Raises:
        APIError: If token is missing, invalid, or blacklisted
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise APIError("Missing or invalid Authorization header", status_code=401)

    token = auth_header[7:]
    payload = decode_token(token)
    if payload is None:
        raise APIError("Invalid or expired token", status_code=401)

    if payload.get("type") != "access":
        raise APIError("Invalid token type", status_code=401)

    # Check token blacklist
    try:
        r = _get_redis_client()
        if r.exists(f"token_blacklist:{token}"):
            raise APIError("Token has been revoked", status_code=401)
    except redis.ConnectionError:
        logger.warning("Redis unavailable for token blacklist check")

    return token, payload


def jwt_required(f):
    """
    Decorator that requires a valid JWT access token.

    Sets g.current_user with {id, username, role} from the token.
    Sets g.raw_token with the raw token string.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token, payload = _extract_token()
        g.current_user = {
            "id": int(payload["sub"]),
            "username": payload["username"],
            "role": payload["role"],
        }
        g.raw_token = token
        return f(*args, **kwargs)

    return decorated


def role_required(*roles):
    """
    Decorator that requires the authenticated user to have one of the specified roles.

    Must be used after @jwt_required.

    Args:
        *roles: Allowed role names (e.g., 'admin', 'operator')

    Usage:
        @app.route('/admin-only')
        @jwt_required
        @role_required('admin')
        def admin_view():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token, payload = _extract_token()
            g.current_user = {
                "id": int(payload["sub"]),
                "username": payload["username"],
                "role": payload["role"],
            }
            g.raw_token = token

            if payload["role"] not in roles:
                raise APIError("Insufficient permissions", status_code=403)
            return f(*args, **kwargs)

        return decorated

    return decorator
