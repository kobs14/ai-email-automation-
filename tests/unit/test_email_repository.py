"""
Unit tests for EmailRepository.

Tests the EmailRepository class from database/schema.py,
focusing on the create_if_not_exists method.
"""

import pytest
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.schema import EmailRepository


class TestEmailRepositoryCreateIfNotExists:
    """Test EmailRepository.create_if_not_exists method."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance."""
        return Mock()

    @pytest.fixture
    def email_repo(self, mock_db):
        """Create EmailRepository with mock database."""
        return EmailRepository(mock_db)

    @pytest.fixture
    def sample_email_data(self):
        """Sample email data for testing."""
        return {
            'gmail_id': 'gmail123',
            'message_id': '<msg123@example.com>',
            'from_address': 'sender@example.com',
            'subject': 'Test email',
            'body': 'This is a test email body.',
            'received_at': datetime(2025, 1, 20, 10, 30, 0),
            'raw_headers': {'gmail_id': 'gmail123', 'thread_id': 'thread456'},
        }

    def test_creates_new_email_when_not_exists(self, email_repo, mock_db, sample_email_data):
        """Test that a new email is created when it doesn't exist."""
        # Mock gmail_id_exists to return False
        mock_db.execute_query.side_effect = [
            {'exists': False},  # gmail_id_exists check
            {'id': 42, 'message_id': sample_email_data['message_id'], 'created_at': datetime.now()},  # INSERT
        ]

        email_id, created = email_repo.create_if_not_exists(**sample_email_data)

        assert email_id == 42
        assert created is True
        assert mock_db.execute_query.call_count == 2

    def test_returns_existing_email_when_exists(self, email_repo, mock_db, sample_email_data):
        """Test that existing email is returned when gmail_id exists."""
        existing_email = {
            'id': 99,
            'message_id': sample_email_data['message_id'],
            'from_address': sample_email_data['from_address'],
            'subject': sample_email_data['subject'],
            'status': 'pending',
            'intent': None,
            'raw_headers': sample_email_data['raw_headers'],
        }

        # Mock gmail_id_exists to return True, then get_email_by_gmail_id
        mock_db.execute_query.side_effect = [
            {'exists': True},  # gmail_id_exists check
            existing_email,  # get_email_by_gmail_id
        ]

        email_id, created = email_repo.create_if_not_exists(**sample_email_data)

        assert email_id == 99
        assert created is False
        # Should not have called INSERT
        assert mock_db.execute_query.call_count == 2

    def test_handles_none_raw_headers(self, email_repo, mock_db):
        """Test creating email with None raw_headers."""
        mock_db.execute_query.side_effect = [
            {'exists': False},  # gmail_id_exists check
            {'id': 1, 'message_id': 'msg1', 'created_at': datetime.now()},  # INSERT
        ]

        email_id, created = email_repo.create_if_not_exists(
            gmail_id='gmail1',
            message_id='msg1',
            from_address='test@example.com',
            subject='Test',
            body='Body',
            received_at=datetime.now(),
            raw_headers=None
        )

        assert email_id == 1
        assert created is True


class TestEmailRepositoryGmailIdExists:
    """Test EmailRepository.gmail_id_exists method."""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def email_repo(self, mock_db):
        return EmailRepository(mock_db)

    def test_returns_true_when_exists(self, email_repo, mock_db):
        """Test returns True when gmail_id exists."""
        mock_db.execute_query.return_value = {'exists': True}

        result = email_repo.gmail_id_exists('gmail123')

        assert result is True

    def test_returns_false_when_not_exists(self, email_repo, mock_db):
        """Test returns False when gmail_id doesn't exist."""
        mock_db.execute_query.return_value = {'exists': False}

        result = email_repo.gmail_id_exists('nonexistent')

        assert result is False

    def test_returns_false_when_query_returns_none(self, email_repo, mock_db):
        """Test returns False when query returns None."""
        mock_db.execute_query.return_value = None

        result = email_repo.gmail_id_exists('gmail123')

        assert result is False


class TestEmailRepositoryGetPendingEmails:
    """Test EmailRepository.get_pending_emails method."""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def email_repo(self, mock_db):
        return EmailRepository(mock_db)

    def test_returns_list_of_pending_emails(self, email_repo, mock_db):
        """Test returns list of pending email dicts."""
        mock_emails = [
            {'id': 1, 'subject': 'Email 1', 'status': 'pending'},
            {'id': 2, 'subject': 'Email 2', 'status': 'pending'},
        ]
        mock_db.execute_query.return_value = mock_emails

        result = email_repo.get_pending_emails(limit=10)

        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[1]['id'] == 2

    def test_returns_empty_list_when_no_pending(self, email_repo, mock_db):
        """Test returns empty list when no pending emails."""
        mock_db.execute_query.return_value = []

        result = email_repo.get_pending_emails(limit=10)

        assert result == []

    def test_returns_empty_list_when_query_returns_none(self, email_repo, mock_db):
        """Test returns empty list when query returns None."""
        mock_db.execute_query.return_value = None

        result = email_repo.get_pending_emails(limit=10)

        assert result == []

    def test_respects_limit_parameter(self, email_repo, mock_db):
        """Test that limit parameter is passed to query."""
        mock_db.execute_query.return_value = []

        email_repo.get_pending_emails(limit=5)

        # Check that the limit was passed in the params
        call_args = mock_db.execute_query.call_args
        assert call_args[1]['params'] == (5,)


class TestEmailRepositoryUpdateIntent:
    """Test EmailRepository.update_intent method."""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def email_repo(self, mock_db):
        return EmailRepository(mock_db)

    def test_updates_intent_successfully(self, email_repo, mock_db):
        """Test successful intent update."""
        mock_db.execute_query.return_value = {
            'id': 1,
            'intent': 'quote_request',
            'status': 'classified'
        }

        result = email_repo.update_intent(1, 'quote_request')

        assert result is True

    def test_returns_false_when_email_not_found(self, email_repo, mock_db):
        """Test returns False when email not found."""
        mock_db.execute_query.return_value = None

        result = email_repo.update_intent(999, 'quote_request')

        assert result is False


class TestEmailRepositoryMarkFailed:
    """Test EmailRepository.mark_failed method."""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def email_repo(self, mock_db):
        return EmailRepository(mock_db)

    def test_marks_email_as_failed(self, email_repo, mock_db):
        """Test marking email as failed."""
        mock_db.execute_query.return_value = {'id': 1, 'status': 'failed'}

        result = email_repo.mark_failed(1)

        assert result is True

    def test_returns_false_when_email_not_found(self, email_repo, mock_db):
        """Test returns False when email not found."""
        mock_db.execute_query.return_value = None

        result = email_repo.mark_failed(999)

        assert result is False
