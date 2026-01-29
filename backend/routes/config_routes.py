"""Business configuration routes."""

import json
import logging

from flask import Blueprint, jsonify, request

from backend.auth.decorators import jwt_required, role_required
from backend.middleware.error_handlers import APIError
from backend.schemas.config_schemas import validate_config_update
from database.connection import get_database
from database.schema import ConfigRepository

logger = logging.getLogger(__name__)

config_bp = Blueprint('config', __name__, url_prefix='/api/config')


@config_bp.route('', methods=['GET'])
@jwt_required
def get_all_config():
    """Get all configuration values."""
    db = get_database()
    config_repo = ConfigRepository(db)

    all_config = config_repo.get_all_config()
    return jsonify({'items': all_config}), 200


@config_bp.route('/<string:key>', methods=['GET'])
@jwt_required
def get_config(key: str):
    """Get a specific configuration value."""
    db = get_database()
    config_repo = ConfigRepository(db)

    value = config_repo.get_config(key, use_cache=False)
    if value is None:
        raise APIError(f"Config key '{key}' not found", status_code=404)

    return jsonify({'key': key, 'value': value}), 200


@config_bp.route('/<string:key>', methods=['PUT'])
@role_required('admin')
def update_config(key: str):
    """
    Update a configuration value. Admin only.

    Request body:
        {"value": <any JSON value>}
    """
    data = request.get_json(silent=True)
    is_valid, errors = validate_config_update(data)
    if not is_valid:
        raise APIError('Validation failed', status_code=400, details={'errors': errors})

    db = get_database()
    config_repo = ConfigRepository(db)

    if not config_repo.config_exists(key):
        raise APIError(f"Config key '{key}' not found", status_code=404)

    value = data['value']
    if not isinstance(value, dict):
        value = {'value': value}

    success = config_repo.set_config(key, value)
    if not success:
        raise APIError('Failed to update config', status_code=500)

    return jsonify({'message': f"Config '{key}' updated", 'key': key}), 200
