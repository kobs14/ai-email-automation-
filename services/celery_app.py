"""
Celery application configuration.

Configures Celery with Redis as the message broker and result backend.
Tasks are auto-discovered from the services.tasks package.

Usage:
    # Start worker
    celery -A services.celery_app worker --loglevel=info

    # Start beat scheduler (for periodic tasks)
    celery -A services.celery_app beat --loglevel=info

    # Start both worker and beat
    celery -A services.celery_app worker --beat --loglevel=info
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from celery import Celery
from celery.schedules import crontab

from config.settings import settings

logger = logging.getLogger(__name__)

# Create Celery app
app = Celery('cleaning_email_automation')

# Configuration
app.conf.update(
    # Broker (Redis)
    broker_url=settings.redis.url,
    result_backend=settings.redis.url,

    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Timezone
    timezone=settings.app.timezone,
    enable_utc=True,

    # Task settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit at 4 minutes

    # Result settings
    result_expires=3600,  # Results expire after 1 hour

    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_concurrency=2,  # Number of concurrent workers

    # Task routing (optional - for future scaling)
    task_routes={
        'services.tasks.email_tasks.fetch_emails': {'queue': 'email_fetch'},
        'services.tasks.email_tasks.process_email': {'queue': 'email_process'},
        'services.tasks.email_tasks.send_approved_responses_task': {'queue': 'email_send'},
        'services.tasks.email_tasks.send_single_response_task': {'queue': 'email_send'},
        'services.tasks.calendar_tasks.create_calendar_event_task': {'queue': 'calendar'},
        'services.tasks.calendar_tasks.force_create_calendar_event_task': {'queue': 'calendar'},
        'services.tasks.calendar_tasks.sync_calendar_events_task': {'queue': 'calendar'},
    },

    # Default queue
    task_default_queue='default',
)

# Auto-discover tasks from services.tasks package
app.autodiscover_tasks(['services.tasks'])

# Beat schedule (periodic tasks)
app.conf.beat_schedule = {
    # Fetch new emails every 5 minutes
    'fetch-emails-every-5-minutes': {
        'task': 'services.tasks.email_tasks.fetch_emails_task',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'email_fetch'},
    },

    # Process pending emails every 2 minutes
    'process-pending-emails-every-2-minutes': {
        'task': 'services.tasks.email_tasks.process_pending_emails_task',
        'schedule': crontab(minute='*/2'),
        'options': {'queue': 'email_process'},
    },

    # Send approved responses every 5 minutes
    'send-approved-responses-every-5-minutes': {
        'task': 'services.tasks.email_tasks.send_approved_responses_task',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'email_send'},
    },

    # Sync Google Calendar events every 5 minutes
    'sync-calendar-every-5-minutes': {
        'task': 'services.tasks.calendar_tasks.sync_calendar_events_task',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'calendar'},
    },
}


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
    return {'status': 'ok', 'worker': self.request.hostname}


# Initialize logging when module loads
if __name__ != '__main__':
    settings.configure_logging()
