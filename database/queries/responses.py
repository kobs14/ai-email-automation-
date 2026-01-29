"""
SQL queries for the responses table.

All queries use parameterized placeholders (%s) to prevent SQL injection.
Always pass user input through the params argument, never concatenate strings.
"""

# =============================================================================
# INSERT Queries
# =============================================================================

INSERT_RESPONSE = """
    INSERT INTO responses (
        email_id,
        draft_content,
        status
    ) VALUES (%s, %s, %s)
    RETURNING id, generated_at, created_at;
"""

INSERT_RESPONSE_DRAFT = """
    INSERT INTO responses (
        email_id,
        draft_content,
        status
    ) VALUES (%s, %s, 'draft')
    RETURNING id, generated_at;
"""

# =============================================================================
# UPDATE Queries
# =============================================================================

UPDATE_RESPONSE_STATUS = """
    UPDATE responses
    SET status = %s,
        sent_at = CASE WHEN %s = 'sent' THEN CURRENT_TIMESTAMP ELSE sent_at END
    WHERE id = %s
    RETURNING id, status, sent_at;
"""

UPDATE_RESPONSE_CONTENT = """
    UPDATE responses
    SET draft_content = %s
    WHERE id = %s
    RETURNING id, draft_content, updated_at;
"""

APPROVE_RESPONSE = """
    UPDATE responses
    SET status = 'approved',
        approved_by = %s
    WHERE id = %s
    RETURNING id, status, approved_by, updated_at;
"""

REJECT_RESPONSE = """
    UPDATE responses
    SET status = 'rejected'
    WHERE id = %s
    RETURNING id, status, updated_at;
"""

MARK_RESPONSE_SENT = """
    UPDATE responses
    SET status = 'sent',
        sent_at = CURRENT_TIMESTAMP
    WHERE id = %s
    RETURNING id, status, sent_at;
"""

# =============================================================================
# SELECT Queries - Single Row
# =============================================================================

GET_RESPONSE_BY_ID = """
    SELECT
        id,
        email_id,
        draft_content,
        status,
        generated_at,
        sent_at,
        approved_by,
        created_at,
        updated_at
    FROM responses
    WHERE id = %s;
"""

GET_RESPONSE_BY_EMAIL_ID = """
    SELECT
        id,
        email_id,
        draft_content,
        status,
        generated_at,
        sent_at,
        approved_by,
        created_at,
        updated_at
    FROM responses
    WHERE email_id = %s
    ORDER BY created_at DESC
    LIMIT 1;
"""

GET_LATEST_RESPONSE_FOR_EMAIL = """
    SELECT
        r.id,
        r.email_id,
        r.draft_content,
        r.status,
        r.generated_at,
        r.sent_at,
        r.approved_by,
        e.from_address,
        e.subject
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    WHERE r.email_id = %s
    ORDER BY r.created_at DESC
    LIMIT 1;
"""

# =============================================================================
# SELECT Queries - Multiple Rows
# =============================================================================

GET_PENDING_DRAFTS = """
    SELECT
        r.id,
        r.email_id,
        r.draft_content,
        r.status,
        r.generated_at,
        e.from_address,
        e.subject,
        e.body,
        e.intent
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    WHERE r.status = 'draft'
    ORDER BY r.generated_at DESC;
"""

GET_RESPONSES_BY_STATUS = """
    SELECT
        r.id,
        r.email_id,
        r.draft_content,
        r.status,
        r.generated_at,
        r.sent_at,
        r.approved_by,
        e.from_address,
        e.subject
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    WHERE r.status = %s
    ORDER BY r.created_at DESC
    LIMIT %s;
"""

GET_APPROVED_UNSENT_RESPONSES = """
    SELECT
        r.id,
        r.email_id,
        r.draft_content,
        r.approved_by,
        e.from_address,
        e.subject
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    WHERE r.status = 'approved'
    AND r.sent_at IS NULL
    ORDER BY r.updated_at ASC;
"""

GET_RECENT_RESPONSES = """
    SELECT
        r.id,
        r.email_id,
        r.draft_content,
        r.status,
        r.generated_at,
        r.sent_at,
        e.from_address,
        e.subject
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    ORDER BY r.created_at DESC
    LIMIT %s;
"""

GET_RESPONSES_FOR_EMAIL = """
    SELECT
        id,
        email_id,
        draft_content,
        status,
        generated_at,
        sent_at,
        approved_by,
        created_at
    FROM responses
    WHERE email_id = %s
    ORDER BY created_at DESC;
"""

# =============================================================================
# COUNT Queries
# =============================================================================

COUNT_RESPONSES_BY_STATUS = """
    SELECT status, COUNT(*) as count
    FROM responses
    GROUP BY status;
"""

COUNT_PENDING_DRAFTS = """
    SELECT COUNT(*) as count
    FROM responses
    WHERE status = 'draft';
"""

COUNT_RESPONSES_FOR_EMAIL = """
    SELECT COUNT(*) as count
    FROM responses
    WHERE email_id = %s;
"""

# =============================================================================
# DELETE Queries
# =============================================================================

DELETE_RESPONSE_BY_ID = """
    DELETE FROM responses
    WHERE id = %s
    RETURNING id;
"""

DELETE_RESPONSES_BY_EMAIL = """
    DELETE FROM responses
    WHERE email_id = %s
    RETURNING id;
"""

DELETE_OLD_DRAFTS = """
    DELETE FROM responses
    WHERE status = 'draft'
    AND generated_at < %s
    RETURNING id;
"""

# =============================================================================
# EMAIL SENDING Queries
# =============================================================================

RECORD_SEND_ERROR = """
    UPDATE responses
    SET send_attempts = send_attempts + 1,
        send_error = %s
    WHERE id = %s
    RETURNING id, send_attempts, send_error;
"""

MARK_SENT_WITH_MESSAGE_ID = """
    UPDATE responses
    SET status = 'sent',
        sent_at = CURRENT_TIMESTAMP,
        sent_message_id = %s,
        send_error = NULL
    WHERE id = %s
    RETURNING id, status, sent_at, sent_message_id;
"""

MARK_RESPONSE_FAILED = """
    UPDATE responses
    SET status = 'failed',
        send_attempts = send_attempts + 1,
        send_error = %s
    WHERE id = %s
    RETURNING id, status, send_attempts, send_error;
"""

GET_APPROVED_RESPONSES_FOR_SENDING = """
    SELECT
        r.id,
        r.email_id,
        r.draft_content,
        r.approved_by,
        r.send_attempts,
        e.from_address,
        e.subject,
        e.message_id,
        e.raw_headers
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    WHERE r.status = 'approved'
    AND r.sent_at IS NULL
    AND r.send_attempts < %s
    ORDER BY r.updated_at ASC
    LIMIT %s;
"""

GET_RESPONSE_WITH_EMAIL = """
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
        r.sent_message_id,
        e.from_address,
        e.subject,
        e.message_id,
        e.body as original_body,
        e.intent,
        e.raw_headers
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    WHERE r.id = %s;
"""

GET_FAILED_RESPONSES = """
    SELECT
        r.id,
        r.email_id,
        r.draft_content,
        r.send_attempts,
        r.send_error,
        e.from_address,
        e.subject
    FROM responses r
    JOIN emails e ON r.email_id = e.id
    WHERE r.status = 'failed'
    ORDER BY r.updated_at DESC
    LIMIT %s;
"""

RESET_RESPONSE_FOR_RETRY = """
    UPDATE responses
    SET status = 'approved',
        send_error = NULL
    WHERE id = %s
    AND status = 'failed'
    RETURNING id, status;
"""
