"""
SQL queries for dashboard statistics.

All queries use parameterized placeholders (%s) to prevent SQL injection.
Always pass user input through the params argument, never concatenate strings.
"""

# =============================================================================
# Overview Statistics
# =============================================================================

COUNT_EMAILS_BY_STATUS = """
    SELECT status, COUNT(*) as count
    FROM emails
    GROUP BY status;
"""

COUNT_RESPONSES_BY_STATUS = """
    SELECT status, COUNT(*) as count
    FROM responses
    GROUP BY status;
"""

COUNT_UPCOMING_EVENTS = """
    SELECT COUNT(*) as count
    FROM calendar_events
    WHERE start_time >= NOW();
"""

# =============================================================================
# Intent Distribution
# =============================================================================

COUNT_EMAILS_BY_INTENT = """
    SELECT
        COALESCE(intent, 'unclassified') as intent,
        COUNT(*) as count
    FROM emails
    GROUP BY intent
    ORDER BY count DESC;
"""

# =============================================================================
# Processing Timeline
# =============================================================================

DAILY_EMAIL_COUNTS = """
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

# =============================================================================
# Response Statistics
# =============================================================================

AVERAGE_RESPONSE_TIME = """
    SELECT
        AVG(EXTRACT(EPOCH FROM (r.generated_at - e.received_at))) as avg_seconds
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    WHERE r.generated_at IS NOT NULL
    AND e.received_at IS NOT NULL;
"""

RESPONSES_BY_DAY = """
    SELECT
        date_trunc('day', generated_at)::date as date,
        COUNT(*) as count,
        COUNT(*) FILTER (WHERE status = 'sent') as sent,
        COUNT(*) FILTER (WHERE status = 'failed') as failed
    FROM responses
    WHERE generated_at >= CURRENT_DATE - INTERVAL '1 day' * %s
    GROUP BY date_trunc('day', generated_at)::date
    ORDER BY date ASC;
"""
