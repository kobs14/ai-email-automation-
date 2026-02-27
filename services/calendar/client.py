"""
Google Calendar API client.

Wraps the Google Calendar API for creating, reading, and managing events.
Handles API errors with proper logging and retry logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import settings

logger = logging.getLogger(__name__)


class CalendarClient:
    """
    Google Calendar API wrapper.

    Provides methods for creating events, checking conflicts,
    and syncing events from Google Calendar.

    Usage:
        from services.calendar.auth import get_calendar_credentials
        from services.calendar.client import CalendarClient

        creds = get_calendar_credentials()
        client = CalendarClient(creds)
        event = client.create_event(event_body)
    """

    def __init__(self, credentials):
        """
        Initialize the Calendar client.

        Args:
            credentials: Valid Google OAuth credentials with calendar scope
        """
        self.service = build("calendar", "v3", credentials=credentials)
        self.calendar_id = settings.calendar.calendar_id

    def create_event(self, event_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new event in Google Calendar.

        Args:
            event_body: Event resource body per Google Calendar API spec.
                Must include 'summary', 'start', and 'end' at minimum.

        Returns:
            Created event resource from Google Calendar API

        Raises:
            HttpError: If the API call fails
        """
        try:
            event = (
                self.service.events()
                .insert(
                    calendarId=self.calendar_id,
                    body=event_body,
                )
                .execute()
            )

            logger.info(f"Created calendar event: {event.get('id')} - {event.get('summary', 'No title')}")
            return event

        except HttpError as e:
            logger.error(f"Failed to create calendar event: {e}")
            raise

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single event by its ID.

        Args:
            event_id: Google Calendar event ID

        Returns:
            Event resource or None if not found
        """
        try:
            event = (
                self.service.events()
                .get(
                    calendarId=self.calendar_id,
                    eventId=event_id,
                )
                .execute()
            )
            return event

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Calendar event {event_id} not found")
                return None
            logger.error(f"Failed to get calendar event {event_id}: {e}")
            raise

    def get_events_in_range(
        self,
        time_min: datetime,
        time_max: datetime,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get events within a time range.

        Used for conflict checking and viewing upcoming events.

        Args:
            time_min: Start of time range (inclusive)
            time_max: End of time range (inclusive)
            max_results: Maximum number of events to return

        Returns:
            List of event resources
        """
        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=time_min.isoformat() + "Z",
                    timeMax=time_max.isoformat() + "Z",
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            logger.debug(f"Found {len(events)} events between {time_min.isoformat()} and {time_max.isoformat()}")
            return events

        except HttpError as e:
            logger.error(f"Failed to list calendar events: {e}")
            raise

    def get_upcoming_events(
        self,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming events starting from now.

        Args:
            max_results: Maximum number of events to return

        Returns:
            List of upcoming event resources
        """
        now = datetime.utcnow().isoformat() + "Z"

        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            return events_result.get("items", [])

        except HttpError as e:
            logger.error(f"Failed to get upcoming events: {e}")
            raise

    def list_events_since(
        self,
        updated_min: Optional[datetime] = None,
        sync_token: Optional[str] = None,
        max_results: int = 100,
        _is_fallback: bool = False,
    ) -> Dict[str, Any]:
        """
        List events modified since a given time or using a sync token.

        Used for incremental sync from Google Calendar to database.

        Args:
            updated_min: Only return events modified after this time.
                Ignored if sync_token is provided.
            sync_token: Token from a previous sync for incremental updates
            max_results: Maximum number of events to return
            _is_fallback: Internal flag to prevent infinite recursion on 410

        Returns:
            Dict with keys:
                - 'items': List of event resources
                - 'next_sync_token': Token for next incremental sync
        """
        try:
            kwargs = {
                "calendarId": self.calendar_id,
                "maxResults": max_results,
            }

            if sync_token:
                # syncToken is incompatible with singleEvents per Google API docs
                kwargs["syncToken"] = sync_token
            elif updated_min:
                kwargs["updatedMin"] = updated_min.isoformat() + "Z"
                kwargs["orderBy"] = "updated"
                kwargs["singleEvents"] = True
            else:
                # Full sync without filters
                kwargs["singleEvents"] = True

            events_result = self.service.events().list(**kwargs).execute()

            items = events_result.get("items", [])
            next_sync_token = events_result.get("nextSyncToken")

            logger.info(
                f"Sync returned {len(items)} events, next_sync_token={'present' if next_sync_token else 'none'}"
            )

            return {
                "items": items,
                "next_sync_token": next_sync_token,
            }

        except HttpError as e:
            if e.resp.status == 410 and not _is_fallback:
                # Sync token expired, need full sync (only retry once)
                logger.warning("Sync token expired (410 Gone). Falling back to full sync.")
                return self.list_events_since(
                    updated_min=None,
                    sync_token=None,
                    max_results=max_results,
                    _is_fallback=True,
                )
            logger.error(f"Failed to list events for sync: {e}")
            raise

    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event from Google Calendar.

        Args:
            event_id: Google Calendar event ID

        Returns:
            True if deletion succeeded
        """
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id,
            ).execute()

            logger.info(f"Deleted calendar event: {event_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Calendar event {event_id} not found for deletion")
                return False
            logger.error(f"Failed to delete calendar event {event_id}: {e}")
            raise

    def update_event(
        self,
        event_id: str,
        event_body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing event in Google Calendar.

        Args:
            event_id: Google Calendar event ID
            event_body: Updated event resource body

        Returns:
            Updated event resource

        Raises:
            HttpError: If the API call fails
        """
        try:
            event = (
                self.service.events()
                .update(
                    calendarId=self.calendar_id,
                    eventId=event_id,
                    body=event_body,
                )
                .execute()
            )

            logger.info(f"Updated calendar event: {event_id}")
            return event

        except HttpError as e:
            logger.error(f"Failed to update calendar event {event_id}: {e}")
            raise
