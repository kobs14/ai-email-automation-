"""
Date and time parser for calendar event scheduling.

Parses natural language dates and times extracted from emails into
concrete datetime objects for Google Calendar events.

Handles:
- Natural language: "next Tuesday", "this Saturday"
- Relative: "tomorrow", "in 3 days"
- Explicit: "January 15, 2024", "1/15/24"
- Time keywords: "morning" -> 9AM, "afternoon" -> 2PM, "evening" -> 5PM
- Fallback: If no time specified, defaults to 9AM
"""

import logging
import re
from datetime import datetime, time, timedelta
from typing import Optional, Tuple

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import FR, MO, SA, SU, TH, TU, WE, relativedelta

from config.settings import settings

logger = logging.getLogger(__name__)

# Maps day names to dateutil weekday constants
_WEEKDAY_MAP = {
    "monday": MO,
    "mon": MO,
    "tuesday": TU,
    "tue": TU,
    "tues": TU,
    "wednesday": WE,
    "wed": WE,
    "thursday": TH,
    "thu": TH,
    "thur": TH,
    "thurs": TH,
    "friday": FR,
    "fri": FR,
    "saturday": SA,
    "sat": SA,
    "sunday": SU,
    "sun": SU,
}

# Maps time keywords to hours
_TIME_KEYWORD_MAP = {
    "morning": time(9, 0),
    "noon": time(12, 0),
    "afternoon": time(14, 0),
    "evening": time(17, 0),
}

DEFAULT_TIME = time(9, 0)


class DateParser:
    """
    Parses date and time strings from extracted email entities.

    Combines separate date and time fields into a single datetime,
    handling natural language and various formats.

    Usage:
        parser = DateParser()
        start, end = parser.parse_booking_datetime(
            date_str="next Tuesday",
            time_str="2pm",
            duration_hours=3.0,
        )
    """

    def __init__(self, timezone: Optional[str] = None):
        """
        Initialize the date parser.

        Args:
            timezone: Timezone string (e.g., 'America/New_York').
                Defaults to CALENDAR_TIMEZONE from settings.
        """
        self.timezone = timezone or settings.calendar.timezone

    def parse_booking_datetime(
        self,
        date_str: Optional[str] = None,
        time_str: Optional[str] = None,
        duration_hours: Optional[float] = None,
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        Parse date and time strings into start/end datetimes.

        Args:
            date_str: Date string (e.g., "next Tuesday", "January 15")
            time_str: Time string (e.g., "2pm", "morning", "14:00")
            duration_hours: Event duration in hours. Defaults to
                CALENDAR_DEFAULT_DURATION from settings.

        Returns:
            Tuple of (start_datetime, end_datetime) or None if parsing fails
        """
        if not date_str and not time_str:
            logger.debug("No date or time provided, cannot parse")
            return None

        duration = duration_hours or settings.calendar.default_duration_hours

        # Parse the date
        parsed_date = self._parse_date(date_str)
        if parsed_date is None and date_str:
            logger.warning(f"Could not parse date: '{date_str}'")
            return None

        # Parse the time
        parsed_time = self._parse_time(time_str)

        # If we only have time but no date, assume next occurrence
        if parsed_date is None and parsed_time is not None:
            now = datetime.now()
            parsed_date = now.date()
            # If the time has already passed today, use tomorrow
            if datetime.combine(parsed_date, parsed_time) <= now:
                parsed_date = (now + timedelta(days=1)).date()

        # If we only have date but no time, use default
        if parsed_date is not None and parsed_time is None:
            parsed_time = DEFAULT_TIME

        if parsed_date is None:
            return None

        start_dt = datetime.combine(parsed_date, parsed_time)
        end_dt = start_dt + timedelta(hours=duration)

        logger.info(
            f"Parsed booking: {start_dt.isoformat()} - {end_dt.isoformat()} (from date='{date_str}', time='{time_str}')"
        )

        return start_dt, end_dt

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse a date string into a date object.

        Handles relative dates, day names, and explicit dates.

        Args:
            date_str: The date string to parse

        Returns:
            Parsed date or None
        """
        if not date_str:
            return None

        text = date_str.strip().lower()
        today = datetime.now().date()

        # Handle relative dates
        if text in ("today", "tonight"):
            return today

        if text in ("tomorrow", "tmrw"):
            return today + timedelta(days=1)

        if text == "day after tomorrow":
            return today + timedelta(days=2)

        # Handle "in X days"
        in_days_match = re.match(r"in\s+(\d+)\s+days?", text)
        if in_days_match:
            days = int(in_days_match.group(1))
            return today + timedelta(days=days)

        # Handle "next <weekday>"
        next_day_match = re.match(r"(?:next|this)\s+(\w+)", text)
        if next_day_match:
            day_name = next_day_match.group(1)
            weekday = _WEEKDAY_MAP.get(day_name)
            if weekday:
                # "next" means the upcoming occurrence (at least 1 day ahead)
                if text.startswith("next"):
                    result = today + relativedelta(weekday=weekday(+1))
                    # Ensure it's at least tomorrow
                    if result <= today:
                        result = today + relativedelta(weekday=weekday(+2))
                    return result
                else:
                    # "this" means this week's occurrence
                    result = today + relativedelta(weekday=weekday(+1))
                    return result

        # Handle bare weekday names (e.g., "Monday")
        if text in _WEEKDAY_MAP:
            weekday = _WEEKDAY_MAP[text]
            result = today + relativedelta(weekday=weekday(+1))
            return result

        # Try dateutil parser for explicit dates
        try:
            parsed = dateutil_parser.parse(date_str, fuzzy=True)
            result = parsed.date()
            # If parsed date is in the past, it might be next year
            if result < today:
                result = result.replace(year=today.year + 1)
            return result
        except (ValueError, OverflowError):
            pass

        logger.debug(f"Could not parse date string: '{date_str}'")
        return None

    def _parse_time(self, time_str: Optional[str]) -> Optional[time]:
        """
        Parse a time string into a time object.

        Handles time keywords (morning, afternoon, evening),
        12-hour format (2pm, 10:30am), and 24-hour format (14:00).

        Args:
            time_str: The time string to parse

        Returns:
            Parsed time or None
        """
        if not time_str:
            return None

        text = time_str.strip().lower()

        # Check keyword map
        if text in _TIME_KEYWORD_MAP:
            return _TIME_KEYWORD_MAP[text]

        # Handle "Xam" / "Xpm" patterns
        ampm_match = re.match(
            r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)",
            text,
        )
        if ampm_match:
            hour = int(ampm_match.group(1))
            minute = int(ampm_match.group(2) or 0)
            period = ampm_match.group(3)

            if period == "pm" and hour != 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0

            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return time(hour, minute)

        # Handle 24-hour format "HH:MM"
        time_24_match = re.match(r"(\d{1,2}):(\d{2})$", text)
        if time_24_match:
            hour = int(time_24_match.group(1))
            minute = int(time_24_match.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return time(hour, minute)

        # Handle bare hour "at 2" / "at 14"
        bare_hour_match = re.match(r"(?:at\s+)?(\d{1,2})$", text)
        if bare_hour_match:
            hour = int(bare_hour_match.group(1))
            if 1 <= hour <= 12:
                # Assume PM for hours 1-6 (business hours), AM for 7-12
                if hour <= 6:
                    hour += 12
                return time(hour, 0)
            elif 13 <= hour <= 23:
                return time(hour, 0)

        # Try dateutil as fallback
        try:
            parsed = dateutil_parser.parse(time_str, fuzzy=True)
            return parsed.time()
        except (ValueError, OverflowError):
            pass

        logger.debug(f"Could not parse time string: '{time_str}'")
        return None
