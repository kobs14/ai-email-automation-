"""Authentication routes: login, refresh, logout, me."""

import logging

import redis
from flask import Blueprint, g, jsonify, request

from backend.auth.decorators import jwt_required
from backend.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_remaining_ttl,
)
from backend.auth.password import verify_password
from backend.middleware.error_handlers import APIError
from backend.schemas.auth_schemas import validate_login
from config.settings import get_settings
from database.connection import get_database
from database.schema import UserRepository

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _get_user_repo() -> UserRepository:
    """Get UserRepository instance."""
    return UserRepository(get_database())


def _get_redis_client() -> redis.Redis:
    """Get Redis client."""
    settings = get_settings()
    return redis.Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        db=settings.redis.db,
        password=settings.redis.password,
        decode_responses=True,
    )


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT tokens.

    Request body:
        {"username": "...", "password": "..."}

    Returns:
        {"access_token": "...", "refresh_token": "...", "user": {...}}
    """
    data = request.get_json(silent=True)
    is_valid, errors = validate_login(data)
    if not is_valid:
        raise APIError('Validation failed', status_code=400, details={'errors': errors})

    username = data['username'].strip()
    password = data['password']

    user_repo = _get_user_repo()
    user = user_repo.get_user_by_username(username)

    if not user:
        raise APIError('Invalid username or password', status_code=401)

    if not user['is_active']:
        raise APIError('Account is deactivated', status_code=403)

    if not verify_password(password, user['password_hash']):
        raise APIError('Invalid username or password', status_code=401)

    # Update last login
    user_repo.update_last_login(user['id'])

    access_token = create_access_token(user['id'], user['username'], user['role'])
    refresh_token = create_refresh_token(user['id'])

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role'],
        },
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Refresh an access token using a valid refresh token.

    Request body:
        {"refresh_token": "..."}

    Returns:
        {"access_token": "..."}
    """
    data = request.get_json(silent=True)
    if not data or 'refresh_token' not in data:
        raise APIError('Refresh token is required', status_code=400)

    token = data['refresh_token']
    payload = decode_token(token)

    if payload is None:
        raise APIError('Invalid or expired refresh token', status_code=401)

    if payload.get('type') != 'refresh':
        raise APIError('Invalid token type', status_code=401)

    # Check blacklist
    try:
        r = _get_redis_client()
        if r.exists(f'token_blacklist:{token}'):
            raise APIError('Token has been revoked', status_code=401)
    except redis.ConnectionError:
        logger.warning("Redis unavailable for token blacklist check")

    # Fetch user to get current role
    user_repo = _get_user_repo()
    user = user_repo.get_user_by_id(int(payload['sub']))

    if not user or not user['is_active']:
        raise APIError('User not found or deactivated', status_code=401)

    access_token = create_access_token(user['id'], user['username'], user['role'])

    return jsonify({
        'access_token': access_token,
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required
def logout():
    """
    Logout by blacklisting the current access token in Redis.
    """
    token = g.raw_token
    ttl = get_token_remaining_ttl(token)

    if ttl > 0:
        try:
            r = _get_redis_client()
            r.setex(f'token_blacklist:{token}', ttl, '1')
        except redis.ConnectionError:
            logger.warning("Redis unavailable for token blacklist")

    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required
def me():
    """
    Return current authenticated user info.
    """
    user_repo = _get_user_repo()
    user = user_repo.get_user_by_id(g.current_user['id'])

    if not user:
        raise APIError('User not found', status_code=404)

    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'role': user['role'],
        'last_login_at': user['last_login_at'].isoformat() if user['last_login_at'] else None,
        'created_at': user['created_at'].isoformat() if user['created_at'] else None,
    }), 200
