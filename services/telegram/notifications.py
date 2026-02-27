"""
Telegram notification functions for email automation.

This module provides functions to send formatted notifications
for various email processing events.
"""

import logging
import traceback
from datetime import datetime
from typing import Optional

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config.settings import settings

logger = logging.getLogger(__name__)

# Telegram message limit
MAX_MESSAGE_LENGTH = 4096


def _truncate_to_lines(text: str, max_lines: int = 4, max_chars: int = 300) -> str:
    """
    Truncate text to a maximum number of lines with ellipsis.

    Args:
        text: The text to truncate
        max_lines: Maximum number of lines to keep
        max_chars: Maximum total characters (safety limit)

    Returns:
        Truncated text with '...' if truncated
    """
    if not text:
        return ""

    lines = text.split("\n")
    truncated_lines = lines[:max_lines]
    result = "\n".join(truncated_lines)

    # Also apply character limit
    if len(result) > max_chars:
        result = result[:max_chars]

    # Add ellipsis if truncated
    if len(lines) > max_lines or len(text) > len(result):
        result = result.rstrip() + "\n..."

    return result


def get_bot() -> Optional[telegram.Bot]:
    """
    Get a configured Telegram bot instance.

    Returns:
        Bot instance or None if not configured.
    """
    token = settings.telegram.bot_token

    if not token or token == "your_bot_token_from_botfather":
        logger.warning("TELEGRAM_BOT_TOKEN not configured")
        return None

    return telegram.Bot(token=token)


def get_chat_id() -> Optional[str]:
    """
    Get the admin chat ID for notifications.

    Returns:
        Chat ID string or None if not configured.
    """
    chat_id = settings.telegram.admin_chat_id

    if not chat_id:
        logger.warning("TELEGRAM_ADMIN_CHAT_ID not configured")
        return None

    return chat_id


async def send_message_async(
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
) -> bool:
    """
    Send a message to the admin chat asynchronously.

    Args:
        text: Message text to send
        reply_markup: Optional inline keyboard
        parse_mode: Optional parse mode (HTML, Markdown)

    Returns:
        True if message was sent successfully
    """
    bot = get_bot()
    chat_id = get_chat_id()

    if not bot or not chat_id:
        logger.warning("Cannot send notification: bot or chat_id not configured")
        return False

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        logger.info(f"Notification sent to chat {chat_id}")
        return True

    except telegram.error.TelegramError as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False


def send_message_sync(
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
) -> bool:
    """
    Send a message to the admin chat synchronously.

    Uses asyncio to run the async send function.

    Args:
        text: Message text to send
        reply_markup: Optional inline keyboard
        parse_mode: Optional parse mode (HTML, Markdown)

    Returns:
        True if message was sent successfully
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_message_async(text, reply_markup, parse_mode))
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(send_message_async(text, reply_markup, parse_mode))
    except RuntimeError:
        return asyncio.run(send_message_async(text, reply_markup, parse_mode))
    except Exception as e:
        logger.error(f"Error in send_message_sync: {e}")
        return False


def notify_new_draft(response_id: int) -> bool:
    """
    Send notification for a new draft ready for review.

    Args:
        response_id: Database ID of the response

    Returns:
        True if notification was sent successfully
    """
    from database.connection import get_database
    from database.schema import ResponseRepository

    try:
        db = get_database()
        response_repo = ResponseRepository(db)

        response = response_repo.get_response_with_email(response_id)
        if not response:
            logger.warning(f"Response {response_id} not found for notification")
            return False

        from_addr = response.get("from_address", "Unknown")
        subject = response.get("subject", "No Subject")
        intent = response.get("intent", "unknown")
        draft_content = response.get("draft_content", "")
        # Field is aliased as 'original_body' in GET_RESPONSE_WITH_EMAIL query
        original_body = response.get("original_body") or response.get("body", "")

        # Truncate to ~4 lines (roughly 200 chars)
        original_preview = _truncate_to_lines(original_body, max_lines=4)

        # Truncate draft for preview
        draft_preview = draft_content[:200]
        if len(draft_content) > 200:
            draft_preview += "..."

        message = (
            "\U0001f4e7 New Draft Ready for Review\n\n"
            f"From: {from_addr}\n"
            f"Subject: {subject}\n"
            f"Intent: {intent}\n\n"
            f"\u2501\u2501 Original Message \u2501\u2501\n"
            f"{original_preview}\n\n"
            f"\u2501\u2501 Draft Response \u2501\u2501\n"
            f"{draft_preview}"
        )

        # Safety check for message length
        if len(message) > MAX_MESSAGE_LENGTH - 100:
            message = message[: MAX_MESSAGE_LENGTH - 150] + "\n... (truncated)"

        keyboard = [
            [
                InlineKeyboardButton("\u2705 Approve", callback_data=f"approve:{response_id}"),
                InlineKeyboardButton("\u274c Reject", callback_data=f"reject:{response_id}"),
            ],
            [
                InlineKeyboardButton("\u270f\ufe0f Edit", callback_data=f"edit:{response_id}"),
                InlineKeyboardButton("\U0001f441 View Full", callback_data=f"view:{response_id}"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        return send_message_sync(message, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error sending new draft notification: {e}\n{traceback.format_exc()}")
        return False


def notify_send_success(response_id: int) -> bool:
    """
    Send notification confirming email was sent successfully.

    Args:
        response_id: Database ID of the response

    Returns:
        True if notification was sent successfully
    """
    from database.connection import get_database
    from database.schema import ResponseRepository

    try:
        db = get_database()
        response_repo = ResponseRepository(db)

        response = response_repo.get_response_with_email(response_id)
        if not response:
            logger.warning(f"Response {response_id} not found for notification")
            return False

        from_addr = response.get("from_address", "Unknown")
        subject = response.get("subject", "No Subject")
        sent_message_id = response.get("sent_message_id", "N/A")

        message = (
            "\u2705 Email Sent Successfully\n\n"
            f"Response #{response_id}\n"
            f"To: {from_addr}\n"
            f"Subject: {subject}\n"
            f"Message ID: {sent_message_id}"
        )

        return send_message_sync(message)

    except Exception as e:
        logger.error(f"Error sending success notification: {e}\n{traceback.format_exc()}")
        return False


def notify_send_failure(response_id: int, error: str) -> bool:
    """
    Send notification alerting about email send failure.

    Args:
        response_id: Database ID of the response
        error: Error message describing the failure

    Returns:
        True if notification was sent successfully
    """
    from database.connection import get_database
    from database.schema import ResponseRepository

    try:
        db = get_database()
        response_repo = ResponseRepository(db)

        response = response_repo.get_response_with_email(response_id)
        if not response:
            logger.warning(f"Response {response_id} not found for notification")
            return False

        from_addr = response.get("from_address", "Unknown")
        subject = response.get("subject", "No Subject")
        send_attempts = response.get("send_attempts", 0)

        message = (
            "\u274c Email Send Failed\n\n"
            f"Response #{response_id}\n"
            f"To: {from_addr}\n"
            f"Subject: {subject}\n"
            f"Attempts: {send_attempts}\n\n"
            f"Error: {error[:500]}"
        )

        return send_message_sync(message)

    except Exception as e:
        logger.error(f"Error sending failure notification: {e}\n{traceback.format_exc()}")
        return False


def notify_calendar_created(response_id: int, event_link: str) -> bool:
    """
    Send notification confirming a calendar event was created.

    Args:
        response_id: Database ID of the response
        event_link: Google Calendar event URL

    Returns:
        True if notification was sent successfully
    """
    from database.connection import get_database
    from database.schema import ResponseRepository

    try:
        db = get_database()
        response_repo = ResponseRepository(db)

        response = response_repo.get_response_with_email(response_id)
        if not response:
            logger.warning(f"Response {response_id} not found for calendar notification")
            return False

        from_addr = response.get("from_address", "Unknown")
        subject = response.get("subject", "No Subject")

        message = (
            f"\U0001f4c5 Calendar Event Created\n\nResponse #{response_id}\nCustomer: {from_addr}\nSubject: {subject}\n"
        )

        if event_link:
            message += f"\nView in Calendar: {event_link}"

        return send_message_sync(message)

    except Exception as e:
        logger.error(f"Error sending calendar created notification: {e}\n{traceback.format_exc()}")
        return False


def notify_calendar_conflict(
    response_id: int,
    proposed_start: datetime,
    proposed_end: datetime,
    conflicts: list,
) -> bool:
    """
    Send notification about a calendar conflict with action buttons.

    Args:
        response_id: Database ID of the response
        proposed_start: Proposed event start datetime
        proposed_end: Proposed event end datetime
        conflicts: List of conflict dicts with 'title', 'start', 'end'

    Returns:
        True if notification was sent successfully
    """
    from database.connection import get_database
    from database.schema import ResponseRepository

    try:
        db = get_database()
        response_repo = ResponseRepository(db)

        response = response_repo.get_response_with_email(response_id)
        if not response:
            logger.warning(f"Response {response_id} not found for conflict notification")
            return False

        from_addr = response.get("from_address", "Unknown")

        # Format proposed time
        proposed_str = proposed_start.strftime("%A, %b %d at %I:%M %p")

        # Format conflicts
        conflict_lines = []
        for c in conflicts:
            conflict_lines.append(f'- "{c.get("title", "Untitled")}" ({c.get("start", "?")} - {c.get("end", "?")})')
        conflict_text = "\n".join(conflict_lines)

        message = (
            "\u26a0\ufe0f Calendar Conflict Detected\n\n"
            f"Response #{response_id}\n"
            f"Customer: {from_addr}\n"
            f"Requested: {proposed_str}\n\n"
            f"Conflicts with:\n"
            f"{conflict_text}"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "\u2705 Create Anyway",
                    callback_data=f"calendar_force:{response_id}",
                ),
                InlineKeyboardButton(
                    "\u23ed Skip",
                    callback_data=f"calendar_skip:{response_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "\U0001f50d View Details",
                    callback_data=f"calendar_details:{response_id}",
                ),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        return send_message_sync(message, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error sending calendar conflict notification: {e}\n{traceback.format_exc()}")
        return False


def notify_calendar_failed(response_id: int, error: str) -> bool:
    """
    Send notification about a calendar event creation failure.

    Args:
        response_id: Database ID of the response
        error: Error description

    Returns:
        True if notification was sent successfully
    """
    message = f"\u274c Calendar Event Failed\n\nResponse #{response_id}\nError: {error[:500]}"

    return send_message_sync(message)


def notify_manual_event_synced(event_details: dict) -> bool:
    """
    Send notification about a manually-added Google Calendar event.

    Args:
        event_details: Dict with event data from calendar_events table

    Returns:
        True if notification was sent successfully
    """
    try:
        title = event_details.get("title", "Untitled")
        location = event_details.get("location", "No location")
        start_time = event_details.get("start_time")

        date_str = "Unknown"
        if start_time:
            if hasattr(start_time, "strftime"):
                date_str = start_time.strftime("%A, %b %d at %I:%M %p")
            else:
                date_str = str(start_time)

        end_time = event_details.get("end_time")
        duration_str = ""
        if start_time and end_time and hasattr(start_time, "__sub__"):
            duration = end_time - start_time
            hours = duration.total_seconds() / 3600
            duration_str = f"\nDuration: {hours:.1f} hours"

        message = (
            "\U0001f4c5 New Booking Added (Manual)\n\n"
            f"Title: {title}\n"
            f"\U0001f550 {date_str}\n"
            f"\U0001f4cd {location}"
            f"{duration_str}\n\n"
            "This event was added directly in Google Calendar."
        )

        return send_message_sync(message)

    except Exception as e:
        logger.error(f"Error sending manual event notification: {e}\n{traceback.format_exc()}")
        return False


def notify_new_email_received(email_id: int) -> bool:
    """
    Send notification for a new email received (optional).

    Args:
        email_id: Database ID of the email

    Returns:
        True if notification was sent successfully
    """
    from database.connection import get_database
    from database.schema import EmailRepository

    try:
        db = get_database()
        email_repo = EmailRepository(db)

        email = email_repo.get_email_by_id(email_id)
        if not email:
            logger.warning(f"Email {email_id} not found for notification")
            return False

        from_addr = email.get("from_address", "Unknown")
        subject = email.get("subject", "No Subject")

        message = (
            "\U0001f4e5 New Email Received\n\n"
            f"Email #{email_id}\n"
            f"From: {from_addr}\n"
            f"Subject: {subject}\n\n"
            "Processing will begin shortly..."
        )

        return send_message_sync(message)

    except Exception as e:
        logger.error(f"Error sending new email notification: {e}\n{traceback.format_exc()}")
        return False
