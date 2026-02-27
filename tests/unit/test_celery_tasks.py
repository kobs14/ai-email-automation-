"""
Unit tests for Celery email tasks.

Tests the email tasks from services/tasks/email_tasks.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Check if google libraries are available
try:
    import google.auth  # noqa: F401

    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False


@pytest.mark.skipif(not GOOGLE_AUTH_AVAILABLE, reason="Google auth libraries not installed")
class TestFetchEmailsTask:
    """Test fetch_emails_task - requires google-auth libraries."""

    @patch("services.tasks.email_tasks.get_email_repository")
    @patch("services.gmail.parser.EmailParser")
    @patch("services.gmail.client.GmailClient")
    @patch("services.gmail.auth.GmailAuth")
    def test_returns_success_when_no_unread_emails(self, mock_auth, mock_client_class, mock_parser, mock_get_repo):
        """Test returns success with zero count when no unread emails."""
        from services.tasks.email_tasks import fetch_emails_task

        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.fetch_unread_emails.return_value = []
        mock_client_class.return_value = mock_client_instance

        # Run task synchronously (without .delay())
        result = fetch_emails_task(max_results=10)

        assert result["status"] == "success"
        assert result["fetched_count"] == 0
        assert result["new_count"] == 0
        assert result["message_ids"] == []

    @patch("services.tasks.email_tasks.get_email_repository")
    @patch("services.gmail.parser.EmailParser")
    @patch("services.gmail.client.GmailClient")
    @patch("services.gmail.auth.GmailAuth")
    def test_skips_existing_emails(self, mock_auth, mock_client_class, mock_parser, mock_get_repo):
        """Test skips emails that already exist in database."""
        from services.tasks.email_tasks import fetch_emails_task

        # Setup mock Gmail client
        mock_client_instance = Mock()
        mock_client_instance.fetch_unread_emails.return_value = [
            {"id": "existing_gmail_id"},
        ]
        mock_client_class.return_value = mock_client_instance

        # Setup mock repository - email already exists
        mock_repo_instance = Mock()
        mock_repo_instance.gmail_id_exists.return_value = True
        mock_get_repo.return_value = mock_repo_instance

        # Run task
        result = fetch_emails_task(max_results=10)

        assert result["status"] == "success"
        assert result["fetched_count"] == 0
        assert result["new_count"] == 0
        # Should not have called create_if_not_exists
        mock_repo_instance.create_if_not_exists.assert_not_called()


class TestProcessPendingEmailsTask:
    """Test process_pending_emails_task."""

    @patch("services.tasks.email_tasks.get_repositories")
    def test_returns_success_when_no_pending_emails(self, mock_get_repos):
        """Test returns success when no pending emails."""
        from services.tasks.email_tasks import process_pending_emails_task

        mock_email_repo = Mock()
        mock_email_repo.get_pending_emails.return_value = []
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": Mock(),
            "response": Mock(),
        }

        result = process_pending_emails_task(batch_size=10)

        assert result["status"] == "success"
        assert result["processed_count"] == 0
        assert result["results"] == []

    @patch("services.tasks.email_tasks._process_email_with_claude")
    @patch("services.tasks.email_tasks.get_repositories")
    def test_processes_and_classifies_pending_emails(self, mock_get_repos, mock_process):
        """Test processes pending emails and updates their intent."""
        from services.tasks.email_tasks import process_pending_emails_task

        pending_emails = [
            {"id": 1, "subject": "Quote request", "body": "I need a quote"},
            {"id": 2, "subject": "Book cleaning", "body": "Want to book"},
        ]

        mock_email_repo = Mock()
        mock_entity_repo = Mock()
        mock_response_repo = Mock()
        mock_email_repo.get_pending_emails.return_value = pending_emails
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": mock_entity_repo,
            "response": mock_response_repo,
        }

        # Mock the Claude processing function
        mock_process.return_value = {
            "classification": {"intent": "quote_request", "confidence": 0.9, "reasoning": "test"},
            "entities_count": 0,
            "entity_ids": [],
            "quote": None,
            "response_id": 1,
            "has_response": True,
        }

        result = process_pending_emails_task(batch_size=10)

        assert result["status"] == "success"
        assert result["processed_count"] == 2
        assert len(result["results"]) == 2

        # Verify _process_email_with_claude was called for each email
        assert mock_process.call_count == 2

    @patch("services.tasks.email_tasks._process_email_with_claude")
    @patch("services.tasks.email_tasks.get_repositories")
    def test_marks_failed_on_processing_error(self, mock_get_repos, mock_process):
        """Test marks email as failed when processing error occurs."""
        from services.tasks.email_tasks import process_pending_emails_task

        pending_emails = [
            {"id": 1, "subject": "Test", "body": "Test body"},
        ]

        mock_email_repo = Mock()
        mock_entity_repo = Mock()
        mock_response_repo = Mock()
        mock_email_repo.get_pending_emails.return_value = pending_emails
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": mock_entity_repo,
            "response": mock_response_repo,
        }

        # Make Claude processing raise an error
        mock_process.side_effect = Exception("Claude API Error")

        result = process_pending_emails_task(batch_size=10)

        assert result["status"] == "success"
        assert result["failed_count"] == 1
        # Verify mark_failed was called
        mock_email_repo.mark_failed.assert_called_once_with(1)


class TestProcessSingleEmailTask:
    """Test process_single_email_task."""

    @patch("services.tasks.email_tasks._process_email_with_claude")
    @patch("services.tasks.email_tasks.get_repositories")
    def test_processes_single_email_successfully(self, mock_get_repos, mock_process):
        """Test processes single email and returns classification."""
        from services.tasks.email_tasks import process_single_email_task

        email_record = {
            "id": 1,
            "message_id": "msg1",
            "from_address": "sender@example.com",
            "subject": "Quote request",
            "body": "I need a quote for cleaning",
        }

        mock_email_repo = Mock()
        mock_email_repo.get_email_by_id.return_value = email_record
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": Mock(),
            "response": Mock(),
        }

        # Mock the Claude processing function
        mock_process.return_value = {
            "classification": {"intent": "quote_request", "confidence": 0.9, "reasoning": "test"},
            "entities_count": 0,
            "entity_ids": [],
            "quote": None,
            "response_id": 1,
            "has_response": True,
        }

        result = process_single_email_task(email_id=1)

        assert result["status"] == "success"
        assert result["email_id"] == 1
        assert result["classification"]["intent"] == "quote_request"

    @patch("services.tasks.email_tasks.get_repositories")
    def test_returns_error_when_email_not_found(self, mock_get_repos):
        """Test returns error when email not found in database."""
        from services.tasks.email_tasks import process_single_email_task

        mock_email_repo = Mock()
        mock_email_repo.get_email_by_id.return_value = None
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": Mock(),
            "response": Mock(),
        }

        result = process_single_email_task(email_id=999)

        assert result["status"] == "error"
        assert result["email_id"] == 999
        assert "not found" in result["error"].lower()

    @patch("services.tasks.email_tasks._process_email_with_claude")
    @patch("services.tasks.email_tasks.get_repositories")
    def test_updates_intent_in_database(self, mock_get_repos, mock_process):
        """Test updates intent in database after classification."""
        from services.tasks.email_tasks import process_single_email_task

        email_record = {
            "id": 1,
            "message_id": "msg1",
            "from_address": "sender@example.com",
            "subject": "Booking request",
            "body": "I want to book a cleaning",
        }

        mock_email_repo = Mock()
        mock_entity_repo = Mock()
        mock_response_repo = Mock()
        mock_email_repo.get_email_by_id.return_value = email_record
        mock_get_repos.return_value = {
            "email": mock_email_repo,
            "entity": mock_entity_repo,
            "response": mock_response_repo,
        }

        # Mock the Claude processing function
        mock_process.return_value = {
            "classification": {"intent": "booking_request", "confidence": 0.9, "reasoning": "test"},
            "entities_count": 0,
            "entity_ids": [],
            "quote": None,
            "response_id": 1,
            "has_response": True,
        }

        process_single_email_task(email_id=1)

        # Verify _process_email_with_claude was called with all repos
        mock_process.assert_called_once()
        call_args = mock_process.call_args
        assert call_args[0][0] == email_record
        assert call_args[0][1] == mock_email_repo


class TestGetEmailRepository:
    """Test get_email_repository helper function."""

    @patch("database.connection.get_database")
    @patch("database.schema.EmailRepository")
    def test_returns_email_repository_instance(self, mock_repo_class, mock_get_db):
        """Test returns EmailRepository with database connection."""
        from services.tasks.email_tasks import get_email_repository

        mock_db = Mock()
        mock_get_db.return_value = mock_db

        get_email_repository()

        mock_get_db.assert_called_once()
        mock_repo_class.assert_called_once_with(mock_db)
