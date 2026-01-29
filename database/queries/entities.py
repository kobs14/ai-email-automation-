"""
SQL queries for the extracted_entities table.

All queries use parameterized placeholders (%s) to prevent SQL injection.
Always pass user input through the params argument, never concatenate strings.
"""

# =============================================================================
# INSERT Queries
# =============================================================================

INSERT_ENTITY = """
    INSERT INTO extracted_entities (
        email_id,
        entity_type,
        entity_value,
        confidence
    ) VALUES (%s, %s, %s, %s)
    RETURNING id, extracted_at;
"""

# For use with psycopg2.extras.execute_values
# Usage: execute_values(cur, INSERT_ENTITIES_BATCH, values_list)
INSERT_ENTITIES_BATCH = """
    INSERT INTO extracted_entities (
        email_id,
        entity_type,
        entity_value,
        confidence
    ) VALUES %s
    RETURNING id;
"""

# Template for execute_values (email_id, entity_type, entity_value, confidence)
INSERT_ENTITIES_TEMPLATE = "(%s, %s, %s, %s)"

# =============================================================================
# UPDATE Queries
# =============================================================================

UPDATE_ENTITY_VALUE = """
    UPDATE extracted_entities
    SET entity_value = %s,
        confidence = %s
    WHERE id = %s
    RETURNING id, entity_value, confidence;
"""

UPDATE_ENTITY_CONFIDENCE = """
    UPDATE extracted_entities
    SET confidence = %s
    WHERE id = %s
    RETURNING id, confidence;
"""

# =============================================================================
# SELECT Queries - By Email
# =============================================================================

GET_ENTITIES_BY_EMAIL = """
    SELECT
        id,
        email_id,
        entity_type,
        entity_value,
        confidence,
        extracted_at
    FROM extracted_entities
    WHERE email_id = %s
    ORDER BY entity_type, confidence DESC;
"""

GET_ENTITIES_BY_EMAIL_AS_DICT = """
    SELECT
        entity_type,
        entity_value,
        confidence
    FROM extracted_entities
    WHERE email_id = %s
    ORDER BY confidence DESC;
"""

GET_ENTITY_BY_TYPE = """
    SELECT
        id,
        email_id,
        entity_type,
        entity_value,
        confidence,
        extracted_at
    FROM extracted_entities
    WHERE email_id = %s
    AND entity_type = %s
    ORDER BY confidence DESC
    LIMIT 1;
"""

GET_HIGH_CONFIDENCE_ENTITIES = """
    SELECT
        id,
        email_id,
        entity_type,
        entity_value,
        confidence,
        extracted_at
    FROM extracted_entities
    WHERE email_id = %s
    AND confidence >= %s
    ORDER BY entity_type;
"""

# =============================================================================
# SELECT Queries - Aggregations
# =============================================================================

COUNT_ENTITIES_BY_TYPE = """
    SELECT entity_type, COUNT(*) as count
    FROM extracted_entities
    GROUP BY entity_type
    ORDER BY count DESC;
"""

COUNT_ENTITIES_FOR_EMAIL = """
    SELECT COUNT(*) as count
    FROM extracted_entities
    WHERE email_id = %s;
"""

GET_ENTITY_TYPE_STATS = """
    SELECT
        entity_type,
        COUNT(*) as total_count,
        AVG(confidence) as avg_confidence,
        MIN(confidence) as min_confidence,
        MAX(confidence) as max_confidence
    FROM extracted_entities
    GROUP BY entity_type
    ORDER BY total_count DESC;
"""

# =============================================================================
# SELECT Queries - Search
# =============================================================================

SEARCH_ENTITIES_BY_VALUE = """
    SELECT
        ee.id,
        ee.email_id,
        ee.entity_type,
        ee.entity_value,
        ee.confidence,
        e.from_address,
        e.subject
    FROM extracted_entities ee
    JOIN emails e ON ee.email_id = e.id
    WHERE ee.entity_value ILIKE %s
    ORDER BY ee.extracted_at DESC
    LIMIT %s;
"""

GET_ENTITIES_BY_TYPE_VALUE = """
    SELECT
        ee.id,
        ee.email_id,
        ee.entity_type,
        ee.entity_value,
        ee.confidence,
        e.from_address,
        e.subject
    FROM extracted_entities ee
    JOIN emails e ON ee.email_id = e.id
    WHERE ee.entity_type = %s
    AND ee.entity_value ILIKE %s
    ORDER BY ee.extracted_at DESC
    LIMIT %s;
"""

# =============================================================================
# DELETE Queries
# =============================================================================

DELETE_ENTITIES_BY_EMAIL = """
    DELETE FROM extracted_entities
    WHERE email_id = %s
    RETURNING id;
"""

DELETE_ENTITY_BY_ID = """
    DELETE FROM extracted_entities
    WHERE id = %s
    RETURNING id;
"""

DELETE_LOW_CONFIDENCE_ENTITIES = """
    DELETE FROM extracted_entities
    WHERE email_id = %s
    AND confidence < %s
    RETURNING id;
"""
