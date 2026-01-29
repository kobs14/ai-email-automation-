"""Response management routes: list, detail, approve, reject, edit, retry."""

import logging

from flask import Blueprint, g, jsonify, request

from backend.auth.decorators import jwt_required, role_required
from backend.middleware.error_handlers import APIError
from backend.schemas.response_schemas import validate_response_content
from database.connection import get_database
from database.schema import ResponseRepository, EmailRepository, EntityRepository
from database.queries import emails as email_queries

logger = logging.getLogger(__name__)

response_bp = Blueprint('responses', __name__, url_prefix='/api/responses')


def _serialize(record: dict) -> dict:
    """Convert record to JSON-safe dict."""
    result = {}
    for key, value in record.items():
        if hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


@response_bp.route('', methods=['GET'])
@jwt_required
def list_responses():
    """
    Paginated response list with optional status filter.

    Query params:
        page (int): Page number (default 1)
        per_page (int): Items per page (default 20, max 100)
        status (str): Filter by status
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status_filter = request.args.get('status') or None
    offset = (page - 1) * per_page

    db = get_database()

    count_result = db.execute_query(
        email_queries.COUNT_RESPONSES_FILTERED,
        params=(status_filter, status_filter),
        fetch='one'
    )
    total = count_result['count'] if count_result else 0

    results = db.execute_query(
        email_queries.GET_RESPONSES_PAGINATED,
        params=(status_filter, status_filter, per_page, offset),
        fetch='all'
    )
    items = [_serialize(dict(r)) for r in results] if results else []

    pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return jsonify({
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages,
    }), 200


@response_bp.route('/pending', methods=['GET'])
@jwt_required
def pending_responses():
    """Get pending draft responses with email context."""
    db = get_database()
    response_repo = ResponseRepository(db)
    drafts = response_repo.get_pending_drafts()
    return jsonify({'items': [_serialize(d) for d in drafts]}), 200


@response_bp.route('/failed', methods=['GET'])
@jwt_required
def failed_responses():
    """Get failed responses."""
    db = get_database()
    response_repo = ResponseRepository(db)
    limit = request.args.get('limit', 50, type=int)
    failed = response_repo.get_failed_responses(limit=limit)
    return jsonify({'items': [_serialize(f) for f in failed]}), 200


@response_bp.route('/<int:response_id>', methods=['GET'])
@jwt_required
def get_response(response_id: int):
    """Get response detail with associated email and entities."""
    db = get_database()
    response_repo = ResponseRepository(db)

    response = response_repo.get_response_with_email(response_id)
    if not response:
        raise APIError('Response not found', status_code=404)

    # Also get entities
    entity_repo = EntityRepository(db)
    entities = entity_repo.get_entities_by_email(response['email_id'])

    result = _serialize(response)
    result['entities'] = [_serialize(e) for e in entities]

    return jsonify(result), 200


@response_bp.route('/<int:response_id>/content', methods=['PUT'])
@role_required('admin', 'operator')
def update_response_content(response_id: int):
    """Update draft response content."""
    data = request.get_json(silent=True)
    is_valid, errors = validate_response_content(data)
    if not is_valid:
        raise APIError('Validation failed', status_code=400, details={'errors': errors})

    db = get_database()
    response_repo = ResponseRepository(db)

    response = response_repo.get_response_by_id(response_id)
    if not response:
        raise APIError('Response not found', status_code=404)

    if response['status'] not in ('draft', 'rejected'):
        raise APIError(
            'Only draft or rejected responses can be edited',
            status_code=400
        )

    success = response_repo.update_content(response_id, data['content'].strip())
    if not success:
        raise APIError('Failed to update response content', status_code=500)

    return jsonify({'message': 'Response content updated'}), 200


@response_bp.route('/<int:response_id>/approve', methods=['POST'])
@role_required('admin', 'operator')
def approve_response(response_id: int):
    """Approve a response draft."""
    db = get_database()
    response_repo = ResponseRepository(db)

    response = response_repo.get_response_by_id(response_id)
    if not response:
        raise APIError('Response not found', status_code=404)

    if response['status'] != 'draft':
        raise APIError(
            f"Cannot approve response with status '{response['status']}'",
            status_code=400
        )

    username = g.current_user['username']
    success = response_repo.approve_response(response_id, approved_by=username)
    if not success:
        raise APIError('Failed to approve response', status_code=500)

    return jsonify({'message': 'Response approved'}), 200


@response_bp.route('/<int:response_id>/reject', methods=['POST'])
@role_required('admin', 'operator')
def reject_response(response_id: int):
    """Reject a response draft."""
    db = get_database()
    response_repo = ResponseRepository(db)

    response = response_repo.get_response_by_id(response_id)
    if not response:
        raise APIError('Response not found', status_code=404)

    if response['status'] != 'draft':
        raise APIError(
            f"Cannot reject response with status '{response['status']}'",
            status_code=400
        )

    success = response_repo.reject_response(response_id)
    if not success:
        raise APIError('Failed to reject response', status_code=500)

    return jsonify({'message': 'Response rejected'}), 200


@response_bp.route('/<int:response_id>/retry', methods=['POST'])
@role_required('admin', 'operator')
def retry_response(response_id: int):
    """Reset a failed response for retry."""
    db = get_database()
    response_repo = ResponseRepository(db)

    response = response_repo.get_response_by_id(response_id)
    if not response:
        raise APIError('Response not found', status_code=404)

    if response['status'] != 'failed':
        raise APIError(
            'Only failed responses can be retried',
            status_code=400
        )

    success = response_repo.reset_for_retry(response_id)
    if not success:
        raise APIError('Failed to reset response for retry', status_code=500)

    return jsonify({'message': 'Response reset for retry'}), 200
