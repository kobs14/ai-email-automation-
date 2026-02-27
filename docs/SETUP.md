# Setup Guide

Complete setup instructions for the AI Email Automation Platform.

## Prerequisites

- **Python 3.11+**
- **Node.js 20+** (for frontend development)
- **Docker** and **Docker Compose**
- **Anthropic API Key** ([Get one here](https://console.anthropic.com/))

## Quick Start

### 1. Clone and Setup

```bash
cd EcoClean_Email_Automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # or vim, code, etc.
```

**Required settings in `.env`:**
```
ANTHROPIC_API_KEY=your_actual_api_key_here
POSTGRES_PASSWORD=your_secure_password
```

### 3. Start All Services

```bash
# Start all Docker containers
docker-compose up -d

# Verify services are running
docker-compose ps
```

This starts 7 containers:

| Container | Description | Port |
|-----------|-------------|------|
| postgres | PostgreSQL 15 database | 5432 |
| redis | Redis 7 cache/queue | 6379 |
| celery_worker | Async task processing | - |
| celery_beat | Periodic task scheduler | - |
| telegram_bot | Telegram notifications | - |
| backend | Flask REST API (Gunicorn) | 5000 |
| frontend | React SPA (nginx) | 3000 |

### 4. Initialize Database

```bash
# Run migrations to create tables and seed data
python scripts/init_db.py

# Verify database connectivity
python scripts/test_connection.py
```

### 5. Access the Web Dashboard

Open [http://localhost:3000](http://localhost:3000) in your browser.

**Default credentials:**
- **Username:** `admin`
- **Password:** `changeme`

> **Important:** Change the default password after first login in production.

### User Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access: manage config, approve/reject responses, manage users |
| `operator` | Approve, reject, and edit responses |
| `viewer` | Read-only access to emails, responses, and stats |

---

## Gmail API Setup

To enable automatic email fetching from Gmail:

### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Cleaning Email Automation")

### Step 2: Enable Google APIs
1. Go to **APIs & Services** -> **Library**
2. Search for "Gmail API" and click **Enable**
3. Search for "Google Calendar API" and click **Enable** (required for calendar integration)

### Step 3: Configure OAuth Consent Screen
1. Go to **APIs & Services** -> **OAuth consent screen**
2. Choose **External** (or Internal for Google Workspace)
3. Fill in app name, support email, developer contact
4. Add scopes: `gmail.modify`, `calendar.events`
5. Add your email as a test user

### Step 4: Create OAuth Credentials
1. Go to **APIs & Services** -> **Credentials**
2. Click **Create Credentials** -> **OAuth client ID**
3. Choose **Desktop app**
4. Download the JSON file
5. Save as `credentials/google_credentials.json`

### Step 5: Authorize and Test
```bash
# Run OAuth setup (opens browser for authorization)
python scripts/setup_gmail_oauth.py

# Fetch emails from Gmail
python scripts/fetch_emails.py

# Fetch and process through AI pipeline
python scripts/fetch_emails.py --process
```

---

## Telegram Bot Setup

Enable Telegram notifications for real-time alerts when new response drafts are created.

### Step 1: Create a Telegram Bot
1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Choose a name (e.g., "EcoClean Notifications")
4. Choose a username (must end in `bot`, e.g., "ecoclean_notify_bot")
5. Copy the bot token provided

### Step 2: Get Your Chat ID
1. Search for [@userinfobot](https://t.me/userinfobot) on Telegram
2. Start a chat and it will display your chat ID
3. Copy the numeric ID

### Step 3: Configure Environment
Add to your `.env` file:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_CHAT_ID=your_chat_id_here
```

### Step 4: Start the Bot
The bot starts automatically with docker-compose:
```bash
docker-compose up -d telegram_bot
```

Or run standalone for development:
```bash
python -m services.telegram.bot
```

### Bot Commands

Commands are available via the **menu button** (tap "/" in Telegram) or by typing directly:

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and displays your chat ID |
| `/pending` | List all response drafts awaiting approval |
| `/calendar` | View upcoming calendar events |
| `/stats` | Show email and response statistics |
| `/cancel` | Cancel current draft edit operation |
| `/help` | Display available commands |

### Action Buttons

| Button | Description |
|--------|-------------|
| Approve | Send the response immediately |
| Reject | Mark draft as rejected (won't send) |
| Edit | Modify the draft before approving |
| View Full | See complete original message and draft |

### Notification Flow
When a new email is processed:
1. Email is classified and response draft is generated
2. Telegram notification sent with **original message** and **draft preview**
3. Admin can:
   - **Approve** to send immediately
   - **Reject** to discard
   - **Edit** to modify the draft, then approve
4. Approved responses are sent automatically
5. Calendar event created automatically (if calendar integration enabled)
6. If scheduling conflict detected, admin notified with action buttons

---

## Google Calendar Integration

Two-way sync between EcoClean and Google Calendar.

### Outbound (System -> Google Calendar)
When a response email is sent, the system automatically:
1. Parses date/time from extracted entities
2. Checks for scheduling conflicts
3. Creates a Google Calendar event (or notifies admin of conflicts)

### Inbound (Google Calendar -> System)
Every 5 minutes, the system syncs events from Google Calendar:
1. Detects manually-added events
2. Imports them to the database
3. Notifies admin via Telegram

### Calendar Setup

#### Step 1: Enable Google Calendar API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** -> **Library**
3. Search for "Google Calendar API" and click **Enable**

#### Step 2: Update OAuth Scopes
The calendar integration requires the `calendar.events` scope in addition to Gmail scopes. When first enabling calendar, you need to re-authorize:

```bash
# Delete existing token to force re-authorization
rm credentials/gmail_token.json

# Re-run OAuth setup (will request both Gmail + Calendar permissions)
python scripts/setup_gmail_oauth.py
```

#### Step 3: Configure Environment
Add to your `.env` file:
```bash
CALENDAR_ENABLED=true
GOOGLE_CALENDAR_ID=primary
CALENDAR_DEFAULT_DURATION=3.0
CALENDAR_BUFFER_MINUTES=30
CALENDAR_TIMEZONE=America/New_York
```

#### Step 4: Run Database Migration
```bash
python scripts/init_db.py
# Or run the specific migration:
python database/migrations/migrate.py --file 004_calendar_events.sql
```

### Calendar Telegram Commands

| Command/Button | Description |
|---------------|-------------|
| `/calendar` | View upcoming calendar events |
| Create Anyway | Force-create event despite conflict |
| Skip | Skip calendar event creation |
| View Details | Show conflict details |

---

## Configuration

### Environment Variables

All environment variables are documented in `.env.example`. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | Database host | localhost |
| `POSTGRES_PORT` | Database port | 5432 |
| `POSTGRES_USER` | Database user | cleaning_user |
| `POSTGRES_PASSWORD` | Database password | (required) |
| `POSTGRES_DB` | Database name | cleaning_email_db |
| `REDIS_HOST` | Redis host | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `ANTHROPIC_API_KEY` | Claude API key | (required) |
| `CLAUDE_MODEL` | Claude model to use | claude-sonnet-4-20250514 |
| `DEBUG` | Enable debug mode | true |
| `LOG_LEVEL` | Logging level | INFO |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | (optional) |
| `TELEGRAM_ADMIN_CHAT_ID` | Your Telegram chat ID for notifications | (optional) |
| `CALENDAR_ENABLED` | Enable Google Calendar integration | false |
| `GOOGLE_CALENDAR_ID` | Google Calendar ID | primary |
| `CALENDAR_DEFAULT_DURATION` | Default event duration (hours) | 3.0 |
| `CALENDAR_BUFFER_MINUTES` | Buffer time for conflict checks | 30 |
| `CALENDAR_TIMEZONE` | Timezone for calendar events | America/New_York |
| `CRM_ENABLED` | Enable CRM integration | false |
| `CRM_PROVIDER` | CRM backend (`null`, future: `hubspot`) | null |
| `FLASK_SECRET_KEY` | Flask session secret (change in production) | (required) |
| `JWT_SECRET_KEY` | JWT signing secret (change in production) | (required) |
| `JWT_ACCESS_TOKEN_EXPIRES` | Access token TTL in seconds | 3600 |
| `JWT_REFRESH_TOKEN_EXPIRES` | Refresh token TTL in seconds | 604800 |
| `FRONTEND_URL` | Frontend URL for CORS | http://localhost:3000 |

### Business Configuration (in database)

The `business_config` table stores:

- **pricing_rules** — Base pricing by property type
- **service_multipliers** — Multipliers for service types (deep clean, move-out, etc.)
- **business_info** — Company contact information
- **brand_voice** — AI response style guidelines

---

## Running Migrations

### Run All Migrations

```bash
python scripts/init_db.py
```

### Run Individual Migration

```bash
python database/migrations/migrate.py --file 001_initial_schema.sql
```

### Seed Data Only

```bash
python scripts/seed_db.py
```
