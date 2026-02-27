"""
Gmail OAuth authentication handler.

Manages OAuth 2.0 flow for Gmail API access, including:
- Initial authorization (opens browser for consent)
- Token storage and refresh
- Credential validation
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Gmail API scopes
# gmail.modify includes read access and ability to mark as read
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]


def _get_default_scopes() -> list:
    """
    Get default OAuth scopes, including calendar if enabled.

    When calendar integration is configured, calendar scopes are
    always included to prevent token scope conflicts between
    services sharing the same token file.

    Returns:
        List of OAuth scope strings
    """
    try:
        from config.settings import settings

        if settings.calendar.is_configured():
            from services.calendar.auth import CALENDAR_SCOPES

            return CALENDAR_SCOPES
    except Exception:
        pass
    return SCOPES


class GmailAuth:
    """
    Handles Gmail OAuth 2.0 authentication.

    Usage:
        auth = GmailAuth(
            credentials_path='credentials/google_credentials.json',
            token_path='credentials/gmail_token.json'
        )
        creds = auth.get_credentials()
    """

    def __init__(
        self,
        credentials_path: str = "credentials/google_credentials.json",
        token_path: str = "credentials/gmail_token.json",
        scopes: Optional[list] = None,
    ):
        """
        Initialize Gmail authentication handler.

        Args:
            credentials_path: Path to OAuth client credentials JSON (from Google Cloud Console)
            token_path: Path to store/load the user's access token
            scopes: Gmail API scopes (defaults to readonly + modify)
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.scopes = scopes or _get_default_scopes()
        self._credentials: Optional[Credentials] = None

    def get_credentials(self) -> Credentials:
        """
        Get valid Gmail API credentials.

        Will attempt to:
        1. Load existing token from file
        2. Refresh expired token
        3. Run OAuth flow if no valid token exists

        Returns:
            Valid Google OAuth credentials

        Raises:
            FileNotFoundError: If credentials file doesn't exist
            Exception: If authorization fails
        """
        # Check if credentials file exists
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"OAuth credentials file not found: {self.credentials_path}\n"
                "Please download it from Google Cloud Console and save it to this location."
            )

        creds = None

        # Try to load existing token
        if self.token_path.exists():
            logger.info(f"Loading existing token from {self.token_path}")
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
                creds = None

        # Check if token needs refresh or re-authorization
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired, refreshing...")
            try:
                creds.refresh(Request())
                self._save_token(creds)
                logger.info("Token refreshed successfully")
            except Exception as e:
                logger.warning(f"Failed to refresh token: {e}")
                creds = None

        # Run OAuth flow if needed
        if not creds or not creds.valid:
            logger.info("No valid credentials, starting OAuth flow...")
            creds = self._run_oauth_flow()
            self._save_token(creds)
            logger.info("OAuth authorization completed successfully")

        self._credentials = creds
        return creds

    def _run_oauth_flow(self) -> Credentials:
        """
        Run the OAuth 2.0 authorization flow.

        Opens a browser window for user to authorize access.

        Returns:
            New OAuth credentials
        """
        flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), self.scopes)

        # Run local server to receive OAuth callback
        # Use port 0 to let the system pick an available port
        creds = flow.run_local_server(
            port=0,
            prompt="consent",
            success_message="Authorization successful! You can close this window.",
            open_browser=True,
        )

        return creds

    def _save_token(self, creds: Credentials) -> None:
        """
        Save credentials to token file using atomic write.

        Writes to a temporary file first, then renames to the target path.
        This prevents corruption when multiple workers save concurrently.

        Args:
            creds: OAuth credentials to save
        """
        # Ensure directory exists
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file, then rename
        fd, tmp_path = tempfile.mkstemp(dir=str(self.token_path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(creds.to_json())
            os.replace(tmp_path, str(self.token_path))
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        logger.info(f"Token saved to {self.token_path}")

    def revoke_credentials(self) -> bool:
        """
        Revoke the current OAuth token.

        Returns:
            True if revocation succeeded
        """
        if not self._credentials:
            logger.warning("No credentials to revoke")
            return False

        try:
            import requests

            requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": self._credentials.token},
                headers={"content-type": "application/x-www-form-urlencoded"},
            )

            # Delete token file
            if self.token_path.exists():
                self.token_path.unlink()
                logger.info(f"Deleted token file: {self.token_path}")

            self._credentials = None
            logger.info("Credentials revoked successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            return False

    def is_authorized(self) -> bool:
        """
        Check if valid credentials exist.

        Returns:
            True if valid, non-expired credentials are available
        """
        if self._credentials and self._credentials.valid:
            return True

        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)
                return creds.valid or (creds.expired and creds.refresh_token)
            except Exception:
                return False

        return False

    @property
    def credentials(self) -> Optional[Credentials]:
        """Get current credentials (may be None if not authorized)."""
        return self._credentials
