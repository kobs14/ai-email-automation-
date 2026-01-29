"""
SQL queries for the calendar_events and calendar_sync_state tables.

All queries use parameterized placeholders (%s) to prevent SQL injection.
Always pass user input through the params argument, never concatenate strings.
"""

# =============================================================================
# INSERT Queries
# =============================================================================

INSERT_CALENDAR_EVENT = """
    INSERT INTO calendar_events (
        google_event_id,
        response_id,
        title,
        description,
        location,
        start_time,
        end_time,
        customer_name,
        customer_phone,
        service_type,
        source,
        google_updated_at,
        synced_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id, google_event_id, created_at;
"""

# =============================================================================
# UPDATE Queries
# =============================================================================

UPDATE_CALENDAR_EVENT = """
    UPDATE calendar_events
    SET title = %s,
        description = %s,
        location = %s,
        start_time = %s,
        end_time = %s,
        google_updated_at = %s,
        synced_at = %s,
        updated_at = NOW()
    WHERE google_event_id = %s
    RETURNING id, google_event_id;
"""

UPDATE_RESPONSE_CALENDAR_STATUS = """
    UPDATE responses
    SET calendar_event_id = %s,
        calendar_status = %s
    WHERE id = %s
    RETURNING id, calendar_event_id, calendar_status;
"""

UPDATE_RESPONSE_CALENDAR_CONFLICT = """
    UPDATE responses
    SET calendar_status = 'conflict',
        calendar_conflict_details = %s
    WHERE id = %s
    RETURNING id, calendar_status;
"""

UPDATE_RESPONSE_CALENDAR_FAILED = """
    UPDATE responses
    SET calendar_status = 'failed'
    WHERE id = %s
    RETURNING id, calendar_status;
"""

# =============================================================================
# SELECT Queries - Single Row
# =============================================================================

GET_CALENDAR_EVENT_BY_ID = """
    SELECT
        id,
        google_event_id,
        response_id,
        title,
        description,
        location,
        start_time,
        end_time,
        customer_name,
        customer_phone,
        service_type,
        source,
        google_updated_at,
        synced_at,
        created_at,
        updated_at
    FROM calendar_events
    WHERE id = %s;
"""

GET_CALENDAR_EVENT_BY_GOOGLE_ID = """
    SELECT
        id,
        google_event_id,
        response_id,
        title,
        description,
        location,
        start_time,
        end_time,
        customer_name,
        customer_phone,
        service_type,
        source,
        google_updated_at,
        synced_at,
        created_at,
        updated_at
    FROM calendar_events
    WHERE google_event_id = %s;
"""

GET_CALENDAR_EVENT_BY_RESPONSE_ID = """
    SELECT
        id,
        google_event_id,
        response_id,
        title,
        description,
        location,
        start_time,
        end_time,
        customer_name,
        service_type,
        source,
        created_at
    FROM calendar_events
    WHERE response_id = %s
    ORDER BY created_at DESC
    LIMIT 1;
"""

# =============================================================================
# SELECT Queries - Multiple Rows
# =============================================================================

GET_UPCOMING_CALENDAR_EVENTS = """
    SELECT
        ce.id,
        ce.google_event_id,
        ce.response_id,
        ce.title,
        ce.location,
        ce.start_time,
        ce.end_time,
        ce.customer_name,
        ce.service_type,
        ce.source
    FROM calendar_events ce
    WHERE ce.start_time >= NOW()
    ORDER BY ce.start_time ASC
    LIMIT %s;
"""

GET_CALENDAR_EVENTS_IN_RANGE = """
    SELECT
        ce.id,
        ce.google_event_id,
        ce.response_id,
        ce.title,
        ce.location,
        ce.start_time,
        ce.end_time,
        ce.customer_name,
        ce.service_type,
        ce.source
    FROM calendar_events ce
    WHERE ce.start_time >= %s
    AND ce.start_time <= %s
    ORDER BY ce.start_time ASC;
"""

GET_MANUAL_EVENTS = """
    SELECT
        id,
        google_event_id,
        title,
        location,
        start_time,
        end_time,
        customer_name,
        service_type,
        created_at
    FROM calendar_events
    WHERE source = 'manual'
    ORDER BY created_at DESC
    LIMIT %s;
"""

# =============================================================================
# SELECT Queries - Response Calendar Status
# =============================================================================

GET_RESPONSES_PENDING_CALENDAR = """
    SELECT
        r.id,
        r.email_id,
        r.calendar_status,
        r.calendar_event_id,
        e.from_address,
        e.subject
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    WHERE r.status = 'sent'
    AND r.calendar_status = 'pending'
    ORDER BY r.sent_at ASC
    LIMIT %s;
"""

# =============================================================================
# Sync State Queries
# =============================================================================

GET_SYNC_STATE = """
    SELECT
        id,
        last_sync_token,
        last_sync_at,
        updated_at
    FROM calendar_sync_state
    WHERE id = 1;
"""

UPDATE_SYNC_STATE = """
    UPDATE calendar_sync_state
    SET last_sync_token = %s,
        last_sync_at = %s,
        updated_at = NOW()
    WHERE id = 1
    RETURNING id, last_sync_at;
"""

# =============================================================================
# DELETE Queries
# =============================================================================

DELETE_CALENDAR_EVENT = """
    DELETE FROM calendar_events
    WHERE id = %s
    RETURNING id, google_event_id;
"""

DELETE_CALENDAR_EVENT_BY_GOOGLE_ID = """
    DELETE FROM calendar_events
    WHERE google_event_id = %s
    RETURNING id;
"""

# =============================================================================
# COUNT Queries
# =============================================================================

COUNT_UPCOMING_EVENTS = """
    SELECT COUNT(*) as count
    FROM calendar_events
    WHERE start_time >= NOW();
"""

COUNT_EVENTS_BY_SOURCE = """
    SELECT source, COUNT(*) as count
    FROM calendar_events
    GROUP BY source;
"""
