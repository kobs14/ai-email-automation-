-- =============================================================================
-- Migration: 001_initial_schema.sql
-- Description: Creates the initial database schema for the email automation system
-- Tables: emails, extracted_entities, responses, business_config
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Function: update_updated_at_column
-- Purpose: Automatically updates the updated_at timestamp on row modification
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- -----------------------------------------------------------------------------
-- Table: emails
-- Purpose: Stores incoming customer emails for processing
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    from_address VARCHAR(255) NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    received_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    intent VARCHAR(50),
    priority INTEGER DEFAULT 0,
    raw_headers JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for emails table
CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status);
CREATE INDEX IF NOT EXISTS idx_emails_intent ON emails(intent);
CREATE INDEX IF NOT EXISTS idx_emails_received_at ON emails(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_emails_status_intent ON emails(status, intent);
CREATE INDEX IF NOT EXISTS idx_emails_from_address ON emails(from_address);

-- Trigger for emails updated_at
DROP TRIGGER IF EXISTS update_emails_updated_at ON emails;
CREATE TRIGGER update_emails_updated_at
    BEFORE UPDATE ON emails
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- -----------------------------------------------------------------------------
-- Table: extracted_entities
-- Purpose: Stores AI-extracted information from emails (property details, dates, etc.)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS extracted_entities (
    id SERIAL PRIMARY KEY,
    email_id INTEGER NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_value TEXT NOT NULL,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for extracted_entities table
CREATE INDEX IF NOT EXISTS idx_entities_email_id ON extracted_entities(email_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON extracted_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_email_type ON extracted_entities(email_id, entity_type);

-- -----------------------------------------------------------------------------
-- Table: responses
-- Purpose: Stores AI-generated response drafts and their status
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS responses (
    id SERIAL PRIMARY KEY,
    email_id INTEGER NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    draft_content TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    approved_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for responses table
CREATE INDEX IF NOT EXISTS idx_responses_email_id ON responses(email_id);
CREATE INDEX IF NOT EXISTS idx_responses_status ON responses(status);
CREATE INDEX IF NOT EXISTS idx_responses_generated_at ON responses(generated_at DESC);

-- Trigger for responses updated_at
DROP TRIGGER IF EXISTS update_responses_updated_at ON responses;
CREATE TRIGGER update_responses_updated_at
    BEFORE UPDATE ON responses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- -----------------------------------------------------------------------------
-- Table: business_config
-- Purpose: Stores business configuration, pricing rules, and AI prompt settings
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger for business_config updated_at
DROP TRIGGER IF EXISTS update_config_updated_at ON business_config;
CREATE TRIGGER update_config_updated_at
    BEFORE UPDATE ON business_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- -----------------------------------------------------------------------------
-- Constraints: Data integrity checks
-- -----------------------------------------------------------------------------

-- Email status must be one of the allowed values
ALTER TABLE emails DROP CONSTRAINT IF EXISTS check_email_status;
ALTER TABLE emails ADD CONSTRAINT check_email_status
    CHECK (status IN ('pending', 'classified', 'responded', 'failed'));

-- Email intent must be one of the allowed values (or NULL for unclassified)
ALTER TABLE emails DROP CONSTRAINT IF EXISTS check_email_intent;
ALTER TABLE emails ADD CONSTRAINT check_email_intent
    CHECK (intent IS NULL OR intent IN (
        'quote_request',
        'booking_request',
        'rescheduling',
        'complaint',
        'general_inquiry'
    ));

-- Response status must be one of the allowed values
ALTER TABLE responses DROP CONSTRAINT IF EXISTS check_response_status;
ALTER TABLE responses ADD CONSTRAINT check_response_status
    CHECK (status IN ('draft', 'approved', 'sent', 'rejected'));

-- =============================================================================
-- End of Migration: 001_initial_schema.sql
-- =============================================================================
