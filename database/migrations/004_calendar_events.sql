-- =============================================================================
-- Migration: 004_calendar_events.sql
-- Description: Add Google Calendar integration tables and response columns
-- Tables: calendar_events, calendar_sync_state
-- Columns added to responses: calendar_event_id, calendar_status,
--                              calendar_conflict_details
-- =============================================================================

-- -----------------------------------------------------------------------------
-- New table: calendar_events
-- Stores both system-created and manually-added Google Calendar events
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    google_event_id VARCHAR(255) UNIQUE NOT NULL,
    response_id INTEGER REFERENCES responses(id) ON DELETE SET NULL,

    -- Event details (synced from Google)
    title VARCHAR(500),
    description TEXT,
    location VARCHAR(500),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Parsed booking info (for manual events)
    customer_name VARCHAR(255),
    customer_phone VARCHAR(50),
    service_type VARCHAR(100),

    -- Sync metadata
    source VARCHAR(20) NOT NULL DEFAULT 'system',
    google_updated_at TIMESTAMP WITH TIME ZONE,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT check_calendar_event_source CHECK (source IN ('system', 'manual'))
);

-- Index for sync queries (find events updated since last sync)
CREATE INDEX IF NOT EXISTS idx_calendar_events_google_updated
    ON calendar_events(google_updated_at);

-- Index for date-range queries (conflict checks, upcoming events)
CREATE INDEX IF NOT EXISTS idx_calendar_events_start_time
    ON calendar_events(start_time);

-- Index for looking up by response
CREATE INDEX IF NOT EXISTS idx_calendar_events_response_id
    ON calendar_events(response_id)
    WHERE response_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- New table: calendar_sync_state
-- Tracks incremental sync state for Google Calendar polling
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS calendar_sync_state (
    id SERIAL PRIMARY KEY,
    last_sync_token VARCHAR(255),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert initial sync state row
INSERT INTO calendar_sync_state (id, last_sync_at)
VALUES (1, NULL)
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Add calendar columns to responses table
-- -----------------------------------------------------------------------------

ALTER TABLE responses
ADD COLUMN IF NOT EXISTS calendar_event_id VARCHAR(255);

ALTER TABLE responses
ADD COLUMN IF NOT EXISTS calendar_status VARCHAR(50) DEFAULT 'pending';

ALTER TABLE responses
ADD COLUMN IF NOT EXISTS calendar_conflict_details JSONB;

-- Constraint for calendar_status values
ALTER TABLE responses DROP CONSTRAINT IF EXISTS check_calendar_status;
ALTER TABLE responses ADD CONSTRAINT check_calendar_status
    CHECK (calendar_status IN ('pending', 'created', 'conflict', 'skipped', 'failed'));

-- Index for finding responses needing calendar events
CREATE INDEX IF NOT EXISTS idx_responses_calendar_pending
    ON responses(calendar_status)
    WHERE calendar_status = 'pending' AND status = 'sent';

-- =============================================================================
-- End of Migration: 004_calendar_events.sql
-- =============================================================================
