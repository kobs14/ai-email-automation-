"""
SQL queries for the users table.

All queries use parameterized placeholders (%s) to prevent SQL injection.
Always pass user input through the params argument, never concatenate strings.
"""

# =============================================================================
# INSERT Queries
# =============================================================================

INSERT_USER = """
    INSERT INTO users (username, email, password_hash, role)
    VALUES (%s, %s, %s, %s)
    RETURNING id, username, email, role, is_active, created_at;
"""

# =============================================================================
# UPDATE Queries
# =============================================================================

UPDATE_USER_LAST_LOGIN = """
    UPDATE users
    SET last_login_at = CURRENT_TIMESTAMP
    WHERE id = %s
    RETURNING id, last_login_at;
"""

UPDATE_USER_PASSWORD = """
    UPDATE users
    SET password_hash = %s
    WHERE id = %s
    RETURNING id, updated_at;
"""

UPDATE_USER_ROLE = """
    UPDATE users
    SET role = %s
    WHERE id = %s
    RETURNING id, role, updated_at;
"""

UPDATE_USER_ACTIVE_STATUS = """
    UPDATE users
    SET is_active = %s
    WHERE id = %s
    RETURNING id, is_active, updated_at;
"""

# =============================================================================
# SELECT Queries
# =============================================================================

GET_USER_BY_ID = """
    SELECT
        id,
        username,
        email,
        password_hash,
        role,
        is_active,
        last_login_at,
        created_at,
        updated_at
    FROM users
    WHERE id = %s;
"""

GET_USER_BY_USERNAME = """
    SELECT
        id,
        username,
        email,
        password_hash,
        role,
        is_active,
        last_login_at,
        created_at,
        updated_at
    FROM users
    WHERE username = %s;
"""

GET_USER_BY_EMAIL = """
    SELECT
        id,
        username,
        email,
        password_hash,
        role,
        is_active,
        last_login_at,
        created_at,
        updated_at
    FROM users
    WHERE email = %s;
"""

GET_ALL_USERS = """
    SELECT
        id,
        username,
        email,
        role,
        is_active,
        last_login_at,
        created_at
    FROM users
    ORDER BY created_at DESC;
"""

GET_ACTIVE_USERS = """
    SELECT
        id,
        username,
        email,
        role,
        last_login_at,
        created_at
    FROM users
    WHERE is_active = true
    ORDER BY username;
"""

# =============================================================================
# EXISTS/CHECK Queries
# =============================================================================

USER_EXISTS_BY_USERNAME = """
    SELECT EXISTS(
        SELECT 1 FROM users WHERE username = %s
    ) AS exists;
"""

USER_EXISTS_BY_EMAIL = """
    SELECT EXISTS(
        SELECT 1 FROM users WHERE email = %s
    ) AS exists;
"""

# =============================================================================
# DELETE Queries
# =============================================================================

DELETE_USER_BY_ID = """
    DELETE FROM users
    WHERE id = %s
    RETURNING id;
"""
