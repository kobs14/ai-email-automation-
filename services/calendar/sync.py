"""
Two-way calendar sync logic.

Handles:
- Inbound: Import new/updated events from Google Calendar to database
- Outbound: Track which system-created events need syncing

Uses Google Calendar's incremental sync (sync tokens) for efficient polling.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from config.settings import settings

logger = logging.getLogger(__name__)


class CalendarSync:
    """
    Manages two-way sync between Google Calendar and database.

    Usage:
        from services.calendar.client import CalendarClient
        sync = CalendarSync(calendar_client, db)
        result = sync.sync_from_google()
    """

    def __init__(self, calendar_client, db):
        """
        Initialize calendar sync.

        Args:
            calendar_client: CalendarClient instance
            db: Database instance
        """
        self.client = calendar_client
        self.db = db

    def sync_from_google(self) -> Dict[str, Any]:
        """
        Sync events from Google Calendar to database.

        Uses incremental sync tokens when available, falls back to
        time-based query for initial sync.

        Returns:
            Dict with sync results:
                - new_events: Count of new events imported
                - updated_events: Count of existing events updated
                - manual_events: Count of manually-added events found
                - errors: List of error descriptions
        """
        from database.queries import calendar as cal_queries

        result = {
            'new_events': 0,
            'updated_events': 0,
            'manual_events': 0,
            'errors': [],
        }

        # Get sync state
        sync_state = self.db.execute_query(
            cal_queries.GET_SYNC_STATE,
            fetch='one',
        )

        sync_token = sync_state.get('last_sync_token') if sync_state else None
        last_sync = sync_state.get('last_sync_at') if sync_state else None

        # Determine sync approach
        if not sync_token and not last_sync:
            # Initial sync: get events from the last 30 days
            updated_min = datetime.utcnow() - timedelta(days=30)
        else:
            updated_min = last_sync

        # Fetch events from Google
        try:
            sync_result = self.client.list_events_since(
                updated_min=updated_min,
                sync_token=sync_token,
            )
        except Exception as e:
            logger.error(f"Failed to fetch events from Google Calendar: {e}")
            result['errors'].append(f"Google API error: {e}")
            return result

        events = sync_result.get('items', [])
        new_sync_token = sync_result.get('next_sync_token')

        logger.info(f"Sync fetched {len(events)} events from Google Calendar")

        # Process each event
        for event in events:
            try:
                event_result = self._process_synced_event(event)
                if event_result == 'new':
                    result['new_events'] += 1
                elif event_result == 'updated':
                    result['updated_events'] += 1
                elif event_result == 'manual':
                    result['manual_events'] += 1
            except Exception as e:
                event_id = event.get('id', 'unknown')
                logger.error(
                    f"Error processing synced event {event_id}: {e}"
                )
                result['errors'].append(
                    f"Event {event_id}: {e}"
                )

        # Update sync state
        try:
            self.db.execute_query(
                cal_queries.UPDATE_SYNC_STATE,
                params=(new_sync_token, datetime.utcnow()),
                fetch='one',
            )
        except Exception as e:
            logger.error(f"Failed to update sync state: {e}")
            result['errors'].append(f"Sync state update: {e}")

        logger.info(
            f"Calendar sync complete: {result['new_events']} new, "
            f"{result['updated_events']} updated, "
            f"{result['manual_events']} manual, "
            f"{len(result['errors'])} errors"
        )

        return result

    def _process_synced_event(
        self,
        event: Dict[str, Any],
    ) -> str:
        """
        Process a single event from Google Calendar sync.

        Determines if the event is system-created or manual,
        and creates/updates the database record accordingly.

        Args:
            event: Google Calendar event resource

        Returns:
            'new', 'updated', or 'manual' indicating what happened
        """
        from database.queries import calendar as cal_queries

        google_event_id = event.get('id')
        if not google_event_id:
            return 'skipped'

        # Skip cancelled events
        if event.get('status') == 'cancelled':
            logger.debug(f"Skipping cancelled event: {google_event_id}")
            return 'skipped'

        # Check if event already exists in database
        existing = self.db.execute_query(
            cal_queries.GET_CALENDAR_EVENT_BY_GOOGLE_ID,
            params=(google_event_id,),
            fetch='one',
        )

        # Parse event times
        start_time = self._parse_event_datetime(event.get('start', {}))
        end_time = self._parse_event_datetime(event.get('end', {}))

        if start_time is None or end_time is None:
            logger.warning(
                f"Cannot parse times for event {google_event_id}, skipping"
            )
            return 'skipped'

        # Check extended properties for our response_id marker
        ext_props = event.get('extendedProperties', {}).get('private', {})
        response_id_str = ext_props.get('ecoclean_response_id')
        source = ext_props.get('ecoclean_source', 'manual')

        response_id = None
        if response_id_str:
            try:
                response_id = int(response_id_str)
            except (ValueError, TypeError):
                pass

        google_updated = event.get('updated')

        if existing:
            # Update existing event
            self.db.execute_query(
                cal_queries.UPDATE_CALENDAR_EVENT,
                params=(
                    event.get('summary', ''),
                    event.get('description', ''),
                    event.get('location', ''),
                    start_time,
                    end_time,
                    google_updated,
                    datetime.utcnow(),
                    google_event_id,
                ),
                fetch='one',
            )
            return 'updated'

        else:
            # Determine source
            is_manual = source != 'system'

            # Create new calendar_events record
            self.db.execute_query(
                cal_queries.INSERT_CALENDAR_EVENT,
                params=(
                    google_event_id,
                    response_id,
                    event.get('summary', ''),
                    event.get('description', ''),
                    event.get('location', ''),
                    start_time,
                    end_time,
                    self._extract_customer_name(event),
                    None,  # customer_phone
                    self._extract_service_type(event),
                    'manual' if is_manual else 'system',
                    google_updated,
                    datetime.utcnow(),
                ),
                fetch='one',
            )

            if is_manual:
                logger.info(
                    f"Imported manual event: {event.get('summary', 'Untitled')} "
                    f"at {start_time.isoformat()}"
                )
                return 'manual'

            return 'new'

    def _parse_event_datetime(
        self,
        time_dict: Dict[str, str],
    ) -> Optional[datetime]:
        """
        Parse a Google Calendar event time object into datetime.

        Args:
            time_dict: Dict with 'dateTime' or 'date' key

        Returns:
            Parsed datetime or None
        """
        dt_str = time_dict.get('dateTime') or time_dict.get('date')
        if not dt_str:
            return None

        try:
            from dateutil import parser as dateutil_parser
            return dateutil_parser.parse(dt_str)
        except (ValueError, OverflowError):
            return None

    def _extract_customer_name(
        self,
        event: Dict[str, Any],
    ) -> Optional[str]:
        """
        Try to extract a customer name from the event summary.

        Looks for patterns like "EcoClean - John Smith - Deep Clean"
        or just returns the full summary for manual events.

        Args:
            event: Google Calendar event resource

        Returns:
            Customer name string or None
        """
        summary = event.get('summary', '')
        if not summary:
            return None

        # Check for our format: "EcoClean - Customer - Service"
        parts = summary.split(' - ')
        if len(parts) >= 2 and parts[0].strip().lower() == 'ecoclean':
            return parts[1].strip()

        return None

    def _extract_service_type(
        self,
        event: Dict[str, Any],
    ) -> Optional[str]:
        """
        Try to extract service type from event summary.

        Args:
            event: Google Calendar event resource

        Returns:
            Service type string or None
        """
        summary = event.get('summary', '')
        if not summary:
            return None

        parts = summary.split(' - ')
        if len(parts) >= 3 and parts[0].strip().lower() == 'ecoclean':
            return parts[2].strip()

        return None
