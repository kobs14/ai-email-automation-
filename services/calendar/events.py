"""
Calendar event building and conflict checking.

Constructs Google Calendar event bodies from response data and
extracted entities. Checks for scheduling conflicts with existing events.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from config.settings import settings
from services.calendar.date_parser import DateParser

logger = logging.getLogger(__name__)

# Duration estimates by service type (hours)
_SERVICE_DURATIONS = {
    'deep_clean': 4.0,
    'deep clean': 4.0,
    'standard_clean': 3.0,
    'standard clean': 3.0,
    'regular_clean': 2.5,
    'regular clean': 2.5,
    'move_in': 5.0,
    'move_out': 5.0,
    'move in': 5.0,
    'move out': 5.0,
    'move-in': 5.0,
    'move-out': 5.0,
    'office_clean': 3.0,
    'office clean': 3.0,
    'carpet_clean': 2.0,
    'carpet clean': 2.0,
    'window_clean': 2.0,
    'window clean': 2.0,
}


def _estimate_duration(service_type: Optional[str]) -> float:
    """
    Estimate cleaning duration based on service type.

    Args:
        service_type: Type of cleaning service

    Returns:
        Duration in hours
    """
    if service_type:
        key = service_type.strip().lower()
        if key in _SERVICE_DURATIONS:
            return _SERVICE_DURATIONS[key]
    return settings.calendar.default_duration_hours


class EventBuilder:
    """
    Builds Google Calendar event bodies from response and entity data.

    Usage:
        builder = EventBuilder()
        event_body = builder.build_from_entities(
            entities={'contact_name': 'John', 'service_type': 'Deep Clean', ...},
            response_id=123,
        )
    """

    def __init__(self):
        """Initialize the event builder."""
        self.date_parser = DateParser()
        self.timezone = settings.calendar.timezone

    def build_from_entities(
        self,
        entities: Dict[str, str],
        response_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build a Google Calendar event body from extracted entities.

        Args:
            entities: Dict mapping entity type to value, e.g.:
                {
                    'contact_name': 'John Smith',
                    'contact_phone': '(555) 123-4567',
                    'address': '123 Oak Street',
                    'service_type': 'Deep Clean',
                    'requested_date': 'next Tuesday',
                    'requested_time': '2pm',
                    'property_type': 'House',
                    'bedrooms': '3',
                    'bathrooms': '2',
                    'special_requests': 'Pet-friendly products',
                    'estimated_price': '$250',
                }
            response_id: Optional database response ID for reference

        Returns:
            Google Calendar event body dict, or None if date/time can't be parsed
        """
        # Extract date/time
        date_str = (
            entities.get('requested_date')
            or entities.get('preferred_date')
        )
        time_str = (
            entities.get('requested_time')
            or entities.get('preferred_time')
        )

        service_type = entities.get('service_type', 'Cleaning')
        duration = _estimate_duration(service_type)

        parsed = self.date_parser.parse_booking_datetime(
            date_str=date_str,
            time_str=time_str,
            duration_hours=duration,
        )

        if parsed is None:
            logger.warning(
                f"Cannot build event: unable to parse date/time "
                f"(date='{date_str}', time='{time_str}')"
            )
            return None

        start_dt, end_dt = parsed

        # Build event components
        customer_name = entities.get('contact_name', 'Customer')
        title = f"EcoClean - {customer_name} - {service_type}"

        location = entities.get('address', '')

        description = self._build_description(entities, response_id)

        event_body = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': self.timezone,
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': self.timezone,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 60},
                    {'method': 'popup', 'minutes': 1440},  # 24 hours
                ],
            },
        }

        # Add response_id as extended property for sync reference
        if response_id is not None:
            event_body['extendedProperties'] = {
                'private': {
                    'ecoclean_response_id': str(response_id),
                    'ecoclean_source': 'system',
                },
            }

        logger.info(
            f"Built calendar event: '{title}' at {start_dt.isoformat()}"
        )
        return event_body

    def _build_description(
        self,
        entities: Dict[str, str],
        response_id: Optional[int] = None,
    ) -> str:
        """
        Build a formatted description for the calendar event.

        Args:
            entities: Extracted entity dict
            response_id: Optional response ID

        Returns:
            Formatted description string
        """
        lines = []

        if response_id:
            lines.append(f"EcoClean Response #{response_id}")
            lines.append("")

        customer = entities.get('contact_name')
        if customer:
            lines.append(f"Customer: {customer}")

        phone = entities.get('contact_phone')
        if phone:
            lines.append(f"Phone: {phone}")

        email = entities.get('contact_email') or entities.get('email')
        if email:
            lines.append(f"Email: {email}")

        # Property details
        property_type = entities.get('property_type')
        bedrooms = entities.get('bedrooms')
        bathrooms = entities.get('bathrooms')
        if property_type or bedrooms or bathrooms:
            parts = []
            if bedrooms:
                parts.append(f"{bedrooms}BR")
            if bathrooms:
                parts.append(f"{bathrooms}BA")
            if property_type:
                parts.append(property_type)
            lines.append(f"Property: {'/'.join(parts)}")

        service = entities.get('service_type')
        if service:
            lines.append(f"Service: {service}")

        sq_ft = entities.get('square_footage')
        if sq_ft:
            lines.append(f"Size: {sq_ft} sq ft")

        price = entities.get('estimated_price') or entities.get('price')
        if price:
            lines.append(f"Price: {price}")

        notes = entities.get('special_requests')
        if notes:
            lines.append(f"Notes: {notes}")

        return '\n'.join(lines)

    def get_event_time_range(
        self,
        entities: Dict[str, str],
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        Parse just the start/end times from entities without building full event.

        Useful for conflict checking before creating the event.

        Args:
            entities: Extracted entity dict

        Returns:
            Tuple of (start, end) datetimes or None
        """
        date_str = (
            entities.get('requested_date')
            or entities.get('preferred_date')
        )
        time_str = (
            entities.get('requested_time')
            or entities.get('preferred_time')
        )
        service_type = entities.get('service_type')
        duration = _estimate_duration(service_type)

        return self.date_parser.parse_booking_datetime(
            date_str=date_str,
            time_str=time_str,
            duration_hours=duration,
        )


class ConflictChecker:
    """
    Checks for scheduling conflicts with existing calendar events.

    Usage:
        from services.calendar.client import CalendarClient
        checker = ConflictChecker(calendar_client)
        conflicts = checker.check_conflicts(start_dt, end_dt)
    """

    def __init__(self, calendar_client):
        """
        Initialize conflict checker.

        Args:
            calendar_client: CalendarClient instance
        """
        self.client = calendar_client
        self.buffer_minutes = settings.calendar.buffer_minutes

    def check_conflicts(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Check for events that overlap with the proposed time.

        Includes a buffer period before and after the proposed event
        to account for travel/setup time.

        Args:
            start_time: Proposed event start
            end_time: Proposed event end

        Returns:
            List of conflicting event resources (empty if no conflicts)
        """
        buffer = timedelta(minutes=self.buffer_minutes)
        check_start = start_time - buffer
        check_end = end_time + buffer

        existing_events = self.client.get_events_in_range(
            time_min=check_start,
            time_max=check_end,
        )

        conflicts = []
        for event in existing_events:
            event_start = self._parse_event_time(event.get('start', {}))
            event_end = self._parse_event_time(event.get('end', {}))

            if event_start is None or event_end is None:
                continue

            # Check overlap (event overlaps if it doesn't end before or start after)
            if event_start < end_time and event_end > start_time:
                conflicts.append(event)

        if conflicts:
            logger.info(
                f"Found {len(conflicts)} conflicting events for "
                f"{start_time.isoformat()} - {end_time.isoformat()}"
            )

        return conflicts

    def format_conflicts(
        self,
        conflicts: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """
        Format conflict events into a human-readable summary.

        Args:
            conflicts: List of conflicting event resources

        Returns:
            List of dicts with 'title', 'start', 'end' keys
        """
        formatted = []
        for event in conflicts:
            start = self._parse_event_time(event.get('start', {}))
            end = self._parse_event_time(event.get('end', {}))

            formatted.append({
                'title': event.get('summary', 'Untitled'),
                'start': start.strftime('%I:%M %p') if start else 'Unknown',
                'end': end.strftime('%I:%M %p') if end else 'Unknown',
                'event_id': event.get('id', ''),
            })

        return formatted

    def _parse_event_time(
        self,
        time_dict: Dict[str, str],
    ) -> Optional[datetime]:
        """
        Parse a Google Calendar event time object.

        Handles both dateTime (timed events) and date (all-day events).

        Args:
            time_dict: Google Calendar start/end dict with
                'dateTime' or 'date' key

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
            logger.warning(f"Could not parse event time: {dt_str}")
            return None
