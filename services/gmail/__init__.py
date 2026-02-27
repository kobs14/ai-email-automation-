"""
Gmail service package for email ingestion.

Provides OAuth authentication, email fetching, and parsing capabilities.
"""

from .auth import GmailAuth
from .client import GmailClient
from .parser import EmailParser

__all__ = ["GmailAuth", "GmailClient", "EmailParser"]
