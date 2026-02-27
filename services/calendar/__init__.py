"""
Google Calendar integration for EcoClean Email Automation.

Provides two-way sync between the email automation system and Google Calendar:
- Outbound: Create booking events when confirmation emails are sent
- Inbound: Sync manually-added Google Calendar events back to database
"""

from services.calendar.auth import get_calendar_credentials
from services.calendar.client import CalendarClient
from services.calendar.date_parser import DateParser
from services.calendar.events import ConflictChecker, EventBuilder

__all__ = [
    "get_calendar_credentials",
    "CalendarClient",
    "DateParser",
    "EventBuilder",
    "ConflictChecker",
]
