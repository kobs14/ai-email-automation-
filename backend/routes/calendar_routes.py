"""Calendar event routes."""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from backend.auth.decorators import jwt_required
from backend.middleware.error_handlers import APIError
from database.connection import get_database
from database.queries import calendar as calendar_queries

logger = logging.getLogger(__name__)

calendar_bp = Blueprint('calendar', __name__, url_prefix='/api/calendar')


def _serialize_event(event: dict) -> dict:
    """Convert calendar event record to JSON-safe dict."""
    result = {}
    for key, value in event.items():
        if hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


@calendar_bp.route('/events', methods=['GET'])
@jwt_required
def list_events():
    """
    Get calendar events with optional date range filter.

    Query params:
        start (str): Start date ISO format (default: now)
        end (str): End date ISO format
    """
    db = get_database()

    start = request.args.get('start')
    end = request.args.get('end')

    if start and end:
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
        except ValueError:
            raise APIError('Invalid date format. Use ISO 8601.', status_code=400)

        results = db.execute_query(
            calendar_queries.GET_CALENDAR_EVENTS_IN_RANGE,
            params=(start_dt, end_dt),
            fetch='all'
        )
    else:
        results = db.execute_query(
            calendar_queries.GET_UPCOMING_CALENDAR_EVENTS,
            params=(100,),
            fetch='all'
        )

    items = [_serialize_event(dict(r)) for r in results] if results else []
    return jsonify({'items': items}), 200


@calendar_bp.route('/events/upcoming', methods=['GET'])
@jwt_required
def upcoming_events():
    """
    Get next N upcoming events.

    Query params:
        limit (int): Number of events (default 10, max 50)
    """
    limit = min(request.args.get('limit', 10, type=int), 50)
    db = get_database()

    results = db.execute_query(
        calendar_queries.GET_UPCOMING_CALENDAR_EVENTS,
        params=(limit,),
        fetch='all'
    )
    items = [_serialize_event(dict(r)) for r in results] if results else []
    return jsonify({'items': items}), 200


@calendar_bp.route('/events/<int:event_id>', methods=['GET'])
@jwt_required
def get_event(event_id: int):
    """Get a single calendar event by ID."""
    db = get_database()

    result = db.execute_query(
        calendar_queries.GET_CALENDAR_EVENT_BY_ID,
        params=(event_id,),
        fetch='one'
    )
    if not result:
        raise APIError('Event not found', status_code=404)

    return jsonify(_serialize_event(dict(result))), 200
