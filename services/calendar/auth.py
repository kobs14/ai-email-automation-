"""
Google Calendar OAuth authentication.

Extends the existing Gmail OAuth flow to include Calendar scopes.
When calendar is enabled, the token must include calendar.events scope.
Users will need to re-authorize (delete existing token) when first enabling
calendar integration.
"""

import logging
from typing import Optional

from google.oauth2.credentials import Credentials

from services.gmail.auth import GmailAuth

logger = logging.getLogger(__name__)

# Combined scopes for Gmail + Calendar
CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.events',
]


def get_calendar_credentials(
    credentials_path: str = 'credentials/google_credentials.json',
    token_path: str = 'credentials/gmail_token.json',
) -> Credentials:
    """
    Get OAuth credentials with both Gmail and Calendar scopes.

    Uses the existing GmailAuth class with extended scopes.
    If the current token doesn't include calendar scopes, the user
    will be prompted to re-authorize.

    Args:
        credentials_path: Path to OAuth client credentials JSON
        token_path: Path to store/load the user's access token

    Returns:
        Valid Google OAuth credentials with calendar scope

    Raises:
        FileNotFoundError: If credentials file doesn't exist
        Exception: If authorization fails
    """
    auth = GmailAuth(
        credentials_path=credentials_path,
        token_path=token_path,
        scopes=CALENDAR_SCOPES,
    )
    return auth.get_credentials()


def has_calendar_scope(
    token_path: str = 'credentials/gmail_token.json',
) -> bool:
    """
    Check if the existing token includes calendar scope.

    Args:
        token_path: Path to the token file

    Returns:
        True if the token includes calendar.events scope
    """
    from pathlib import Path

    token_file = Path(token_path)
    if not token_file.exists():
        return False

    try:
        creds = Credentials.from_authorized_user_file(
            str(token_file),
            CALENDAR_SCOPES,
        )
        return creds.valid or (creds.expired and creds.refresh_token)
    except Exception as e:
        logger.debug(f"Token does not include calendar scope: {e}")
        return False
