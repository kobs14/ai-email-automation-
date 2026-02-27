"""
Unit tests for the email sender service.

Tests the EmailSender class from services/email_sender.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.email_sender import EmailSender, ErrorType, SendResult


class TestSendResult:
    """Tests for the SendResult dataclass."""

    def test_success_result_is_not_retryable(self):
        """Test successful result is not retryable."""
        result = SendResult(success=True, message_id="msg123", thread_id="thread456")
        assert result.success is True
        assert result.is_retryable is False

    def test_retryable_error_is_retryable(self):
        """Test retryable error type is marked as retryable."""
        result = SendResult(success=False, error="Rate limit exceeded", error_type=ErrorType.RETRYABLE, http_status=429)
        assert result.success is False
        assert result.is_retryable is True

    def test_permanent_error_is_not_retryable(self):
        """Test permanent error type is not retryable."""
        result = SendResult(success=False, error="Invalid recipient", error_type=ErrorType.PERMANENT, http_status=400)
        assert result.success is False
        assert result.is_retryable is False

    def test_network_error_is_retryable(self):
        """Test network error type is retryable."""
        result = SendResult(success=False, error="Connection timeout", error_type=ErrorType.NETWORK)
        assert result.success is False
        assert result.is_retryable is True


class TestEmailSender:
    """Tests for the EmailSender class."""

    @patch("services.email_sender.GmailClient")
    @patch("services.email_sender.GmailAuth")
    def test_send_new_email_success(self, mock_auth_class, mock_client_class):
        """Test sending a new email successfully."""
        # Setup mock
        mock_client = Mock()
        mock_client.send_email.return_value = {"id": "sent_msg_123", "threadId": "thread_456"}
        mock_client_class.return_value = mock_client

        sender = EmailSender()
        result = sender.send_new_email(
            to="customer@example.com", subject="Quote for Cleaning", body="Thank you for your inquiry..."
        )

        assert result.success is True
        assert result.message_id == "sent_msg_123"
        assert result.thread_id == "thread_456"
        mock_client.send_email.assert_called_once()

    @patch("services.email_sender.GmailClient")
    @patch("services.email_sender.GmailAuth")
    def test_send_reply_success(self, mock_auth_class, mock_client_class):
        """Test sending a reply in an existing thread."""
        # Setup mock
        mock_client = Mock()
        mock_client.send_reply.return_value = {"id": "reply_msg_123", "threadId": "existing_thread"}
        mock_client_class.return_value = mock_client

        sender = EmailSender()
        result = sender.send_reply(
            to="customer@example.com",
            subject="Cleaning Quote Request",
            body="Thank you for your inquiry...",
            thread_id="existing_thread",
            in_reply_to="<original@example.com>",
        )

        assert result.success is True
        assert result.message_id == "reply_msg_123"
        assert result.thread_id == "existing_thread"
        mock_client.send_reply.assert_called_once()

    @patch("services.email_sender.GmailClient")
    @patch("services.email_sender.GmailAuth")
    def test_send_reply_adds_re_prefix(self, mock_auth_class, mock_client_class):
        """Test that replies get Re: prefix added to subject."""
        mock_client = Mock()
        mock_client.send_reply.return_value = {"id": "msg", "threadId": "thread"}
        mock_client_class.return_value = mock_client

        sender = EmailSender()
        sender.send_reply(
            to="customer@example.com",
            subject="Cleaning Quote",  # No Re: prefix
            body="Response...",
            thread_id="thread_123",
            in_reply_to="<original@example.com>",
        )

        # Verify the subject was modified to include Re:
        call_args = mock_client.send_reply.call_args
        assert call_args.kwargs["subject"] == "Re: Cleaning Quote"

    @patch("services.email_sender.GmailClient")
    @patch("services.email_sender.GmailAuth")
    def test_send_reply_keeps_existing_re_prefix(self, mock_auth_class, mock_client_class):
        """Test that existing Re: prefix is not duplicated."""
        mock_client = Mock()
        mock_client.send_reply.return_value = {"id": "msg", "threadId": "thread"}
        mock_client_class.return_value = mock_client

        sender = EmailSender()
        sender.send_reply(
            to="customer@example.com",
            subject="Re: Cleaning Quote",  # Already has Re:
            body="Response...",
            thread_id="thread_123",
            in_reply_to="<original@example.com>",
        )

        call_args = mock_client.send_reply.call_args
        assert call_args.kwargs["subject"] == "Re: Cleaning Quote"

    @patch("services.email_sender.GmailClient")
    @patch("services.email_sender.GmailAuth")
    def test_rate_limit_error_is_retryable(self, mock_auth_class, mock_client_class):
        """Test that 429 rate limit errors are marked as retryable."""
        from googleapiclient.errors import HttpError

        mock_response = Mock()
        mock_response.status = 429
        error = HttpError(resp=mock_response, content=b"Rate limit exceeded")

        mock_client = Mock()
        mock_client.send_email.side_effect = error
        mock_client_class.return_value = mock_client

        sender = EmailSender()
        result = sender.send_new_email(to="customer@example.com", subject="Test", body="Test body")

        assert result.success is False
        assert result.is_retryable is True
        assert result.error_type == ErrorType.RETRYABLE
        assert result.http_status == 429

    @patch("services.email_sender.GmailClient")
    @patch("services.email_sender.GmailAuth")
    def test_server_error_is_retryable(self, mock_auth_class, mock_client_class):
        """Test that 5xx server errors are marked as retryable."""
        from googleapiclient.errors import HttpError

        mock_response = Mock()
        mock_response.status = 503
        error = HttpError(resp=mock_response, content=b"Service unavailable")

        mock_client = Mock()
        mock_client.send_email.side_effect = error
        mock_client_class.return_value = mock_client

        sender = EmailSender()
        result = sender.send_new_email(to="customer@example.com", subject="Test", body="Test body")

        assert result.success is False
        assert result.is_retryable is True
        assert result.error_type == ErrorType.RETRYABLE
        assert result.http_status == 503

    @patch("services.email_sender.GmailClient")
    @patch("services.email_sender.GmailAuth")
    def test_auth_error_is_permanent(self, mock_auth_class, mock_client_class):
        """Test that 401 auth errors are marked as permanent."""
        from googleapiclient.errors import HttpError

        mock_response = Mock()
        mock_response.status = 401
        error = HttpError(resp=mock_response, content=b"Unauthorized")

        mock_client = Mock()
        mock_client.send_email.side_effect = error
        mock_client_class.return_value = mock_client

        sender = EmailSender()
        result = sender.send_new_email(to="customer@example.com", subject="Test", body="Test body")

        assert result.success is False
        assert result.is_retryable is False
        assert result.error_type == ErrorType.PERMANENT
        assert result.http_status == 401

    @patch("services.email_sender.GmailClient")
    @patch("services.email_sender.GmailAuth")
    def test_bad_request_is_permanent(self, mock_auth_class, mock_client_class):
        """Test that 400 bad request errors are marked as permanent."""
        from googleapiclient.errors import HttpError

        mock_response = Mock()
        mock_response.status = 400
        error = HttpError(resp=mock_response, content=b"Invalid recipient")

        mock_client = Mock()
        mock_client.send_email.side_effect = error
        mock_client_class.return_value = mock_client

        sender = EmailSender()
        result = sender.send_new_email(to="invalid-email", subject="Test", body="Test body")

        assert result.success is False
        assert result.is_retryable is False
        assert result.error_type == ErrorType.PERMANENT
        assert result.http_status == 400

    @patch("services.email_sender.GmailClient")
    @patch("services.email_sender.GmailAuth")
    def test_generic_exception_is_network_error(self, mock_auth_class, mock_client_class):
        """Test that generic exceptions are treated as network errors."""
        mock_client = Mock()
        mock_client.send_email.side_effect = ConnectionError("Network unreachable")
        mock_client_class.return_value = mock_client

        sender = EmailSender()
        result = sender.send_new_email(to="customer@example.com", subject="Test", body="Test body")

        assert result.success is False
        assert result.is_retryable is True
        assert result.error_type == ErrorType.NETWORK

    def test_uses_provided_gmail_client(self):
        """Test that provided GmailClient is used instead of creating new one."""
        mock_client = Mock()

        sender = EmailSender(gmail_client=mock_client)

        assert sender.client is mock_client


class TestSendResponseEmail:
    """Tests for the send_response_email convenience function."""

    @patch("services.email_sender.EmailSender")
    def test_sends_reply_when_thread_info_available(self, mock_sender_class):
        """Test sends as reply when thread_id and message_id are provided."""
        from services.email_sender import send_response_email

        mock_sender = Mock()
        mock_sender.send_reply.return_value = SendResult(success=True, message_id="msg123", thread_id="thread456")
        mock_sender_class.return_value = mock_sender

        response_data = {
            "from_address": "customer@example.com",
            "subject": "Quote Request",
            "draft_content": "Thank you for your inquiry...",
            "raw_headers": {"thread_id": "thread_456", "Message-ID": "<original@example.com>"},
        }

        result = send_response_email(response_data)

        assert result.success is True
        mock_sender.send_reply.assert_called_once()

    @patch("services.email_sender.EmailSender")
    def test_sends_new_email_when_no_thread_info(self, mock_sender_class):
        """Test sends as new email when no threading info available."""
        from services.email_sender import send_response_email

        mock_sender = Mock()
        mock_sender.send_new_email.return_value = SendResult(success=True, message_id="msg123", thread_id="thread456")
        mock_sender_class.return_value = mock_sender

        response_data = {
            "from_address": "customer@example.com",
            "subject": "Quote Request",
            "draft_content": "Thank you for your inquiry...",
            "raw_headers": {},
        }

        result = send_response_email(response_data)

        assert result.success is True
        mock_sender.send_new_email.assert_called_once()
