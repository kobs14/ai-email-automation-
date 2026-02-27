"""
Celery tasks for Google Calendar integration.

Tasks:
- create_calendar_event_task: Create event when email confirmation is sent
- sync_calendar_events_task: Periodic sync from Google Calendar to database
- force_create_calendar_event_task: Force-create event despite conflicts
"""

import json
import logging
from typing import Any, Dict

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from config.settings import settings

logger = logging.getLogger(__name__)


def _get_calendar_client():
    """
    Get an authenticated CalendarClient instance.

    Returns:
        CalendarClient instance

    Raises:
        Exception: If authentication fails or calendar is not configured
    """
    from services.calendar.auth import get_calendar_credentials
    from services.calendar.client import CalendarClient

    creds = get_calendar_credentials()
    return CalendarClient(creds)


@shared_task(
    bind=True,
    name="services.tasks.calendar_tasks.create_calendar_event_task",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def create_calendar_event_task(
    self,
    response_id: int,
) -> Dict[str, Any]:
    """
    Create a Google Calendar event for a sent response.

    This task:
    1. Fetches response and associated entities from database
    2. Parses date/time from extracted entities
    3. Checks for scheduling conflicts
    4. Creates event if no conflicts, or notifies admin if conflicts found
    5. Updates response with calendar status

    Args:
        response_id: Database ID of the sent response

    Returns:
        Dict with creation result
    """
    if not settings.calendar.is_configured():
        logger.debug("Calendar integration not enabled, skipping")
        return {
            "status": "skipped",
            "reason": "calendar_not_enabled",
        }

    logger.info(f"Creating calendar event for response {response_id}")

    try:
        from database.connection import get_database
        from database.queries import calendar as cal_queries
        from database.schema import EntityRepository, ResponseRepository
        from services.calendar.events import ConflictChecker, EventBuilder

        db = get_database()
        response_repo = ResponseRepository(db)
        entity_repo = EntityRepository(db)

        # Get response with email data
        response = response_repo.get_response_with_email(response_id)
        if not response:
            logger.error(f"Response {response_id} not found")
            return {
                "status": "error",
                "response_id": response_id,
                "error": "Response not found",
            }

        # Get extracted entities
        email_id = response["email_id"]
        entities = entity_repo.get_entities_as_dict(email_id)

        if not entities:
            logger.warning(f"No entities found for email {email_id}, cannot create calendar event")
            db.execute_query(
                cal_queries.UPDATE_RESPONSE_CALENDAR_FAILED,
                params=(response_id,),
                fetch="one",
            )
            return {
                "status": "skipped",
                "response_id": response_id,
                "reason": "no_entities",
            }

        # Build the event
        builder = EventBuilder()
        event_body = builder.build_from_entities(
            entities=entities,
            response_id=response_id,
        )

        if event_body is None:
            logger.warning(
                f"Could not build calendar event for response {response_id}: no parseable date/time in entities"
            )
            db.execute_query(
                cal_queries.UPDATE_RESPONSE_CALENDAR_FAILED,
                params=(response_id,),
                fetch="one",
            )
            return {
                "status": "skipped",
                "response_id": response_id,
                "reason": "no_datetime",
            }

        # Check for conflicts
        time_range = builder.get_event_time_range(entities)
        if time_range:
            start_dt, end_dt = time_range
            client = _get_calendar_client()
            checker = ConflictChecker(client)
            conflicts = checker.check_conflicts(start_dt, end_dt)

            if conflicts:
                # Store conflict details and notify admin
                conflict_info = checker.format_conflicts(conflicts)
                conflict_json = json.dumps(conflict_info)

                db.execute_query(
                    cal_queries.UPDATE_RESPONSE_CALENDAR_CONFLICT,
                    params=(conflict_json, response_id),
                    fetch="one",
                )

                # Notify admin via Telegram
                try:
                    from services.telegram.notifications import (
                        notify_calendar_conflict,
                    )

                    notify_calendar_conflict(
                        response_id=response_id,
                        proposed_start=start_dt,
                        proposed_end=end_dt,
                        conflicts=conflict_info,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send conflict notification: {e}")

                return {
                    "status": "conflict",
                    "response_id": response_id,
                    "conflicts": conflict_info,
                }

        # No conflicts - create the event
        client = _get_calendar_client()
        created_event = client.create_event(event_body)

        google_event_id = created_event.get("id")
        event_link = created_event.get("htmlLink", "")

        # Update response with calendar info
        db.execute_query(
            cal_queries.UPDATE_RESPONSE_CALENDAR_STATUS,
            params=(google_event_id, "created", response_id),
            fetch="one",
        )

        # Store in calendar_events table
        start_str = event_body["start"]["dateTime"]
        end_str = event_body["end"]["dateTime"]

        from dateutil import parser as dateutil_parser

        start_dt = dateutil_parser.parse(start_str)
        end_dt = dateutil_parser.parse(end_str)

        db.execute_query(
            cal_queries.INSERT_CALENDAR_EVENT,
            params=(
                google_event_id,
                response_id,
                event_body.get("summary", ""),
                event_body.get("description", ""),
                event_body.get("location", ""),
                start_dt,
                end_dt,
                entities.get("contact_name"),
                entities.get("contact_phone"),
                entities.get("service_type"),
                "system",
                created_event.get("updated"),
                start_dt,  # synced_at
            ),
            fetch="one",
        )

        # Notify admin via Telegram
        try:
            from services.telegram.notifications import (
                notify_calendar_created,
            )

            notify_calendar_created(response_id, event_link)
        except Exception as e:
            logger.warning(f"Failed to send calendar created notification: {e}")

        logger.info(f"Calendar event created for response {response_id}: {google_event_id}")

        return {
            "status": "created",
            "response_id": response_id,
            "google_event_id": google_event_id,
            "event_link": event_link,
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"Calendar task hit soft time limit for response {response_id}")
        raise

    except Exception as e:
        logger.error(f"Failed to create calendar event for response {response_id}: {e}")
        # Mark as failed in DB
        try:
            from database.connection import get_database
            from database.queries import calendar as cal_queries

            db = get_database()
            db.execute_query(
                cal_queries.UPDATE_RESPONSE_CALENDAR_FAILED,
                params=(response_id,),
                fetch="one",
            )
        except Exception:
            pass

        raise


@shared_task(
    bind=True,
    name="services.tasks.calendar_tasks.force_create_calendar_event_task",
    max_retries=2,
    default_retry_delay=30,
)
def force_create_calendar_event_task(
    self,
    response_id: int,
) -> Dict[str, Any]:
    """
    Force-create a calendar event, ignoring conflicts.

    Called when admin chooses "Create Anyway" from conflict notification.

    Args:
        response_id: Database ID of the response

    Returns:
        Dict with creation result
    """
    if not settings.calendar.is_configured():
        return {"status": "skipped", "reason": "calendar_not_enabled"}

    logger.info(f"Force-creating calendar event for response {response_id}")

    try:
        from database.connection import get_database
        from database.queries import calendar as cal_queries
        from database.schema import EntityRepository, ResponseRepository
        from services.calendar.events import EventBuilder

        db = get_database()
        response_repo = ResponseRepository(db)
        entity_repo = EntityRepository(db)

        response = response_repo.get_response_with_email(response_id)
        if not response:
            return {
                "status": "error",
                "response_id": response_id,
                "error": "Response not found",
            }

        email_id = response["email_id"]
        entities = entity_repo.get_entities_as_dict(email_id)

        builder = EventBuilder()
        event_body = builder.build_from_entities(
            entities=entities,
            response_id=response_id,
        )

        if event_body is None:
            return {
                "status": "error",
                "response_id": response_id,
                "error": "Cannot build event (no date/time)",
            }

        # Create event without conflict check
        client = _get_calendar_client()
        created_event = client.create_event(event_body)

        google_event_id = created_event.get("id")
        event_link = created_event.get("htmlLink", "")

        # Update response
        db.execute_query(
            cal_queries.UPDATE_RESPONSE_CALENDAR_STATUS,
            params=(google_event_id, "created", response_id),
            fetch="one",
        )

        # Store in calendar_events
        start_str = event_body["start"]["dateTime"]
        end_str = event_body["end"]["dateTime"]

        from dateutil import parser as dateutil_parser

        start_dt = dateutil_parser.parse(start_str)
        end_dt = dateutil_parser.parse(end_str)

        db.execute_query(
            cal_queries.INSERT_CALENDAR_EVENT,
            params=(
                google_event_id,
                response_id,
                event_body.get("summary", ""),
                event_body.get("description", ""),
                event_body.get("location", ""),
                start_dt,
                end_dt,
                entities.get("contact_name"),
                entities.get("contact_phone"),
                entities.get("service_type"),
                "system",
                created_event.get("updated"),
                start_dt,
            ),
            fetch="one",
        )

        # Notify
        try:
            from services.telegram.notifications import (
                notify_calendar_created,
            )

            notify_calendar_created(response_id, event_link)
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

        return {
            "status": "created",
            "response_id": response_id,
            "google_event_id": google_event_id,
            "event_link": event_link,
            "forced": True,
        }

    except Exception as e:
        logger.error(f"Failed to force-create calendar event for response {response_id}: {e}")
        raise self.retry(exc=e) from e


@shared_task(
    bind=True,
    name="services.tasks.calendar_tasks.sync_calendar_events_task",
    max_retries=2,
    default_retry_delay=120,
)
def sync_calendar_events_task(self) -> Dict[str, Any]:
    """
    Sync events from Google Calendar to database.

    Runs periodically (every 5 minutes via Celery Beat) to import
    new and updated events, including manually-added ones.

    Returns:
        Dict with sync results
    """
    if not settings.calendar.is_configured():
        return {"status": "skipped", "reason": "calendar_not_enabled"}

    logger.info("Starting calendar sync task")

    try:
        from database.connection import get_database
        from services.calendar.sync import CalendarSync

        client = _get_calendar_client()
        db = get_database()
        sync = CalendarSync(client, db)

        result = sync.sync_from_google()

        # Notify admin about manually-added events
        if result.get("manual_events", 0) > 0:
            try:
                # Get recently synced manual events for notification
                from database.queries import calendar as cal_queries
                from services.telegram.notifications import (
                    notify_manual_event_synced,
                )

                manual_events = db.execute_query(
                    cal_queries.GET_MANUAL_EVENTS,
                    params=(result["manual_events"],),
                    fetch="all",
                )
                if manual_events:
                    for event in manual_events:
                        notify_manual_event_synced(dict(event))
            except Exception as e:
                logger.warning(f"Failed to send manual event notification: {e}")

        return {
            "status": "success",
            **result,
        }

    except SoftTimeLimitExceeded:
        logger.warning("Calendar sync task hit soft time limit")
        raise

    except Exception as e:
        logger.error(f"Calendar sync task failed: {e}")
        raise self.retry(exc=e) from e
