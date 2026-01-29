"""
Gmail API client for fetching and managing emails.

Provides methods to:
- List emails with various filters
- Fetch full email content
- Mark emails as read
- Get email metadata
- Send emails and replies
"""

import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from .auth import GmailAuth

logger = logging.getLogger(__name__)


class GmailClient:
    """
    Gmail API client for email operations.

    Usage:
        auth = GmailAuth()
        client = GmailClient(auth)

        # Fetch unread emails
        emails = client.fetch_unread_emails(max_results=10)

        # Get full email content
        for email in emails:
            full_email = client.get_email(email['id'])
    """

    def __init__(self, auth: GmailAuth):
        """
        Initialize Gmail client.

        Args:
            auth: GmailAuth instance for authentication
        """
        self.auth = auth
        self._service = None

    @property
    def service(self):
        """
        Get the Gmail API service (lazy initialization).

        Returns:
            Gmail API service resource
        """
        if self._service is None:
            creds = self.auth.get_credentials()
            self._service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API service initialized")
        return self._service

    def fetch_unread_emails(
        self,
        max_results: int = 10,
        label_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch unread emails from inbox.

        Args:
            max_results: Maximum number of emails to fetch
            label_ids: Filter by label IDs (default: INBOX, UNREAD)

        Returns:
            List of email metadata dicts with 'id', 'threadId'
        """
        if label_ids is None:
            label_ids = ['INBOX', 'UNREAD']

        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=label_ids,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} unread emails")
            return messages

        except HttpError as e:
            logger.error(f"Gmail API error fetching emails: {e}")
            raise

    def fetch_emails_with_query(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails matching a Gmail search query.

        Args:
            query: Gmail search query (e.g., "from:customer@example.com", "subject:quote")
            max_results: Maximum number of emails to fetch

        Returns:
            List of email metadata dicts

        Examples:
            # Emails from specific sender
            client.fetch_emails_with_query("from:john@example.com")

            # Emails with specific subject
            client.fetch_emails_with_query("subject:cleaning quote")

            # Unread emails from last 7 days
            client.fetch_emails_with_query("is:unread newer_than:7d")
        """
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Query '{query}' returned {len(messages)} emails")
            return messages

        except HttpError as e:
            logger.error(f"Gmail API error with query: {e}")
            raise

    def get_email(self, message_id: str, format: str = 'full') -> Dict[str, Any]:
        """
        Get full email content by ID.

        Args:
            message_id: Gmail message ID
            format: Response format ('full', 'metadata', 'minimal', 'raw')

        Returns:
            Full email data including headers, body, attachments info
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format=format
            ).execute()

            logger.debug(f"Fetched email {message_id}")
            return message

        except HttpError as e:
            logger.error(f"Gmail API error fetching email {message_id}: {e}")
            raise

    def get_email_metadata(self, message_id: str) -> Dict[str, Any]:
        """
        Get email metadata only (headers, no body).

        Args:
            message_id: Gmail message ID

        Returns:
            Email metadata including headers
        """
        return self.get_email(message_id, format='metadata')

    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark an email as read (remove UNREAD label).

        Args:
            message_id: Gmail message ID

        Returns:
            True if successful
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            logger.debug(f"Marked email {message_id} as read")
            return True

        except HttpError as e:
            logger.error(f"Gmail API error marking email as read: {e}")
            return False

    def mark_as_unread(self, message_id: str) -> bool:
        """
        Mark an email as unread (add UNREAD label).

        Args:
            message_id: Gmail message ID

        Returns:
            True if successful
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()

            logger.debug(f"Marked email {message_id} as unread")
            return True

        except HttpError as e:
            logger.error(f"Gmail API error marking email as unread: {e}")
            return False

    def add_label(self, message_id: str, label_id: str) -> bool:
        """
        Add a label to an email.

        Args:
            message_id: Gmail message ID
            label_id: Label ID to add

        Returns:
            True if successful
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()

            logger.debug(f"Added label {label_id} to email {message_id}")
            return True

        except HttpError as e:
            logger.error(f"Gmail API error adding label: {e}")
            return False

    def get_labels(self) -> List[Dict[str, Any]]:
        """
        Get all labels in the mailbox.

        Returns:
            List of label dicts with 'id', 'name', 'type'
        """
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            return labels

        except HttpError as e:
            logger.error(f"Gmail API error fetching labels: {e}")
            raise

    def create_label(self, name: str) -> Dict[str, Any]:
        """
        Create a new label.

        Args:
            name: Label name

        Returns:
            Created label data
        """
        try:
            label = self.service.users().labels().create(
                userId='me',
                body={
                    'name': name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
            ).execute()

            logger.info(f"Created label: {name} (id: {label['id']})")
            return label

        except HttpError as e:
            logger.error(f"Gmail API error creating label: {e}")
            raise

    def get_profile(self) -> Dict[str, Any]:
        """
        Get the authenticated user's Gmail profile.

        Returns:
            Profile data including email address
        """
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile

        except HttpError as e:
            logger.error(f"Gmail API error fetching profile: {e}")
            raise

    def fetch_emails_batch(
        self,
        message_ids: List[str],
        format: str = 'full'
    ) -> List[Dict[str, Any]]:
        """
        Fetch multiple emails by ID.

        Args:
            message_ids: List of Gmail message IDs
            format: Response format

        Returns:
            List of full email data
        """
        emails = []
        for msg_id in message_ids:
            try:
                email = self.get_email(msg_id, format=format)
                emails.append(email)
            except HttpError as e:
                logger.warning(f"Failed to fetch email {msg_id}: {e}")
                continue

        return emails

    # -------------------------------------------------------------------------
    # Email Sending Methods
    # -------------------------------------------------------------------------

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a new email.

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Plain text body content
            html_body: Optional HTML body content
            reply_to: Optional Reply-To address

        Returns:
            Dict with 'id' (Gmail message ID) and 'threadId'

        Raises:
            HttpError: If Gmail API call fails
        """
        message = self._create_message(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
            reply_to=reply_to
        )

        try:
            sent = self.service.users().messages().send(
                userId='me',
                body={'raw': message}
            ).execute()

            logger.info(
                f"Sent email to {to} | Subject: {subject[:50]}... | "
                f"ID: {sent['id']}"
            )
            return sent

        except HttpError as e:
            logger.error(f"Gmail API error sending email to {to}: {e}")
            raise

    def send_reply(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str,
        in_reply_to: str,
        references: Optional[str] = None,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a reply in an existing email thread.

        Args:
            to: Recipient email address
            subject: Email subject line (should include Re: prefix)
            body: Plain text body content
            thread_id: Gmail thread ID to reply in
            in_reply_to: Message-ID of the email being replied to
            references: Optional References header (for threading)
            html_body: Optional HTML body content
            reply_to: Optional Reply-To address

        Returns:
            Dict with 'id' (Gmail message ID) and 'threadId'

        Raises:
            HttpError: If Gmail API call fails
        """
        message = self._create_message(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
            reply_to=reply_to,
            in_reply_to=in_reply_to,
            references=references or in_reply_to
        )

        try:
            sent = self.service.users().messages().send(
                userId='me',
                body={
                    'raw': message,
                    'threadId': thread_id
                }
            ).execute()

            logger.info(
                f"Sent reply to {to} in thread {thread_id} | "
                f"Subject: {subject[:50]}... | ID: {sent['id']}"
            )
            return sent

        except HttpError as e:
            logger.error(
                f"Gmail API error sending reply to {to} "
                f"(thread={thread_id}): {e}"
            )
            raise

    def _create_message(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> str:
        """
        Create a base64url-encoded email message.

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Plain text body content
            html_body: Optional HTML body content
            reply_to: Optional Reply-To address
            in_reply_to: Optional In-Reply-To header for threading
            references: Optional References header for threading

        Returns:
            Base64url-encoded email string
        """
        if html_body:
            # Multipart message with both plain text and HTML
            message = MIMEMultipart('alternative')
            message.attach(MIMEText(body, 'plain'))
            message.attach(MIMEText(html_body, 'html'))
        else:
            # Plain text only
            message = MIMEText(body, 'plain')

        message['To'] = to
        message['Subject'] = subject

        if reply_to:
            message['Reply-To'] = reply_to

        if in_reply_to:
            message['In-Reply-To'] = in_reply_to

        if references:
            message['References'] = references

        # Encode message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return raw

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        """
        Get all messages in a thread.

        Args:
            thread_id: Gmail thread ID

        Returns:
            Thread data with all messages
        """
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()

            logger.debug(f"Fetched thread {thread_id}")
            return thread

        except HttpError as e:
            logger.error(f"Gmail API error fetching thread {thread_id}: {e}")
            raise
