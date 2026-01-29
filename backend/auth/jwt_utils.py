"""JWT token creation and verification utilities."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import jwt

from config.settings import get_settings

logger = logging.getLogger(__name__)


def create_access_token(user_id: int, username: str, role: str) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User's database ID
        username: User's username
        role: User's role (admin, operator, viewer)

    Returns:
        Encoded JWT string
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'username': username,
        'role': role,
        'type': 'access',
        'iat': now,
        'exp': now + timedelta(seconds=settings.flask.jwt_access_token_expires),
    }
    return jwt.encode(payload, settings.flask.jwt_secret_key, algorithm='HS256')


def create_refresh_token(user_id: int) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User's database ID

    Returns:
        Encoded JWT string
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'type': 'refresh',
        'iat': now,
        'exp': now + timedelta(seconds=settings.flask.jwt_refresh_token_expires),
    }
    return jwt.encode(payload, settings.flask.jwt_secret_key, algorithm='HS256')


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.

    Args:
        token: Encoded JWT string

    Returns:
        Decoded payload dict, or None if invalid/expired
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.flask.jwt_secret_key,
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None


def get_token_remaining_ttl(token: str) -> int:
    """
    Get the remaining TTL in seconds for a token.

    Args:
        token: Encoded JWT string

    Returns:
        Remaining seconds until expiry, or 0 if expired/invalid
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.flask.jwt_secret_key,
            algorithms=['HS256'],
            options={'verify_exp': False}
        )
        exp = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        remaining = int((exp - now).total_seconds())
        return max(remaining, 0)
    except jwt.InvalidTokenError:
        return 0
