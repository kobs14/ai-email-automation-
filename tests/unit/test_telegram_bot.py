"""
Unit tests for the Telegram bot service.

Tests cover:
- Bot creation and configuration
- Command handlers
- Notification functions
- Callback handlers
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime


class TestTelegramSettings:
    """Tests for TelegramSettings configuration."""

    def test_telegram_settings_not_configured(self):
        """Test that is_configured returns False when token is missing."""
        from config.settings import TelegramSettings

        settings = TelegramSettings()
        settings.bot_token = ''
        settings.admin_chat_id = '12345'

        assert settings.is_configured() is False

    def test_telegram_settings_not_configured_default_token(self):
        """Test that is_configured returns False with placeholder token."""
        from config.settings import TelegramSettings

        settings = TelegramSettings()
        settings.bot_token = 'your_bot_token_from_botfather'
        settings.admin_chat_id = '12345'

        assert settings.is_configured() is False

    def test_telegram_settings_not_configured_missing_chat_id(self):
        """Test that is_configured returns False without chat_id."""
        from config.settings import TelegramSettings

        settings = TelegramSettings()
        settings.bot_token = 'valid_token_123'
        settings.admin_chat_id = ''

        assert settings.is_configured() is False

    def test_telegram_settings_configured(self):
        """Test that is_configured returns True with valid settings."""
        from config.settings import TelegramSettings

        settings = TelegramSettings()
        settings.bot_token = 'valid_token_123'
        settings.admin_chat_id = '12345'

        assert settings.is_configured() is True


class TestBotCreation:
    """Tests for bot application creation."""

    @patch('services.telegram.bot.settings')
    def test_create_application_no_token(self, mock_settings):
        """Test that create_application returns None when token not set."""
        from services.telegram.bot import create_application

        mock_telegram_settings = Mock()
        mock_telegram_settings.bot_token = ''
        mock_settings.telegram = mock_telegram_settings

        result = create_application()

        assert result is None

    @patch('services.telegram.bot.settings')
    def test_create_application_placeholder_token(self, mock_settings):
        """Test that create_application returns None with placeholder token."""
        from services.telegram.bot import create_application

        mock_telegram_settings = Mock()
        mock_telegram_settings.bot_token = 'your_bot_token_from_botfather'
        mock_settings.telegram = mock_telegram_settings

        result = create_application()

        assert result is None

    @patch('services.telegram.bot.Application')
    @patch('services.telegram.bot.settings')
    def test_create_application_with_valid_token(
        self, mock_settings, mock_application
    ):
        """Test that create_application creates app with valid token."""
        from services.telegram.bot import create_application

        mock_telegram_settings = Mock()
        mock_telegram_settings.bot_token = 'valid_token_123'
        mock_settings.telegram = mock_telegram_settings

        mock_builder = Mock()
        mock_app = Mock()
        mock_application.builder.return_value = mock_builder
        mock_builder.token.return_value = mock_builder
        mock_builder.post_init.return_value = mock_builder
        mock_builder.build.return_value = mock_app

        result = create_application()

        mock_application.builder.assert_called_once()
        mock_builder.token.assert_called_once_with('valid_token_123')
        mock_builder.build.assert_called_once()
        assert result == mock_app


class TestNotifications:
    """Tests for notification functions."""

    @patch('services.telegram.notifications.settings')
    def test_get_bot_no_token(self, mock_settings):
        """Test get_bot returns None when token not configured."""
        from services.telegram.notifications import get_bot

        mock_telegram_settings = Mock()
        mock_telegram_settings.bot_token = ''
        mock_settings.telegram = mock_telegram_settings

        result = get_bot()

        assert result is None

    @patch('services.telegram.notifications.settings')
    def test_get_chat_id_no_id(self, mock_settings):
        """Test get_chat_id returns None when not configured."""
        from services.telegram.notifications import get_chat_id

        mock_telegram_settings = Mock()
        mock_telegram_settings.admin_chat_id = ''
        mock_settings.telegram = mock_telegram_settings

        result = get_chat_id()

        assert result is None

    @patch('services.telegram.notifications.settings')
    def test_get_chat_id_configured(self, mock_settings):
        """Test get_chat_id returns ID when configured."""
        from services.telegram.notifications import get_chat_id

        mock_telegram_settings = Mock()
        mock_telegram_settings.admin_chat_id = '12345'
        mock_settings.telegram = mock_telegram_settings

        result = get_chat_id()

        assert result == '12345'

    @patch('database.connection.get_database')
    @patch('services.telegram.notifications.send_message_sync')
    def test_notify_new_draft_success(self, mock_send, mock_db):
        """Test notify_new_draft sends notification successfully."""
        from services.telegram.notifications import notify_new_draft

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = {
            'id': 1,
            'from_address': 'test@example.com',
            'subject': 'Test Subject',
            'intent': 'quote_request',
            'draft_content': 'Test draft content',
        }

        with patch(
            'database.schema.ResponseRepository',
            return_value=mock_response_repo
        ):
            mock_send.return_value = True
            result = notify_new_draft(1)

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert 'Test Subject' in call_args[0][0]
        assert 'test@example.com' in call_args[0][0]

    @patch('database.connection.get_database')
    @patch('services.telegram.notifications.send_message_sync')
    def test_notify_new_draft_response_not_found(self, mock_send, mock_db):
        """Test notify_new_draft handles missing response."""
        from services.telegram.notifications import notify_new_draft

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = None

        with patch(
            'database.schema.ResponseRepository',
            return_value=mock_response_repo
        ):
            result = notify_new_draft(999)

        assert result is False
        mock_send.assert_not_called()

    @patch('database.connection.get_database')
    @patch('services.telegram.notifications.send_message_sync')
    def test_notify_send_success(self, mock_send, mock_db):
        """Test notify_send_success sends notification."""
        from services.telegram.notifications import notify_send_success

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = {
            'id': 1,
            'from_address': 'test@example.com',
            'subject': 'Test Subject',
            'sent_message_id': 'msg123',
        }

        with patch(
            'database.schema.ResponseRepository',
            return_value=mock_response_repo
        ):
            mock_send.return_value = True
            result = notify_send_success(1)

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert 'Email Sent Successfully' in call_args[0][0]

    @patch('database.connection.get_database')
    @patch('services.telegram.notifications.send_message_sync')
    def test_notify_send_failure(self, mock_send, mock_db):
        """Test notify_send_failure sends notification with error."""
        from services.telegram.notifications import notify_send_failure

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = {
            'id': 1,
            'from_address': 'test@example.com',
            'subject': 'Test Subject',
            'send_attempts': 3,
        }

        with patch(
            'database.schema.ResponseRepository',
            return_value=mock_response_repo
        ):
            mock_send.return_value = True
            result = notify_send_failure(1, 'Connection timeout')

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert 'Email Send Failed' in call_args[0][0]
        assert 'Connection timeout' in call_args[0][0]


class TestCommandHandlers:
    """Tests for bot command handlers."""

    @pytest.mark.asyncio
    async def test_start_command(self):
        """Test /start command responds with welcome message."""
        from services.telegram.bot import start_command

        mock_update = Mock()
        mock_update.effective_chat.id = 12345
        mock_update.effective_user.username = 'testuser'
        mock_update.effective_user.id = 67890
        mock_update.message.reply_text = AsyncMock()

        mock_context = Mock()

        await start_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        assert 'Welcome' in message
        assert '12345' in message
        assert '/pending' in message

    @pytest.mark.asyncio
    async def test_help_command(self):
        """Test /help command responds with help text."""
        from services.telegram.bot import help_command

        mock_update = Mock()
        mock_update.message.reply_text = AsyncMock()

        mock_context = Mock()

        await help_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        assert '/start' in message
        assert '/pending' in message
        assert '/stats' in message

    @pytest.mark.asyncio
    @patch('services.telegram.bot.get_repositories')
    async def test_pending_command_no_drafts(self, mock_get_repos):
        """Test /pending command with no pending drafts."""
        from services.telegram.bot import pending_command

        mock_response_repo = Mock()
        mock_response_repo.get_pending_drafts.return_value = []
        mock_get_repos.return_value = {
            'response': mock_response_repo,
            'email': Mock(),
        }

        mock_update = Mock()
        mock_update.message.reply_text = AsyncMock()

        mock_context = Mock()

        await pending_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        assert 'No pending drafts' in message

    @pytest.mark.asyncio
    @patch('services.telegram.bot.get_repositories')
    async def test_stats_command(self, mock_get_repos):
        """Test /stats command responds with statistics."""
        from services.telegram.bot import stats_command

        mock_email_repo = Mock()
        mock_email_repo.count_by_status.return_value = {
            'pending': 5,
            'classified': 10,
            'responded': 20,
            'failed': 2,
        }

        mock_response_repo = Mock()
        mock_response_repo.count_pending_drafts.return_value = 3
        mock_response_repo.get_responses_by_status.return_value = []

        mock_get_repos.return_value = {
            'email': mock_email_repo,
            'response': mock_response_repo,
        }

        mock_update = Mock()
        mock_update.message.reply_text = AsyncMock()

        mock_context = Mock()

        await stats_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        assert 'Pending: 5' in message
        assert 'Classified: 10' in message


class TestCallbackHandlers:
    """Tests for inline button callback handlers."""

    @pytest.mark.asyncio
    async def test_callback_invalid_data(self):
        """Test callback handler with invalid data format."""
        from services.telegram.bot import button_callback

        mock_query = Mock()
        mock_query.data = 'invaliddata'
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = Mock()
        mock_update.callback_query = mock_query

        mock_context = Mock()

        await button_callback(mock_update, mock_context)

        mock_query.answer.assert_called_once()
        mock_query.edit_message_text.assert_called_once_with('Invalid callback data.')

    @pytest.mark.asyncio
    async def test_callback_invalid_response_id(self):
        """Test callback handler with non-numeric response ID."""
        from services.telegram.bot import button_callback

        mock_query = Mock()
        mock_query.data = 'approve:abc'
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = Mock()
        mock_update.callback_query = mock_query

        mock_context = Mock()

        await button_callback(mock_update, mock_context)

        mock_query.edit_message_text.assert_called_once_with('Invalid response ID.')

    @pytest.mark.asyncio
    @patch('services.telegram.bot.get_repositories')
    async def test_callback_approve_success(self, mock_get_repos):
        """Test approve callback handler success."""
        from services.telegram.bot import button_callback

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = {
            'id': 1,
            'status': 'draft',
            'from_address': 'test@example.com',
            'subject': 'Test',
        }
        mock_response_repo.approve_response.return_value = True
        mock_get_repos.return_value = {
            'response': mock_response_repo,
            'email': Mock(),
        }

        mock_query = Mock()
        mock_query.data = 'approve:1'
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = Mock()
        mock_update.callback_query = mock_query
        mock_update.effective_user.username = 'testadmin'
        mock_update.effective_user.id = 12345

        mock_context = Mock()

        with patch('services.telegram.bot.send_single_response_task') as mock_task:
            mock_task.delay = Mock()
            await button_callback(mock_update, mock_context)

        mock_response_repo.approve_response.assert_called_once_with(1, 'testadmin')
        mock_task.delay.assert_called_once_with(1)

    @pytest.mark.asyncio
    @patch('services.telegram.bot.get_repositories')
    async def test_callback_reject_success(self, mock_get_repos):
        """Test reject callback handler success."""
        from services.telegram.bot import button_callback

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = {
            'id': 1,
            'status': 'draft',
        }
        mock_response_repo.reject_response.return_value = True
        mock_get_repos.return_value = {
            'response': mock_response_repo,
            'email': Mock(),
        }

        mock_query = Mock()
        mock_query.data = 'reject:1'
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = Mock()
        mock_update.callback_query = mock_query

        mock_context = Mock()

        await button_callback(mock_update, mock_context)

        mock_response_repo.reject_response.assert_called_once_with(1)
        call_args = mock_query.edit_message_text.call_args
        assert 'rejected' in call_args[0][0]

    @pytest.mark.asyncio
    @patch('services.telegram.bot.get_repositories')
    async def test_callback_view_draft(self, mock_get_repos):
        """Test view callback handler shows draft content."""
        from services.telegram.bot import button_callback

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = {
            'id': 1,
            'status': 'draft',
            'from_address': 'test@example.com',
            'subject': 'Test Subject',
            'intent': 'quote_request',
            'draft_content': 'This is the draft email content.',
        }
        mock_get_repos.return_value = {
            'response': mock_response_repo,
            'email': Mock(),
        }

        mock_query = Mock()
        mock_query.data = 'view:1'
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = Mock()
        mock_update.callback_query = mock_query

        mock_context = Mock()

        await button_callback(mock_update, mock_context)

        call_args = mock_query.edit_message_text.call_args
        message = call_args[0][0]
        assert 'Test Subject' in message
        assert 'test@example.com' in message
        assert 'This is the draft email content.' in message

    @pytest.mark.asyncio
    @patch('services.telegram.bot.get_repositories')
    async def test_callback_already_processed(self, mock_get_repos):
        """Test callback handler when response already processed."""
        from services.telegram.bot import button_callback

        mock_response_repo = Mock()
        mock_response_repo.get_response_with_email.return_value = {
            'id': 1,
            'status': 'sent',
        }
        mock_get_repos.return_value = {
            'response': mock_response_repo,
            'email': Mock(),
        }

        mock_query = Mock()
        mock_query.data = 'approve:1'
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = Mock()
        mock_update.callback_query = mock_query

        mock_context = Mock()

        await button_callback(mock_update, mock_context)

        call_args = mock_query.edit_message_text.call_args
        assert 'already sent' in call_args[0][0]
