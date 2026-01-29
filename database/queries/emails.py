"""
SQL queries for the emails table.

All queries use parameterized placeholders (%s) to prevent SQL injection.
Always pass user input through the params argument, never concatenate strings.
"""

# =============================================================================
# INSERT Queries
# =============================================================================

INSERT_EMAIL = """
    INSERT INTO emails (
        message_id,
        from_address,
        subject,
        body,
        received_at,
        raw_headers
    ) VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id, message_id, created_at;
"""

INSERT_EMAIL_FULL = """
    INSERT INTO emails (
        message_id,
        from_address,
        subject,
        body,
        received_at,
        status,
        intent,
        priority,
        raw_headers
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id, message_id, status, created_at;
"""

# =============================================================================
# UPDATE Queries
# =============================================================================

UPDATE_EMAIL_STATUS = """
    UPDATE emails
    SET status = %s,
        processed_at = CURRENT_TIMESTAMP
    WHERE id = %s
    RETURNING id, status, processed_at;
"""

UPDATE_EMAIL_INTENT = """
    UPDATE emails
    SET intent = %s,
        status = 'classified'
    WHERE id = %s
    RETURNING id, intent, status;
"""

UPDATE_EMAIL_STATUS_AND_INTENT = """
    UPDATE emails
    SET status = %s,
        intent = %s,
        processed_at = CURRENT_TIMESTAMP
    WHERE id = %s
    RETURNING id, status, intent, processed_at;
"""

UPDATE_EMAIL_PRIORITY = """
    UPDATE emails
    SET priority = %s
    WHERE id = %s
    RETURNING id, priority;
"""

MARK_EMAIL_FAILED = """
    UPDATE emails
    SET status = 'failed',
        processed_at = CURRENT_TIMESTAMP
    WHERE id = %s
    RETURNING id, status;
"""

MARK_EMAIL_RESPONDED = """
    UPDATE emails
    SET status = 'responded',
        processed_at = CURRENT_TIMESTAMP
    WHERE id = %s
    RETURNING id, status, processed_at;
"""

# =============================================================================
# SELECT Queries - Single Row
# =============================================================================

GET_EMAIL_BY_ID = """
    SELECT
        id,
        message_id,
        from_address,
        subject,
        body,
        received_at,
        processed_at,
        status,
        intent,
        priority,
        raw_headers,
        created_at,
        updated_at
    FROM emails
    WHERE id = %s;
"""

GET_EMAIL_BY_MESSAGE_ID = """
    SELECT
        id,
        message_id,
        from_address,
        subject,
        body,
        received_at,
        processed_at,
        status,
        intent,
        priority,
        raw_headers,
        created_at,
        updated_at
    FROM emails
    WHERE message_id = %s;
"""

EMAIL_EXISTS_BY_MESSAGE_ID = """
    SELECT EXISTS(
        SELECT 1 FROM emails WHERE message_id = %s
    ) AS exists;
"""

GET_EMAIL_BY_GMAIL_ID = """
    SELECT
        id,
        message_id,
        from_address,
        subject,
        status,
        intent,
        raw_headers
    FROM emails
    WHERE raw_headers->>'gmail_id' = %s;
"""

EMAIL_EXISTS_BY_GMAIL_ID = """
    SELECT EXISTS(
        SELECT 1 FROM emails WHERE raw_headers->>'gmail_id' = %s
    ) AS exists;
"""

# =============================================================================
# SELECT Queries - Multiple Rows
# =============================================================================

GET_PENDING_EMAILS = """
    SELECT
        id,
        message_id,
        from_address,
        subject,
        body,
        received_at,
        status,
        intent
    FROM emails
    WHERE status = 'pending'
    ORDER BY priority DESC, received_at ASC
    LIMIT %s;
"""

GET_EMAILS_BY_STATUS = """
    SELECT
        id,
        message_id,
        from_address,
        subject,
        body,
        received_at,
        processed_at,
        status,
        intent
    FROM emails
    WHERE status = %s
    ORDER BY received_at DESC
    LIMIT %s;
"""

GET_EMAILS_BY_INTENT = """
    SELECT
        id,
        message_id,
        from_address,
        subject,
        body,
        received_at,
        status,
        intent
    FROM emails
    WHERE intent = %s
    ORDER BY received_at DESC
    LIMIT %s;
"""

GET_EMAILS_BY_SENDER = """
    SELECT
        id,
        message_id,
        from_address,
        subject,
        body,
        received_at,
        status,
        intent
    FROM emails
    WHERE from_address = %s
    ORDER BY received_at DESC
    LIMIT %s;
"""

GET_RECENT_EMAILS = """
    SELECT
        id,
        message_id,
        from_address,
        subject,
        body,
        received_at,
        status,
        intent
    FROM emails
    ORDER BY received_at DESC
    LIMIT %s;
"""

GET_UNPROCESSED_EMAILS = """
    SELECT
        id,
        message_id,
        from_address,
        subject,
        body,
        received_at,
        status
    FROM emails
    WHERE status IN ('pending', 'classified')
    ORDER BY priority DESC, received_at ASC
    LIMIT %s;
"""

# =============================================================================
# COUNT Queries
# =============================================================================

COUNT_EMAILS_BY_STATUS = """
    SELECT status, COUNT(*) as count
    FROM emails
    GROUP BY status;
"""

COUNT_EMAILS_BY_INTENT = """
    SELECT intent, COUNT(*) as count
    FROM emails
    WHERE intent IS NOT NULL
    GROUP BY intent;
"""

COUNT_PENDING_EMAILS = """
    SELECT COUNT(*) as count
    FROM emails
    WHERE status = 'pending';
"""

# =============================================================================
# DELETE Queries
# =============================================================================

DELETE_EMAIL_BY_ID = """
    DELETE FROM emails
    WHERE id = %s
    RETURNING id;
"""

DELETE_EMAILS_OLDER_THAN = """
    DELETE FROM emails
    WHERE received_at < %s
    AND status IN ('responded', 'failed')
    RETURNING id;
"""

# =============================================================================
# PAGINATED Queries (for web dashboard)
# =============================================================================

GET_EMAILS_PAGINATED = """
    SELECT
        id,
        message_id,
        from_address,
        subject,
        received_at,
        processed_at,
        status,
        intent,
        priority,
        created_at
    FROM emails
    WHERE (%s IS NULL OR status = %s)
    AND (%s IS NULL OR intent = %s)
    AND (%s IS NULL OR from_address ILIKE %s OR subject ILIKE %s)
    ORDER BY received_at DESC
    LIMIT %s OFFSET %s;
"""

COUNT_EMAILS_FILTERED = """
    SELECT COUNT(*) as count
    FROM emails
    WHERE (%s IS NULL OR status = %s)
    AND (%s IS NULL OR intent = %s)
    AND (%s IS NULL OR from_address ILIKE %s OR subject ILIKE %s);
"""

GET_RESPONSES_PAGINATED = """
    SELECT
        r.id,
        r.email_id,
        r.draft_content,
        r.status,
        r.generated_at,
        r.sent_at,
        r.approved_by,
        r.send_attempts,
        r.send_error,
        r.created_at,
        r.updated_at,
        e.from_address,
        e.subject,
        e.intent
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    WHERE (%s IS NULL OR r.status = %s)
    ORDER BY r.created_at DESC
    LIMIT %s OFFSET %s;
"""

COUNT_RESPONSES_FILTERED = """
    SELECT COUNT(*) as count
    FROM responses r
    WHERE (%s IS NULL OR r.status = %s);
"""
