"""
Celery tasks package for the cleaning service email automation.

Contains asynchronous tasks for:
- Email fetching from Gmail
- Email processing and classification with Claude
- Entity extraction and storage
- Response generation and storage
- Google Calendar event creation and sync
"""

from .calendar_tasks import (
    create_calendar_event_task,
    force_create_calendar_event_task,
    sync_calendar_events_task,
)
from .email_tasks import (
    fetch_emails_task,
    get_email_repository,
    get_repositories,
    process_pending_emails_task,
    process_single_email_task,
)

__all__ = [
    "fetch_emails_task",
    "process_pending_emails_task",
    "process_single_email_task",
    "get_email_repository",
    "get_repositories",
    "create_calendar_event_task",
    "force_create_calendar_event_task",
    "sync_calendar_events_task",
]
