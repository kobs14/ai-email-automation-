"""
SQL query modules for the cleaning service email automation system.

Each module contains raw SQL queries as string constants.
All queries use parameterized placeholders (%s) to prevent SQL injection.
"""

from . import emails
from . import entities
from . import responses
from . import config
from . import calendar
from . import users
from . import stats

__all__ = ["emails", "entities", "responses", "config", "calendar", "users", "stats"]
