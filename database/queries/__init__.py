"""
SQL query modules for the cleaning service email automation system.

Each module contains raw SQL queries as string constants.
All queries use parameterized placeholders (%s) to prevent SQL injection.
"""

from . import calendar, config, emails, entities, responses, stats, users

__all__ = ["emails", "entities", "responses", "config", "calendar", "users", "stats"]
