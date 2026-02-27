"""
Database package for the cleaning service email automation system.

Provides:
- Connection pooling via psycopg2
- Raw SQL query modules
- Repository classes for data access
- Migration utilities
"""

from .connection import Database
from .schema import (
    ConfigRepository,
    EmailRepository,
    EntityRepository,
    ResponseRepository,
    UserRepository,
)

__all__ = [
    "Database",
    "EmailRepository",
    "EntityRepository",
    "ResponseRepository",
    "ConfigRepository",
    "UserRepository",
]
