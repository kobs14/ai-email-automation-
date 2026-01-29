-- =============================================================================
-- Migration: 003_email_sending.sql
-- Description: Add columns to responses table for email sending functionality
-- Columns added: send_attempts, send_error, sent_message_id
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Add new columns to responses table for tracking send status
-- -----------------------------------------------------------------------------

-- Track the number of send attempts
ALTER TABLE responses
ADD COLUMN IF NOT EXISTS send_attempts INTEGER NOT NULL DEFAULT 0;

-- Store the last error message from a failed send attempt
ALTER TABLE responses
ADD COLUMN IF NOT EXISTS send_error TEXT;

-- Store the Gmail message ID of the sent response (for threading)
ALTER TABLE responses
ADD COLUMN IF NOT EXISTS sent_message_id VARCHAR(255);

-- -----------------------------------------------------------------------------
-- Update response status constraint to include 'failed' status
-- -----------------------------------------------------------------------------

ALTER TABLE responses DROP CONSTRAINT IF EXISTS check_response_status;
ALTER TABLE responses ADD CONSTRAINT check_response_status
    CHECK (status IN ('draft', 'approved', 'sent', 'rejected', 'failed'));

-- -----------------------------------------------------------------------------
-- Add indexes for efficient querying of responses needing to be sent
-- -----------------------------------------------------------------------------

-- Index for finding approved responses that need to be sent
CREATE INDEX IF NOT EXISTS idx_responses_pending_send
    ON responses(status, send_attempts)
    WHERE status = 'approved' AND sent_at IS NULL;

-- Index for finding failed responses that might be retried
CREATE INDEX IF NOT EXISTS idx_responses_failed_send
    ON responses(status, send_attempts)
    WHERE status = 'failed';

-- Index for looking up by sent_message_id
CREATE INDEX IF NOT EXISTS idx_responses_sent_message_id
    ON responses(sent_message_id)
    WHERE sent_message_id IS NOT NULL;

-- =============================================================================
-- End of Migration: 003_email_sending.sql
-- =============================================================================
