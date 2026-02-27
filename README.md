# AI Email Automation Platform

**AI-powered email automation platform that handles the full lifecycle of inbound customer emails — from ingestion and classification to response generation, human approval, and delivery.**

Built for service businesses that need to eliminate manual email triage without sacrificing quality. The system ingests emails via Gmail, classifies intent and extracts entities using Claude, drafts context-aware responses, routes them through a human-in-the-loop approval workflow (Telegram + web dashboard), and syncs confirmed appointments to Google Calendar.

**Core Engineering Highlights:**
- **Distributed Architecture** — 7 containerized microservices communicating via Redis Pub/Sub and Celery task queues
- **AI/NLP Pipeline** — Claude API integration for intent classification, entity extraction, and context-aware response generation
- **Full-Stack Implementation** — React + TypeScript SPA with Flask REST API, JWT authentication, and role-based access control
- **Real-Time Admin Interface** — Telegram Bot with inline keyboard callbacks, conversational workflows, and instant push notifications
- **Multi-Service Integration** — Gmail API (OAuth 2.0), Google Calendar API (bidirectional sync), Telegram Bot API
- **Production-Ready Infrastructure** — Docker Compose orchestration, connection pooling, rate limiting, retry logic, and comprehensive error handling

Built with **Python**, **Flask**, **React/TypeScript**, **PostgreSQL**, **Redis**, **Celery**, and **Docker**.

## Screenshots

**Web Dashboard** — Analytics & email management interface

<img src="docs/screenshots/dashboard.png" width="700" alt="Web Dashboard">
<img src="docs/screenshots/dashboard2.png" width="700" alt="Web Dashboard">

**Telegram Bot** — Real-time approval workflow with inline actions

<img src="docs/screenshots/telegram-bot1.png" width="220" alt="Telegram Bot"> <img src="docs/screenshots/telegram-bot2.png" width="220" alt="Telegram Bot"> <img src="docs/screenshots/telegram-bot3.png" width="220" alt="Telegram Bot">

## Table of Contents

- [Overview](#overview)
- [Key Capabilities](#key-capabilities)
- [Tech Stack](#tech-stack)
- [End-to-End Flow](#end-to-end-flow)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Testing](#testing)
- [API Reference](#api-reference)
- [Completed Milestones](#completed-milestones)
- [CI/CD Pipeline](#cicd-pipeline)
- [Database Backup Strategy](#database-backup-strategy)

## Overview

The platform runs as an **event-driven, asynchronous processing pipeline** built to handle unreliable external APIs, variable processing times, and the need for human oversight on AI-generated content.

The core design pattern is **human-in-the-loop automation** — the system handles email parsing, intent classification, entity extraction, response drafting, and scheduling automatically, but routes every AI-generated response through an approval workflow before it reaches the customer. This keeps throughput high while ensuring nothing goes out without a human sign-off.

### System Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES LAYER                                │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐   ┌────────────────────────┐    │
│  │  Gmail   │   │  Claude  │   │   Telegram   │   │    Google Calendar     │    │
│  │   API    │   │   API    │   │   Bot API    │   │         API            │    │
│  └────┬─────┘   └────┬─────┘   └──────┬───────┘   └───────────┬────────────┘    │
├───────┼──────────────┼────────────────┼───────────────────────┼─────────────────┤
│       │              │                │                       │                  │
│       ▼              ▼                ▼                       ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                      CELERY ASYNC TASK LAYER                            │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │    │
│  │  │ FETCH QUEUE │  │PROCESS QUEUE│  │ SEND QUEUE  │  │CALENDAR QUEUE│   │    │
│  │  │             │  │             │  │             │  │              │   │    │
│  │  │ • Poll Gmail│  │ • Classify  │  │ • Dispatch  │  │ • Create     │   │    │
│  │  │ • Parse MIME│  │ • Extract   │  │ • Retry     │  │ • Sync       │   │    │
│  │  │ • Dedup     │  │ • Generate  │  │ • Thread    │  │ • Conflicts  │   │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘   │    │
│  │         │                │                │                │           │    │
│  │         └────────────────┴────────┬───────┴────────────────┘           │    │
│  │                                   │                                     │    │
│  │                          ┌────────▼────────┐                           │    │
│  │                          │  REDIS BROKER   │                           │    │
│  │                          │  • Task Queue   │                           │    │
│  │                          │  • Pub/Sub      │                           │    │
│  │                          │  • Rate Limits  │                           │    │
│  │                          └────────┬────────┘                           │    │
│  └───────────────────────────────────┼─────────────────────────────────────┘    │
│                                      │                                          │
├──────────────────────────────────────┼──────────────────────────────────────────┤
│                    APPROVAL WORKFLOW │ (Human-in-the-Loop)                      │
│           ┌──────────────────────────┴──────────────────────────┐               │
│           │                                                      │               │
│    ┌──────▼──────┐                                      ┌───────▼───────┐       │
│    │ TELEGRAM BOT │                                      │ WEB DASHBOARD │       │
│    │              │                                      │               │       │
│    │ • Push Notif │                                      │ • React SPA   │       │
│    │ • Inline KB  │◄────────── APPROVE ─────────────────►│ • JWT Auth    │       │
│    │ • /pending   │◄────────── REJECT ──────────────────►│ • Role-based  │       │
│    │ • /calendar  │◄────────── EDIT ────────────────────►│ • Analytics   │       │
│    └──────────────┘                                      └───────────────┘       │
│                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────┤
│                            PERSISTENCE LAYER                                     │
│    ┌─────────────────────────────────────────────────────────────────────┐      │
│    │                        POSTGRESQL 15                                 │      │
│    │   emails │ entities │ responses │ calendar_events │ users │ config  │      │
│    └─────────────────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## Key Capabilities

### AI & NLP Integration
- **Multi-stage LLM Pipeline** — Intent classification → entity extraction (NER) → context-aware response generation, all powered by Claude API
- **Prompt Engineering** — Configurable brand voice, pricing rules, and business context injected into generation prompts
- **Structured Output Parsing** — Reliable extraction of typed entities (dates, property types, service categories) from unstructured email text

### Distributed Systems & Backend
- **Celery Task Architecture** — Dedicated queues (fetch, process, send, calendar) with configurable concurrency, retry policies, and dead-letter handling
- **Event-Driven Processing** — Redis Pub/Sub for inter-service communication; Beat scheduler for periodic jobs (email polling, calendar sync)
- **Database Design** — PostgreSQL with raw SQL (psycopg2), connection pooling, JSONB for flexible config storage, and proper transaction management

### Full-Stack Development
- **React + TypeScript SPA** — Vite build system, TanStack Query for server state, TailwindCSS, Recharts for analytics visualization
- **Flask REST API** — Blueprint-based routing, JWT authentication with refresh tokens, Redis-backed token blacklisting
- **Role-Based Access Control** — Admin/operator/viewer roles with decorator-based route protection

### External Service Integration
- **Gmail API** — OAuth 2.0 flow, incremental sync with deduplication, threaded reply dispatch, attachment handling
- **Google Calendar API** — Bidirectional sync (system→calendar + calendar→system), conflict detection with admin notifications
- **Telegram Bot API** — Real-time notifications, inline keyboard callbacks, conversational edit workflow

### Production Infrastructure
- **Docker Compose Orchestration** — 7-container deployment with health checks, named volumes, and network isolation
- **CI/CD Pipeline** — GitHub Actions with 5 parallel jobs (lint, test, build, integration, security), Dependabot for dependency updates
- **Database Backup System** — Hourly pg_dump with checksums, automated verification, Telegram alerts on failure, and one-command restore
- **Resilience Patterns** — Exponential backoff retry logic, circuit breaker considerations, graceful degradation
- **Security Hardening** — Non-root containers, rate limiting, input validation, parameterized queries, CORS configuration

## Tech Stack

| Layer | Technology |
|-------|------------|
| AI | Anthropic Claude API (claude-sonnet-4-20250514) |
| Backend API | Flask, Gunicorn, PyJWT, bcrypt |
| Frontend | React 18, TypeScript, Vite, TailwindCSS, TanStack Query, Recharts |
| Task Queue | Celery with Redis broker, Celery Beat scheduler |
| Database | PostgreSQL 15 (raw SQL via psycopg2, connection pooling) |
| Cache/Queue | Redis 7 (task broker, rate limiting, token blacklist) |
| Email | Gmail API (OAuth 2.0) |
| Calendar | Google Calendar API (two-way sync) |
| Notifications | Telegram Bot API |
| Infrastructure | Docker, Docker Compose (7 containers), nginx |
| CI/CD | GitHub Actions (lint, test, build, security audit), Dependabot |
| Backup | pg_dump (hourly), Redis RDB (daily), SHA256 verification |
| Testing | pytest, pytest-cov, ruff (linter + formatter) |

### End-to-End Flow

```
Email Received → AI Processing → Draft Created → Telegram Notification
                                                         ↓
                                              Admin Reviews (Approve/Reject/Edit)
                                              via Telegram or Web Dashboard
                                                         ↓
                                              Approved → Email Sent
                                                         ↓
                                              Parse Date/Time from Entities
                                                         ↓
                                            ┌────────────┴────────────┐
                                            ↓                         ↓
                                     Has Conflict              No Conflict
                                            ↓                         ↓
                                  Telegram Alert             Create Calendar
                                  [Force][Skip]              Event in Google
                                                                  ↓
                                                         Telegram Confirmation

                    ┌──────────────────────────────────────────────┐
                    │   Inbound Sync (every 5 min via Celery Beat) │
                    │   Google Calendar → DB → Telegram Alert      │
                    └──────────────────────────────────────────────┘
```

## Project Structure

```
EcoClean_Email_Automation/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # CI pipeline (lint, test, build, security)
│   │   └── docker-build.yml    # Docker image builds with layer caching
│   └── dependabot.yml          # Automated dependency updates
├── docker-compose.yml          # 7-container orchestration
├── docker-compose.backup.yml   # Backup services (pg-backup, redis-backup)
├── Dockerfile                  # Celery worker/services image
├── pyproject.toml              # Python tooling config (pytest, ruff, coverage)
├── requirements.txt            # Python dependencies (workers)
├── backend/                    # Flask REST API (Gunicorn)
│   ├── auth/                   # JWT auth, decorators, bcrypt
│   ├── middleware/              # Error handling, rate limiting, logging
│   ├── routes/                 # API endpoint blueprints
│   └── schemas/                # Request validation
├── frontend/                   # React 18 + TypeScript + Vite + TailwindCSS
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── pages/              # Page components
│   │   ├── hooks/              # Custom React hooks
│   │   └── utils/              # API clients and helpers
│   └── nginx.conf              # SPA routing config
├── database/                   # PostgreSQL layer
│   ├── connection.py           # psycopg2 connection pooling
│   ├── migrations/             # Raw SQL migrations (001–005)
│   └── queries/                # SQL query modules per domain
├── services/                   # Business logic
│   ├── claude/                 # AI pipeline (classify → extract → respond)
│   ├── gmail/                  # Gmail OAuth + MIME parsing
│   ├── calendar/               # Google Calendar two-way sync
│   ├── telegram/               # Bot commands + notifications
│   ├── tasks/                  # Celery async tasks
│   └── celery_app.py           # Celery config + Beat schedule
├── config/                     # Dataclass-based settings
├── scripts/
│   ├── backup/                 # Backup & restore scripts
│   │   ├── pg_backup.sh        # Hourly PostgreSQL dump (custom format)
│   │   ├── pg_restore.sh       # Restore with verification + safety prompts
│   │   ├── backup_verify.sh    # Integrity checks + Telegram alerts
│   │   └── backup_cleanup.sh   # Retention-based rotation
│   └── ...                     # DB init, OAuth setup, utilities
└── tests/                      # pytest suite (unit + integration)
```

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and POSTGRES_PASSWORD at minimum

# 2. Start all services (7 containers)
docker-compose up -d

# 3. Initialize database
python scripts/init_db.py
```

Dashboard: [http://localhost:3000](http://localhost:3000) — Login with `admin` / `changeme`

For detailed setup including Gmail API, Telegram Bot, Google Calendar integration, and all configuration options, see **[docs/SETUP.md](docs/SETUP.md)**.

## Testing

```bash
pytest                                    # Run all tests
pytest --cov --cov-fail-under=80          # With coverage (80% minimum enforced)
pytest -m "not integration"               # Unit tests only
ruff check .                              # Lint check
ruff format --check .                     # Format check
```

Covers: email classification, MIME parsing, database CRUD, email sending, Celery tasks, quote generation, Telegram bot handlers, and configuration validation.

All checks run automatically on every push and PR via GitHub Actions CI.

## API Reference

Flask REST API at `http://localhost:5000` — JWT Bearer token required on all endpoints except `/api/health` and `/api/auth/login`.

**Endpoint groups:** Authentication, Emails, Responses (approve/reject/edit/retry), Calendar, Configuration, Statistics, Health.

Full endpoint documentation: **[docs/API.md](docs/API.md)**

## Completed Milestones

### Phase 1 — Database & AI Pipeline
- [x] PostgreSQL + Redis via Docker
- [x] Database migrations system with raw SQL
- [x] Claude API classification, entity extraction, response generation
- [x] Sample email test suite

### Phase 2 — Gmail Integration
- [x] OAuth 2.0 authentication flow
- [x] Email fetching, parsing, and storage
- [x] Celery task queue with Beat scheduler

### Phase 3 — Telegram Bot
- [x] Admin notifications with inline action buttons
- [x] Approve/reject/edit workflow
- [x] `/pending`, `/stats`, `/help` commands

### Phase 4 — Google Calendar
- [x] Two-way sync (outbound event creation + inbound polling)
- [x] Conflict detection with Telegram alerts
- [x] Natural language date/time parsing
- [x] `/calendar` command for upcoming events

### Phase 5 — Web Dashboard & CRM
- [x] Flask REST API with JWT authentication
- [x] React + TypeScript + TailwindCSS frontend
- [x] Role-based access control (admin, operator, viewer)
- [x] Response management via web dashboard
- [x] Email search, filtering, and pagination
- [x] Dashboard analytics with charts
- [x] Business configuration management
- [x] Calendar event viewer
- [x] Abstract CRM interface (`BaseCRMProvider`)
- [x] Vendor-agnostic data models and exception hierarchy
- [x] Null provider (no-op default) and factory function

### Phase 6 — CI/CD & Backup Strategy
- [x] GitHub Actions CI pipeline (lint, test, frontend build, security audit)
- [x] Docker image build workflow with GHA layer caching
- [x] Dependabot for automated dependency updates (pip, npm, Docker, Actions)
- [x] Ruff linter + formatter with PEP 8, import sorting, and bugbear rules
- [x] PostgreSQL backup system (hourly pg_dump, SHA256 checksums, retention rotation)
- [x] Redis backup system (daily RDB snapshots)
- [x] Backup verification with Telegram alerts on failure
- [x] Restore script with checksum verification and safety prompts
- [x] Backup Docker Compose overlay with profile-based services

### Production Preparation
- [x] Non-root Docker users in all containers
- [x] Health checks on all services
- [x] Security headers in nginx
- [x] Rate limiting on API endpoints
- [x] Token blacklisting for logout
- [x] Input validation on all routes
- [x] Comprehensive test suite

## CI/CD Pipeline

GitHub Actions runs **5 parallel jobs** on every push to `main` and every PR:

| Job | What it does |
|-----|-------------|
| **Lint** | `ruff check` + `ruff format --check` |
| **Test** | `pytest` with 80% coverage minimum |
| **Integration Test** | PostgreSQL 15 + Redis 7 service containers, runs migrations |
| **Frontend** | `npm ci` + `tsc -b && vite build` |
| **Security** | `pip-audit` on all requirements files |

A separate **Docker Build** workflow builds all 3 images in parallel with layer caching.

**Dependabot** scans weekly for pip/npm/Actions updates and monthly for Docker base image updates.

## Database Backup Strategy

| Metric | Target | Rationale |
|--------|--------|-----------|
| **RPO** | 1 hour | Hourly `pg_dump`; emails can be re-fetched from Gmail |
| **RTO** | 30 minutes | Stop services, restore dump, restart |

### Running Backups

```bash
# PostgreSQL backup (run hourly via cron)
docker compose -f docker-compose.yml -f docker-compose.backup.yml run --rm pg-backup

# Redis backup (run daily via cron)
docker compose -f docker-compose.yml -f docker-compose.backup.yml run --rm redis-backup

# Verify latest backup integrity
bash scripts/backup/backup_verify.sh

# Restore from latest backup (interactive, requires confirmation)
bash scripts/backup/pg_restore.sh --latest

# Verify a backup without restoring
bash scripts/backup/pg_restore.sh --verify-only --latest
```

### Recommended Crontab

```cron
0 * * * *   cd /path/to/project && docker compose -f docker-compose.yml -f docker-compose.backup.yml run --rm pg-backup
0 3 * * *   cd /path/to/project && docker compose -f docker-compose.yml -f docker-compose.backup.yml run --rm redis-backup
0 4 * * *   bash /path/to/project/scripts/backup/backup_verify.sh
0 5 * * 0   bash /path/to/project/scripts/backup/backup_cleanup.sh
```

### Retention Policy

| Type | Frequency | Local Retention |
|------|-----------|----------------|
| PostgreSQL dump | Hourly | 7 days |
| Redis RDB | Daily | 7 days |

S3 offsite upload is supported via `UPLOAD_S3=true` + `AWS_S3_BUCKET` environment variables.

## License

Copyright (c) 2025 Jacob Khorshid. All rights reserved.
