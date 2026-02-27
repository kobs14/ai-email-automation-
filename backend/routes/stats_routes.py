"""Statistics routes for dashboard."""

import logging

from flask import Blueprint, jsonify, request

from backend.auth.decorators import jwt_required
from database.connection import get_database
from database.queries import stats as stats_queries

logger = logging.getLogger(__name__)

stats_bp = Blueprint("stats", __name__, url_prefix="/api/stats")


@stats_bp.route("/overview", methods=["GET"])
@jwt_required
def overview():
    """
    Get dashboard overview statistics.

    Returns email counts by status, response counts by status,
    and upcoming event count.
    """
    db = get_database()

    email_counts = db.execute_query(stats_queries.COUNT_EMAILS_BY_STATUS, fetch="all")
    response_counts = db.execute_query(stats_queries.COUNT_RESPONSES_BY_STATUS, fetch="all")
    upcoming = db.execute_query(stats_queries.COUNT_UPCOMING_EVENTS, fetch="one")

    return jsonify(
        {
            "email_counts": {r["status"]: r["count"] for r in email_counts} if email_counts else {},
            "response_counts": {r["status"]: r["count"] for r in response_counts} if response_counts else {},
            "upcoming_events": upcoming["count"] if upcoming else 0,
        }
    ), 200


@stats_bp.route("/intents", methods=["GET"])
@jwt_required
def intents():
    """Get email counts grouped by intent."""
    db = get_database()

    results = db.execute_query(stats_queries.COUNT_EMAILS_BY_INTENT, fetch="all")

    items = [{"intent": r["intent"], "count": r["count"]} for r in results] if results else []

    return jsonify({"items": items}), 200


@stats_bp.route("/processing", methods=["GET"])
@jwt_required
def processing_timeline():
    """
    Get daily email processing timeline.

    Query params:
        days (int): Number of days to look back (default 7, max 90)
    """
    days = min(request.args.get("days", 7, type=int), 90)

    db = get_database()

    query = """
        SELECT
            date_trunc('day', received_at)::date as date,
            COUNT(*) as received,
            COUNT(*) FILTER (WHERE status IN ('classified', 'responded')) as processed,
            COUNT(*) FILTER (WHERE status = 'responded') as responded
        FROM emails
        WHERE received_at >= CURRENT_DATE - INTERVAL '1 day' * %s
        GROUP BY date_trunc('day', received_at)::date
        ORDER BY date ASC;
    """

    results = db.execute_query(query, params=(days,), fetch="all")

    items = (
        [
            {
                "date": r["date"].isoformat() if r["date"] else None,
                "received": r["received"],
                "processed": r["processed"],
                "responded": r["responded"],
            }
            for r in results
        ]
        if results
        else []
    )

    return jsonify({"items": items, "days": days}), 200
