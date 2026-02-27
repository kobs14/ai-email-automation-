# Database Schema

PostgreSQL 15 with raw SQL via psycopg2 and connection pooling. Migrations are stored in `database/migrations/`.

## Tables

### `emails`
Stores incoming customer emails.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| message_id | VARCHAR(255) | Unique email identifier |
| from_address | VARCHAR(255) | Sender email |
| subject | TEXT | Email subject |
| body | TEXT | Email content |
| received_at | TIMESTAMP | When email was received |
| processed_at | TIMESTAMP | When processing completed |
| status | VARCHAR(50) | pending, classified, responded, failed |
| intent | VARCHAR(50) | Classified intent |
| priority | INTEGER | Processing priority |
| raw_headers | JSONB | Original email headers |

### `extracted_entities`
Stores AI-extracted information from emails.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| email_id | INTEGER | Foreign key to emails |
| entity_type | VARCHAR(50) | Type (property_type, bedrooms, etc.) |
| entity_value | TEXT | Extracted value |
| confidence | FLOAT | AI confidence score (0-1) |

### `responses`
Stores generated response drafts.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| email_id | INTEGER | Foreign key to emails |
| draft_content | TEXT | Generated response text |
| status | VARCHAR(50) | draft, approved, sent, rejected, failed |
| approved_by | VARCHAR(100) | Who approved the response |
| sent_at | TIMESTAMP | When response was sent |
| send_attempts | INTEGER | Number of send attempts |
| send_error | TEXT | Last send error message |
| sent_message_id | VARCHAR(255) | Gmail message ID of sent response |
| calendar_event_id | VARCHAR(255) | Google Calendar event ID |
| calendar_status | VARCHAR(50) | pending, created, conflict, skipped, failed |
| calendar_conflict_details | JSONB | Details of scheduling conflicts |

### `calendar_events`
Stores Google Calendar events (both auto-created and manual).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| google_event_id | VARCHAR(255) | Google Calendar event ID |
| response_id | INTEGER | FK to responses (NULL if manual) |
| title | VARCHAR(500) | Event title |
| description | TEXT | Event description |
| location | VARCHAR(500) | Event location |
| start_time | TIMESTAMPTZ | Event start |
| end_time | TIMESTAMPTZ | Event end |
| customer_name | VARCHAR(255) | Customer name |
| service_type | VARCHAR(100) | Cleaning service type |
| source | VARCHAR(20) | 'system' or 'manual' |

### `calendar_sync_state`
Tracks Google Calendar sync progress.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| last_sync_token | VARCHAR(255) | Google sync token |
| last_sync_at | TIMESTAMPTZ | Last sync timestamp |

### `users`
Stores user accounts for the web dashboard.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| username | VARCHAR(100) | Unique username |
| email | VARCHAR(255) | Unique email address |
| password_hash | VARCHAR(255) | bcrypt hashed password |
| role | VARCHAR(50) | admin, operator, viewer |
| is_active | BOOLEAN | Account active status |
| last_login_at | TIMESTAMPTZ | Last login timestamp |

### `business_config`
Stores business settings and AI prompts.

| Column | Type | Description |
|--------|------|-------------|
| key | VARCHAR(100) | Configuration key (PK) |
| value | JSONB | Configuration value |
| description | TEXT | Human-readable description |

## Intent Types

| Intent | Description |
|--------|-------------|
| `quote_request` | Customer asking for pricing |
| `booking_request` | Customer wants to schedule service |
| `rescheduling` | Customer wants to change existing booking |
| `complaint` | Customer expressing dissatisfaction |
| `general_inquiry` | Other questions |
