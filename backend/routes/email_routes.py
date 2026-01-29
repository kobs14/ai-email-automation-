"""Email listing and detail routes."""

import logging

from flask import Blueprint, jsonify, request

from backend.auth.decorators import jwt_required
from backend.middleware.error_handlers import APIError
from database.connection import get_database
from database.schema import EmailRepository, EntityRepository
from database.queries import emails as email_queries

logger = logging.getLogger(__name__)

email_bp = Blueprint('emails', __name__, url_prefix='/api/emails')


def _serialize_email(email: dict) -> dict:
    """Convert email record to JSON-safe dict."""
    result = {}
    for key, value in email.items():
        if hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


@email_bp.route('', methods=['GET'])
@jwt_required
def list_emails():
    """
    Paginated email list with optional filters.

    Query params:
        page (int): Page number (default 1)
        per_page (int): Items per page (default 20, max 100)
        status (str): Filter by status
        intent (str): Filter by intent
        search (str): Search in from_address and subject
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status = request.args.get('status') or None
    intent = request.args.get('intent') or None
    search = request.args.get('search') or None

    search_pattern = f'%{search}%' if search else None
    offset = (page - 1) * per_page

    db = get_database()

    # Get filtered count
    count_result = db.execute_query(
        email_queries.COUNT_EMAILS_FILTERED,
        params=(status, status, intent, intent, search, search_pattern, search_pattern),
        fetch='one'
    )
    total = count_result['count'] if count_result else 0

    # Get paginated results
    results = db.execute_query(
        email_queries.GET_EMAILS_PAGINATED,
        params=(status, status, intent, intent, search, search_pattern, search_pattern, per_page, offset),
        fetch='all'
    )
    items = [_serialize_email(dict(r)) for r in results] if results else []

    pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return jsonify({
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages,
    }), 200


@email_bp.route('/<int:email_id>', methods=['GET'])
@jwt_required
def get_email(email_id: int):
    """Get email detail with entities and response."""
    db = get_database()
    email_repo = EmailRepository(db)
    entity_repo = EntityRepository(db)

    email = email_repo.get_email_by_id(email_id)
    if not email:
        raise APIError('Email not found', status_code=404)

    entities = entity_repo.get_entities_by_email(email_id)

    # Get associated response
    from database.schema import ResponseRepository
    response_repo = ResponseRepository(db)
    response = response_repo.get_response_for_email(email_id)

    result = _serialize_email(email)
    result['entities'] = [_serialize_email(e) for e in entities]
    result['response'] = _serialize_email(response) if response else None

    return jsonify(result), 200


@email_bp.route('/<int:email_id>/entities', methods=['GET'])
@jwt_required
def get_email_entities(email_id: int):
    """Get extracted entities for an email."""
    db = get_database()
    email_repo = EmailRepository(db)
    entity_repo = EntityRepository(db)

    email = email_repo.get_email_by_id(email_id)
    if not email:
        raise APIError('Email not found', status_code=404)

    entities = entity_repo.get_entities_by_email(email_id)
    items = [_serialize_email(e) for e in entities]

    return jsonify({'items': items}), 200
