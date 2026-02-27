"""
Unit tests for email send tasks.

Tests the send tasks from services/tasks/email_tasks.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from googleapiclient.errors import HttpError  # noqa: F401

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


@pytest.mark.skipif(not GOOGLE_API_AVAILABLE, reason="Google API client not installed")
class TestSendApprovedResponsesTask:
    """Tests for send_approved_responses_task."""

    @patch("services.tasks.email_tasks.get_repositories")
    def test_returns_success_when_no_approved_responses(self, mock_get_repos):
        """Test returns success with zero count when no approved responses."""
        from services.tasks.email_tasks import send_approved_responses_task

        mock_response_repo = Mock()
        mock_response_repo.get_approved_for_sending.return_value = []
        mock_get_repos.return_value = {
            "email": Mock(),
            "entity": Mock(),
            "response": mock_response_repo,
        }

        result = send_approved_responses_task(batch_size=10)

        assert result["status"] == "success"
        assert result["sent_count"] == 0
        assert result["failed_count"] == 0
        assert result["results"] == []

    @patch("services.email_sender.EmailSender")
    @patch("services.tasks.email_tasks.get_repositories")
    def test_sends_approved_responses(self, mock_get_repos, mock_sender_class):
        """Test sends approved responses and updates database."""
        from services.email_sender import SendResult
        from services.tasks.email_tasks import send_approved_responses_task

        approved_responses = [
            {
                "id": 1,
                "email_id": 10,
                "from_address": "customer1@example.com",
                "subject": "Quote Request 1",
                "draft_content": "Response 1",
                "send_attempts": 0,
                "raw_headers": {"thread_id": "t1", "Message-ID": "<m1@ex.com>"},
            },
            {
                "id": 2,
                "email_id": 20,
                "from_address": "customer2@example.com",
                "subject": "Quote Request 2",
                "draft_content": "Response 2",
                "send_attempts": 0,
                "raw_headers": {"thread_id": "t2", "Message-ID": "<m2@ex.com>"},
            },
        ]

        mock_response_repo = Mock()
        mock_response_repo.get_approved_for_sending.return_value = approved_responses
        mock_email_repo = Mock()
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": Mock(),
            "response": mock_response_repo,
        }

        # Mock sender - all sends succeed
        mock_sender = Mock()
        mock_sender.send_reply.return_value = SendResult(success=True, message_id="sent_123", thread_id="thread_456")
        mock_sender_class.return_value = mock_sender

        result = send_approved_responses_task(batch_size=10)

        assert result["status"] == "success"
        assert result["sent_count"] == 2
        assert result["failed_count"] == 0
        assert len(result["results"]) == 2

        # Verify database updates
        assert mock_response_repo.mark_sent_with_message_id.call_count == 2
        assert mock_email_repo.mark_responded.call_count == 2

    @patch("services.email_sender.EmailSender")
    @patch("services.tasks.email_tasks.get_repositories")
    def test_handles_send_failure_retryable(self, mock_get_repos, mock_sender_class):
        """Test handles retryable send failures correctly."""
        from services.email_sender import ErrorType, SendResult
        from services.tasks.email_tasks import send_approved_responses_task

        approved_responses = [
            {
                "id": 1,
                "email_id": 10,
                "from_address": "customer@example.com",
                "subject": "Quote Request",
                "draft_content": "Response",
                "send_attempts": 0,
                "raw_headers": {},
            },
        ]

        mock_response_repo = Mock()
        mock_response_repo.get_approved_for_sending.return_value = approved_responses
        mock_email_repo = Mock()
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": Mock(),
            "response": mock_response_repo,
        }

        # Mock sender - send fails with retryable error
        mock_sender = Mock()
        mock_sender.send_new_email.return_value = SendResult(
            success=False, error="Rate limit exceeded", error_type=ErrorType.RETRYABLE, http_status=429
        )
        mock_sender_class.return_value = mock_sender

        result = send_approved_responses_task(batch_size=10, max_attempts=3)

        assert result["status"] == "success"
        assert result["sent_count"] == 0
        # Retryable error should NOT be counted as failed (will retry)
        assert result["results"][0]["status"] == "retry"

        # Verify error was recorded but not marked as failed
        mock_response_repo.record_send_error.assert_called_once()
        mock_response_repo.mark_failed.assert_not_called()

    @patch("services.email_sender.EmailSender")
    @patch("services.tasks.email_tasks.get_repositories")
    def test_handles_send_failure_permanent(self, mock_get_repos, mock_sender_class):
        """Test handles permanent send failures correctly."""
        from services.email_sender import ErrorType, SendResult
        from services.tasks.email_tasks import send_approved_responses_task

        approved_responses = [
            {
                "id": 1,
                "email_id": 10,
                "from_address": "invalid@example.com",
                "subject": "Quote Request",
                "draft_content": "Response",
                "send_attempts": 0,
                "raw_headers": {},
            },
        ]

        mock_response_repo = Mock()
        mock_response_repo.get_approved_for_sending.return_value = approved_responses
        mock_email_repo = Mock()
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": Mock(),
            "response": mock_response_repo,
        }

        # Mock sender - send fails with permanent error
        mock_sender = Mock()
        mock_sender.send_new_email.return_value = SendResult(
            success=False, error="Invalid recipient", error_type=ErrorType.PERMANENT, http_status=400
        )
        mock_sender_class.return_value = mock_sender

        result = send_approved_responses_task(batch_size=10, max_attempts=3)

        assert result["status"] == "success"
        assert result["sent_count"] == 0
        assert result["failed_count"] == 1
        assert result["results"][0]["status"] == "failed"

        # Verify marked as failed
        mock_response_repo.mark_failed.assert_called_once()

    @patch("services.email_sender.EmailSender")
    @patch("services.tasks.email_tasks.get_repositories")
    def test_marks_failed_after_max_attempts(self, mock_get_repos, mock_sender_class):
        """Test marks as failed after reaching max attempts."""
        from services.email_sender import ErrorType, SendResult
        from services.tasks.email_tasks import send_approved_responses_task

        approved_responses = [
            {
                "id": 1,
                "email_id": 10,
                "from_address": "customer@example.com",
                "subject": "Quote Request",
                "draft_content": "Response",
                "send_attempts": 2,  # Already 2 attempts, max is 3
                "raw_headers": {},
            },
        ]

        mock_response_repo = Mock()
        mock_response_repo.get_approved_for_sending.return_value = approved_responses
        mock_email_repo = Mock()
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": Mock(),
            "response": mock_response_repo,
        }

        # Mock sender - send fails with retryable error
        mock_sender = Mock()
        mock_sender.send_new_email.return_value = SendResult(
            success=False, error="Rate limit exceeded", error_type=ErrorType.RETRYABLE, http_status=429
        )
        mock_sender_class.return_value = mock_sender

        result = send_approved_responses_task(batch_size=10, max_attempts=3)

        # Should be marked as failed because we've reached max attempts
        assert result["failed_count"] == 1
        assert result["results"][0]["status"] == "failed"
        mock_response_repo.mark_failed.assert_called_once()


@pytest.mark.skipif(not GOOGLE_API_AVAILABLE, reason="Google API client not installed")
class TestSendSingleResponseTask:
    """Tests for send_single_response_task."""

    @patch("services.tasks.email_tasks.get_repositories")
    def test_returns_error_when_response_not_found(self, mock_get_repos):
        """Test returns error when response not found in database."""
        from services.tasks.email_tasks import send_single_response_task

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = None
        mock_get_repos.return_value = {
            "email": Mock(),
            "entity": Mock(),
            "response": mock_response_repo,
        }

        result = send_single_response_task(response_id=999)

        assert result["status"] == "error"
        assert result["response_id"] == 999
        assert "not found" in result["error"].lower()

    @patch("services.tasks.email_tasks.get_repositories")
    def test_returns_error_when_not_approved(self, mock_get_repos):
        """Test returns error when response is not approved."""
        from services.tasks.email_tasks import send_single_response_task

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = {
            "id": 1,
            "status": "draft",  # Not approved
        }
        mock_get_repos.return_value = {
            "email": Mock(),
            "entity": Mock(),
            "response": mock_response_repo,
        }

        result = send_single_response_task(response_id=1)

        assert result["status"] == "error"
        assert "not approved" in result["error"].lower()

    @patch("services.email_sender.EmailSender")
    @patch("services.tasks.email_tasks.get_repositories")
    def test_sends_approved_response_successfully(self, mock_get_repos, mock_sender_class):
        """Test sends approved response and updates database."""
        from services.email_sender import SendResult
        from services.tasks.email_tasks import send_single_response_task

        response_data = {
            "id": 1,
            "email_id": 10,
            "status": "approved",
            "from_address": "customer@example.com",
            "subject": "Quote Request",
            "draft_content": "Thank you for your inquiry...",
            "send_attempts": 0,
            "raw_headers": {"thread_id": "t1", "Message-ID": "<m1@ex.com>"},
        }

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = response_data
        mock_email_repo = Mock()
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": Mock(),
            "response": mock_response_repo,
        }

        # Mock sender - send succeeds
        mock_sender = Mock()
        mock_sender.send_reply.return_value = SendResult(success=True, message_id="sent_123", thread_id="thread_456")
        mock_sender_class.return_value = mock_sender

        result = send_single_response_task(response_id=1)

        assert result["status"] == "sent"
        assert result["message_id"] == "sent_123"

        # Verify database updates
        mock_response_repo.mark_sent_with_message_id.assert_called_once_with(1, "sent_123")
        mock_email_repo.mark_responded.assert_called_once_with(10)


@pytest.mark.skipif(not GOOGLE_API_AVAILABLE, reason="Google API client not installed")
class TestSendSingleResponseHelper:
    """Tests for the _send_single_response helper function."""

    def test_uses_reply_when_thread_info_present(self):
        """Test uses send_reply when thread info is available."""
        from services.email_sender import SendResult
        from services.tasks.email_tasks import _send_single_response

        resp = {
            "id": 1,
            "email_id": 10,
            "from_address": "customer@example.com",
            "subject": "Quote Request",
            "draft_content": "Response body",
            "send_attempts": 0,
            "raw_headers": {"thread_id": "thread_123", "Message-ID": "<original@example.com>"},
        }

        mock_sender = Mock()
        mock_sender.send_reply.return_value = SendResult(success=True, message_id="msg123", thread_id="thread_123")

        mock_response_repo = Mock()
        mock_email_repo = Mock()

        result = _send_single_response(resp, mock_sender, mock_response_repo, mock_email_repo, max_attempts=3)

        mock_sender.send_reply.assert_called_once()
        mock_sender.send_new_email.assert_not_called()
        assert result["status"] == "sent"

    def test_uses_new_email_when_no_thread_info(self):
        """Test uses send_new_email when no thread info available."""
        from services.email_sender import SendResult
        from services.tasks.email_tasks import _send_single_response

        resp = {
            "id": 1,
            "email_id": 10,
            "from_address": "customer@example.com",
            "subject": "Quote Request",
            "draft_content": "Response body",
            "send_attempts": 0,
            "raw_headers": {},  # No thread info
        }

        mock_sender = Mock()
        mock_sender.send_new_email.return_value = SendResult(success=True, message_id="msg123", thread_id="new_thread")

        mock_response_repo = Mock()
        mock_email_repo = Mock()

        result = _send_single_response(resp, mock_sender, mock_response_repo, mock_email_repo, max_attempts=3)

        mock_sender.send_new_email.assert_called_once()
        mock_sender.send_reply.assert_not_called()
        assert result["status"] == "sent"
