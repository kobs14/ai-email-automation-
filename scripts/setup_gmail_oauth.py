#!/usr/bin/env python3
"""
Gmail OAuth setup script.

Run this once to authorize the application to access your Gmail account.
It will open a browser window for Google OAuth consent, then save the
token for future use.

Usage:
    python scripts/setup_gmail_oauth.py

Prerequisites:
    1. Download OAuth credentials from Google Cloud Console
    2. Save as credentials/google_credentials.json
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from services.gmail.auth import GmailAuth
from services.gmail.client import GmailClient
from services.calendar.auth import CALENDAR_SCOPES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run Gmail OAuth setup."""
    print("\n" + "=" * 60)
    print("  Gmail OAuth Setup")
    print("=" * 60)

    credentials_path = Path('credentials/google_credentials.json')
    token_path = Path('credentials/gmail_token.json')

    # Check for credentials file
    if not credentials_path.exists():
        print(f"\n❌ Credentials file not found: {credentials_path}")
        print("\nTo fix this:")
        print("1. Go to Google Cloud Console (console.cloud.google.com)")
        print("2. Navigate to APIs & Services → Credentials")
        print("3. Create or download OAuth 2.0 Client ID credentials")
        print("4. Save the JSON file as: credentials/google_credentials.json")
        return 1

    print(f"\n✓ Found credentials file: {credentials_path}")

    # Determine scopes based on calendar setting
    use_calendar = settings.calendar.is_configured()
    if use_calendar:
        scopes = CALENDAR_SCOPES
        print(f"✓ Calendar integration enabled - requesting Gmail + Calendar scopes")
    else:
        scopes = None  # Use default Gmail-only scopes
        print(f"  Calendar integration not enabled (set CALENDAR_ENABLED=true to include)")

    # Check if already authorized
    if token_path.exists():
        print(f"✓ Token file exists: {token_path}")
        response = input("\nRe-authorize? This will replace the existing token. (y/N): ")
        if response.lower() != 'y':
            print("\nKeeping existing authorization.")

            # Test the connection
            print("\nTesting Gmail connection...")
            try:
                auth = GmailAuth(
                    credentials_path=str(credentials_path),
                    token_path=str(token_path),
                    scopes=scopes,
                )
                client = GmailClient(auth)
                profile = client.get_profile()
                print(f"✓ Connected as: {profile['emailAddress']}")
                print(f"  Total messages: {profile.get('messagesTotal', 'N/A')}")
                return 0
            except Exception as e:
                print(f"❌ Connection test failed: {e}")
                print("You may need to re-authorize.")
                return 1

    # Run OAuth flow
    print("\n📋 Starting OAuth authorization...")
    print("   A browser window will open for you to grant access.")
    print("   Make sure you're logged into the correct Google account.\n")

    try:
        auth = GmailAuth(
            credentials_path=str(credentials_path),
            token_path=str(token_path),
            scopes=scopes,
        )

        # This triggers the OAuth flow
        creds = auth.get_credentials()

        if creds and creds.valid:
            print("\n✓ Authorization successful!")
            print(f"✓ Token saved to: {token_path}")

            # Test the connection
            print("\nTesting Gmail connection...")
            client = GmailClient(auth)
            profile = client.get_profile()
            print(f"✓ Connected as: {profile['emailAddress']}")
            print(f"  Total messages: {profile.get('messagesTotal', 'N/A')}")

            # Show some unread emails
            print("\nFetching recent unread emails...")
            unread = client.fetch_unread_emails(max_results=5)
            print(f"  Found {len(unread)} unread email(s)")

            # Get labels
            print("\nAvailable labels:")
            labels = client.get_labels()
            system_labels = [l for l in labels if l.get('type') == 'system']
            user_labels = [l for l in labels if l.get('type') == 'user']

            print(f"  System labels: {len(system_labels)}")
            for label in user_labels[:5]:
                print(f"  - {label['name']}")
            if len(user_labels) > 5:
                print(f"  ... and {len(user_labels) - 5} more")

            print("\n" + "=" * 60)
            print("  Setup Complete!")
            print("=" * 60)
            print("\nYou can now run:")
            print("  python scripts/fetch_emails.py")
            print("\nTo fetch and process incoming emails.")

            return 0

        else:
            print("\n❌ Authorization failed - credentials are invalid")
            return 1

    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        return 1

    except Exception as e:
        print(f"\n❌ Authorization failed: {e}")
        logger.exception("OAuth setup failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
