"""
SQL queries for the business_config table.

All queries use parameterized placeholders (%s) to prevent SQL injection.
Always pass user input through the params argument, never concatenate strings.

The business_config table stores JSONB values, so queries may include
PostgreSQL JSON operators like ->, ->>, @>, etc.
"""

# =============================================================================
# UPSERT Queries
# =============================================================================

UPSERT_CONFIG = """
    INSERT INTO business_config (key, value, description)
    VALUES (%s, %s, %s)
    ON CONFLICT (key) DO UPDATE
    SET value = EXCLUDED.value,
        description = COALESCE(EXCLUDED.description, business_config.description),
        updated_at = CURRENT_TIMESTAMP
    RETURNING key, updated_at;
"""

UPSERT_CONFIG_VALUE_ONLY = """
    INSERT INTO business_config (key, value)
    VALUES (%s, %s)
    ON CONFLICT (key) DO UPDATE
    SET value = EXCLUDED.value,
        updated_at = CURRENT_TIMESTAMP
    RETURNING key, updated_at;
"""

# =============================================================================
# UPDATE Queries
# =============================================================================

UPDATE_CONFIG_VALUE = """
    UPDATE business_config
    SET value = %s,
        updated_at = CURRENT_TIMESTAMP
    WHERE key = %s
    RETURNING key, updated_at;
"""

UPDATE_CONFIG_DESCRIPTION = """
    UPDATE business_config
    SET description = %s,
        updated_at = CURRENT_TIMESTAMP
    WHERE key = %s
    RETURNING key, updated_at;
"""

# Update a specific JSON field within a config value
# Usage: params = ('new_value', 'json_path', 'config_key')
UPDATE_CONFIG_JSON_FIELD = """
    UPDATE business_config
    SET value = jsonb_set(value, %s, %s),
        updated_at = CURRENT_TIMESTAMP
    WHERE key = %s
    RETURNING key, value, updated_at;
"""

# =============================================================================
# SELECT Queries
# =============================================================================

GET_CONFIG = """
    SELECT value
    FROM business_config
    WHERE key = %s;
"""

GET_CONFIG_WITH_META = """
    SELECT key, value, description, updated_at
    FROM business_config
    WHERE key = %s;
"""

GET_ALL_CONFIG = """
    SELECT key, value, description, updated_at
    FROM business_config
    ORDER BY key;
"""

GET_CONFIG_KEYS = """
    SELECT key
    FROM business_config
    ORDER BY key;
"""

# Get a specific field from a JSONB config value
# Usage: params = ('config_key', 'field_name')
GET_CONFIG_FIELD = """
    SELECT value -> %s as field_value
    FROM business_config
    WHERE key = %s;
"""

# Get a text value from a nested JSONB path
# Usage: params = ('config_key',) - path is hardcoded in query
GET_CONFIG_TEXT_FIELD = """
    SELECT value ->> %s as field_value
    FROM business_config
    WHERE key = %s;
"""

# =============================================================================
# Pricing-Specific Queries
# =============================================================================

GET_PRICING_RULES = """
    SELECT value
    FROM business_config
    WHERE key = 'pricing_rules';
"""

GET_SERVICE_MULTIPLIERS = """
    SELECT value
    FROM business_config
    WHERE key = 'service_multipliers';
"""

GET_ADDON_SERVICES = """
    SELECT value
    FROM business_config
    WHERE key = 'addon_services';
"""

# Get pricing for a specific property type
# Usage: params = ('house',) for property type
GET_PROPERTY_PRICING = """
    SELECT value -> %s as pricing
    FROM business_config
    WHERE key = 'pricing_rules';
"""

# Get multiplier for a specific service type
GET_SERVICE_MULTIPLIER = """
    SELECT value -> %s -> 'multiplier' as multiplier
    FROM business_config
    WHERE key = 'service_multipliers';
"""

# =============================================================================
# Brand/Business Info Queries
# =============================================================================

GET_BUSINESS_INFO = """
    SELECT value
    FROM business_config
    WHERE key = 'business_info';
"""

GET_BRAND_VOICE = """
    SELECT value
    FROM business_config
    WHERE key = 'brand_voice';
"""

GET_RESPONSE_TEMPLATES = """
    SELECT value
    FROM business_config
    WHERE key = 'response_templates';
"""

GET_ENTITY_EXTRACTION_RULES = """
    SELECT value
    FROM business_config
    WHERE key = 'entity_extraction_rules';
"""

# Get extraction rules for a specific intent
GET_EXTRACTION_RULES_FOR_INTENT = """
    SELECT value -> %s as rules
    FROM business_config
    WHERE key = 'entity_extraction_rules';
"""

# =============================================================================
# EXISTS/CHECK Queries
# =============================================================================

CONFIG_EXISTS = """
    SELECT EXISTS(
        SELECT 1 FROM business_config WHERE key = %s
    ) AS exists;
"""

# =============================================================================
# DELETE Queries
# =============================================================================

DELETE_CONFIG = """
    DELETE FROM business_config
    WHERE key = %s
    RETURNING key;
"""
