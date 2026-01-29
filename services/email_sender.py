"""
Email sender service for sending response emails.

Wraps the Gmail client with:
- Error classification (retryable vs permanent)
- Logging of all send attempts
- Clean result object (SendResult)
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from googleapiclient.errors import HttpError

from services.gmail.auth import GmailAuth
from services.gmail.client import GmailClient

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of send errors."""
    RETRYABLE = "retryable"      # Can retry later (rate limit, server error)
    PERMANENT = "permanent"       # Cannot retry (bad request, auth error)
    NETWORK = "network"           # Network issues (may retry)


@dataclass
class SendResult:
    """Result of an email send attempt."""
    success: bool
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    http_status: Optional[int] = None

    @property
    def is_retryable(self) -> bool:
        """Check if the error is retryable."""
        if self.success:
            return False
        return self.error_type in (ErrorType.RETRYABLE, ErrorType.NETWORK)


class EmailSender:
    """
    Service for sending response emails via Gmail.

    Handles error classification and logging for all send operations.

    Usage:
        sender = EmailSender()
        result = sender.send_response(
            to="customer@example.com",
            subject="Re: Cleaning Quote Request",
            body="Thank you for your inquiry...",
            thread_id="abc123",
            in_reply_to="<original-message-id@example.com>"
        )

        if result.success:
            print(f"Sent! Message ID: {result.message_id}")
        elif result.is_retryable:
            print(f"Temporary error, can retry: {result.error}")
        else:
            print(f"Permanent error: {result.error}")
    """

    # HTTP status codes that indicate retryable errors
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    # HTTP status codes that indicate permanent errors
    PERMANENT_STATUS_CODES = {400, 401, 403, 404}

    def __init__(self, gmail_client: Optional[GmailClient] = None):
        """
        Initialize the email sender.

        Args:
            gmail_client: Optional pre-configured GmailClient.
                         If not provided, one will be created.
        """
        self._client = gmail_client

    @property
    def client(self) -> GmailClient:
        """Get or create the Gmail client."""
        if self._client is None:
            auth = GmailAuth()
            self._client = GmailClient(auth)
        return self._client

    def send_response(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> SendResult:
        """
        Send a response email, optionally as a reply in a thread.

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Plain text body content
            thread_id: Optional Gmail thread ID for replies
            in_reply_to: Optional Message-ID for threading
            references: Optional References header
            html_body: Optional HTML body content
            reply_to: Optional Reply-To address

        Returns:
            SendResult with success status and details
        """
        logger.info(f"Attempting to send email to {to} | Subject: {subject[:50]}...")

        try:
            if thread_id and in_reply_to:
                # Send as reply in existing thread
                result = self.client.send_reply(
                    to=to,
                    subject=self._ensure_reply_prefix(subject),
                    body=body,
                    thread_id=thread_id,
                    in_reply_to=in_reply_to,
                    references=references,
                    html_body=html_body,
                    reply_to=reply_to
                )
            else:
                # Send as new email
                result = self.client.send_email(
                    to=to,
                    subject=subject,
                    body=body,
                    html_body=html_body,
                    reply_to=reply_to
                )

            logger.info(
                f"Successfully sent email to {to} | "
                f"Message ID: {result.get('id')} | "
                f"Thread ID: {result.get('threadId')}"
            )

            return SendResult(
                success=True,
                message_id=result.get('id'),
                thread_id=result.get('threadId')
            )

        except HttpError as e:
            return self._handle_http_error(e, to)

        except Exception as e:
            logger.error(f"Unexpected error sending email to {to}: {e}")
            return SendResult(
                success=False,
                error=str(e),
                error_type=ErrorType.NETWORK
            )

    def send_new_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> SendResult:
        """
        Send a new email (not a reply).

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Plain text body content
            html_body: Optional HTML body content
            reply_to: Optional Reply-To address

        Returns:
            SendResult with success status and details
        """
        return self.send_response(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
            reply_to=reply_to
        )

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
    ) -> SendResult:
        """
        Send a reply in an existing thread.

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Plain text body content
            thread_id: Gmail thread ID
            in_reply_to: Message-ID of original email
            references: Optional References header
            html_body: Optional HTML body content
            reply_to: Optional Reply-To address

        Returns:
            SendResult with success status and details
        """
        return self.send_response(
            to=to,
            subject=subject,
            body=body,
            thread_id=thread_id,
            in_reply_to=in_reply_to,
            references=references,
            html_body=html_body,
            reply_to=reply_to
        )

    def _handle_http_error(self, error: HttpError, recipient: str) -> SendResult:
        """
        Handle and classify HTTP errors from Gmail API.

        Args:
            error: The HttpError from Gmail API
            recipient: Email recipient (for logging)

        Returns:
            SendResult with error details
        """
        status_code = error.resp.status if error.resp else None
        error_message = str(error)

        # Classify the error
        if status_code in self.RETRYABLE_STATUS_CODES:
            error_type = ErrorType.RETRYABLE
            log_level = logging.WARNING
        elif status_code in self.PERMANENT_STATUS_CODES:
            error_type = ErrorType.PERMANENT
            log_level = logging.ERROR
        else:
            # Unknown status - treat as potentially retryable
            error_type = ErrorType.NETWORK
            log_level = logging.WARNING

        logger.log(
            log_level,
            f"Gmail API error sending to {recipient} | "
            f"Status: {status_code} | Type: {error_type.value} | "
            f"Error: {error_message}"
        )

        return SendResult(
            success=False,
            error=error_message,
            error_type=error_type,
            http_status=status_code
        )

    def _ensure_reply_prefix(self, subject: str) -> str:
        """
        Ensure subject has 'Re:' prefix for replies.

        Args:
            subject: Original subject line

        Returns:
            Subject with 'Re:' prefix if not already present
        """
        if subject.lower().startswith('re:'):
            return subject
        return f"Re: {subject}"


def send_response_email(response_data: Dict[str, Any]) -> SendResult:
    """
    Convenience function to send a response email from response data.

    Args:
        response_data: Dict containing response and email information
            Required keys: from_address, subject, draft_content
            Optional keys: raw_headers (with thread_id, Message-ID)

    Returns:
        SendResult with success status and details
    """
    sender = EmailSender()

    to = response_data.get('from_address')
    subject = response_data.get('subject', 'Response from EcoClean')
    body = response_data.get('draft_content', '')

    # Extract threading information from raw_headers if available
    raw_headers = response_data.get('raw_headers') or {}
    thread_id = raw_headers.get('thread_id')
    message_id = raw_headers.get('Message-ID') or response_data.get('message_id')

    if thread_id and message_id:
        return sender.send_reply(
            to=to,
            subject=subject,
            body=body,
            thread_id=thread_id,
            in_reply_to=message_id
        )
    else:
        return sender.send_new_email(
            to=to,
            subject=subject,
            body=body
        )
