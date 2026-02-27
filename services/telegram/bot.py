"""
Telegram bot for email automation notifications and approvals.

This module provides:
- /start: Register chat and show welcome message
- /pending: List pending drafts awaiting approval
- /stats: Show counts by status
- /help: Command reference
- Callback handlers for inline buttons (approve/reject/view)

Usage:
    python -m services.telegram.bot
"""

import logging
import sys
import traceback
from pathlib import Path
from typing import Optional

# Telegram message limit
MAX_MESSAGE_LENGTH = 4096

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config.settings import settings

logger = logging.getLogger(__name__)


def _is_admin(update: Update) -> bool:
    """
    Check if the message sender is the configured admin.

    Args:
        update: Telegram update object

    Returns:
        True if sender's chat ID matches TELEGRAM_ADMIN_CHAT_ID
    """
    admin_chat_id = settings.telegram.admin_chat_id
    if not admin_chat_id:
        return False
    return str(update.effective_chat.id) == str(admin_chat_id)


async def _reject_unauthorized(update: Update) -> bool:
    """
    Check authorization and send rejection message if unauthorized.

    Args:
        update: Telegram update object

    Returns:
        True if unauthorized (caller should return early)
    """
    if _is_admin(update):
        return False

    logger.warning(
        f"Unauthorized access attempt from chat_id={update.effective_chat.id} "
        f"user={update.effective_user.username or update.effective_user.id}"
    )
    if update.message:
        await update.message.reply_text("\u26d4 Unauthorized. This bot is restricted to the admin account.")
    elif update.callback_query:
        await update.callback_query.answer(
            "Unauthorized. This bot is restricted to the admin account.",
            show_alert=True,
        )
    return True


def get_repositories():
    """Get repository instances with database connection."""
    from database.connection import get_database
    from database.schema import EmailRepository, ResponseRepository

    db = get_database()
    return {
        "email": EmailRepository(db),
        "response": ResponseRepository(db),
    }


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command.

    Welcomes the user and displays available commands.
    """
    if await _reject_unauthorized(update):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user

    logger.info(f"User {user.username or user.id} started bot (chat_id={chat_id})")

    welcome_message = (
        f"\U0001f3e0 Welcome to EcoClean Email Bot!\n\n"
        f"Your Chat ID: {chat_id}\n\n"
        f"Available commands:\n"
        f"\U0001f4cb  /pending - View pending response drafts\n"
        f"\U0001f4c5  /calendar - View upcoming calendar events\n"
        f"\U0001f4ca  /stats - View email statistics\n"
        f"\u274c  /cancel - Cancel current edit\n"
        f"\u2753  /help - Show all commands\n\n"
        f"You will receive notifications when new email drafts are ready for review.\n"
        f"Each notification includes the original message and draft response.\n"
        f"You can approve, reject, or edit drafts before sending."
    )

    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if await _reject_unauthorized(update):
        return

    help_text = (
        "\U0001f3e0 EcoClean Email Bot\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        "Commands:\n"
        "\U0001f4cb  /pending - List all pending response drafts\n"
        "\U0001f4c5  /calendar - View upcoming calendar events\n"
        "\U0001f4ca  /stats - Show email and response statistics\n"
        "\u274c  /cancel - Cancel current edit operation\n"
        "\u2753  /help - Show this help message\n\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "Draft Review:\n"
        "When a new draft is ready, you'll receive a notification with:\n"
        "\u2022 Original message preview from the sender\n"
        "\u2022 AI-generated draft response preview\n\n"
        "Action Buttons:\n"
        "\u2022 \u2705 Approve \u2014 Send the response immediately\n"
        "\u2022 \u274c Reject \u2014 Mark draft as rejected\n"
        "\u2022 \u270f\ufe0f Edit \u2014 Modify the draft before approving\n"
        "\u2022 \U0001f441 View Full \u2014 See complete message and draft\n\n"
        "Editing Drafts:\n"
        "1. Click '\u270f\ufe0f Edit' on any draft\n"
        "2. Type your new response text\n"
        "3. Send the message to save\n"
        "4. Use /cancel to abort editing"
    )

    await update.message.reply_text(help_text)


async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /pending command.

    Lists all pending response drafts awaiting approval.
    """
    if await _reject_unauthorized(update):
        return

    try:
        repos = get_repositories()
        response_repo = repos["response"]

        pending_drafts = response_repo.get_pending_drafts()

        if not pending_drafts:
            await update.message.reply_text("\U0001f4cb No pending drafts awaiting review.")
            return

        # Send header message
        await update.message.reply_text(f"\U0001f4cb Pending Drafts  \u2014  {len(pending_drafts)} awaiting review")

        for _i, draft in enumerate(pending_drafts[:10], 1):
            from_addr = draft.get("from_address", "Unknown")
            subject = draft.get("subject", "No Subject")[:40]
            intent = draft.get("intent", "unknown")
            response_id = draft["id"]

            keyboard = [
                [
                    InlineKeyboardButton("\u2705 Approve", callback_data=f"approve:{response_id}"),
                    InlineKeyboardButton("\u274c Reject", callback_data=f"reject:{response_id}"),
                ],
                [
                    InlineKeyboardButton("\u270f\ufe0f Edit", callback_data=f"edit:{response_id}"),
                    InlineKeyboardButton("\U0001f441 View", callback_data=f"view:{response_id}"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"\U0001f4c4 Draft #{response_id}\nFrom: {from_addr}\nSubject: {subject}\nIntent: {intent}",
                reply_markup=reply_markup,
            )

        if len(pending_drafts) > 10:
            await update.message.reply_text(f"\U0001f4cb ... and {len(pending_drafts) - 10} more pending drafts.")

    except Exception as e:
        logger.error(f"Error in pending_command: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("\u26a0\ufe0f Error fetching pending drafts. Please try again.")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /stats command.

    Shows email and response statistics.
    """
    if await _reject_unauthorized(update):
        return

    try:
        repos = get_repositories()
        email_repo = repos["email"]
        response_repo = repos["response"]

        email_stats = email_repo.count_by_status()

        responses_by_status = {}
        for status in ["draft", "approved", "sent", "rejected", "failed"]:
            responses = response_repo.get_responses_by_status(status, limit=1000)
            responses_by_status[status] = len(responses)

        stats_message = (
            "\U0001f4ca Email Statistics\n"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
            f"\U0001f4e5 Pending: {email_stats.get('pending', 0)}\n"
            f"\U0001f3f7 Classified: {email_stats.get('classified', 0)}\n"
            f"\u2705 Responded: {email_stats.get('responded', 0)}\n"
            f"\u274c Failed: {email_stats.get('failed', 0)}\n\n"
            "\U0001f4ca Response Statistics\n"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
            f"\U0001f4dd Pending Drafts: {responses_by_status.get('draft', 0)}\n"
            f"\U0001f44d Approved: {responses_by_status.get('approved', 0)}\n"
            f"\U0001f4e4 Sent: {responses_by_status.get('sent', 0)}\n"
            f"\U0001f6ab Rejected: {responses_by_status.get('rejected', 0)}\n"
            f"\u274c Failed: {responses_by_status.get('failed', 0)}"
        )

        await update.message.reply_text(stats_message)

    except Exception as e:
        logger.error(f"Error in stats_command: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("\u26a0\ufe0f Error fetching statistics. Please try again.")


async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /calendar command.

    Shows upcoming calendar events from the database.
    """
    if await _reject_unauthorized(update):
        return

    try:
        from database.connection import get_database
        from database.queries import calendar as cal_queries

        db = get_database()

        events = db.execute_query(
            cal_queries.GET_UPCOMING_CALENDAR_EVENTS,
            params=(10,),
            fetch="all",
        )

        if not events:
            await update.message.reply_text("\U0001f4c5 No upcoming calendar events.")
            return

        await update.message.reply_text(f"\U0001f4c5 Upcoming Events  \u2014  {len(events)} scheduled")

        for event in events:
            event = dict(event)
            title = event.get("title", "Untitled")
            location = event.get("location", "")
            start_time = event.get("start_time")
            end_time = event.get("end_time")
            source = event.get("source", "unknown")
            customer = event.get("customer_name", "")

            date_str = "Unknown"
            time_str = ""
            if start_time and hasattr(start_time, "strftime"):
                date_str = start_time.strftime("%a, %b %d")
                time_str = start_time.strftime("%I:%M %p")

            duration_str = ""
            if start_time and end_time and hasattr(start_time, "__sub__"):
                duration = end_time - start_time
                hours = duration.total_seconds() / 3600
                duration_str = f" ({hours:.1f}h)"

            source_label = "Manual" if source == "manual" else "Auto"

            lines = [f"\U0001f4c5 {title}"]
            lines.append(f"\U0001f550 {date_str} at {time_str}{duration_str}")
            if customer:
                lines.append(f"\U0001f464 {customer}")
            if location:
                lines.append(f"\U0001f4cd {location}")
            lines.append(f"Source: {source_label}")

            await update.message.reply_text("\n".join(lines))

    except Exception as e:
        logger.error(f"Error in calendar_command: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("\u26a0\ufe0f Error fetching calendar events. Please try again.")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle inline button callbacks.

    Processes approve, reject, and view actions for response drafts.
    """
    if await _reject_unauthorized(update):
        return

    query = update.callback_query
    await query.answer()

    data = query.data
    user = update.effective_user
    logger.info(f"Callback received: {data} from user {user.username or user.id}")

    if ":" not in data:
        await query.edit_message_text("\u26a0\ufe0f Invalid callback data.")
        return

    action, response_id_str = data.split(":", 1)

    try:
        response_id = int(response_id_str)
    except ValueError:
        await query.edit_message_text("\u26a0\ufe0f Invalid response ID.")
        return

    try:
        repos = get_repositories()
        response_repo = repos["response"]

        response = response_repo.get_response_with_email(response_id)
        if not response:
            await query.edit_message_text(f"\u26a0\ufe0f Response #{response_id} not found.")
            return

        current_status = response.get("status")

        if action == "approve":
            if current_status != "draft":
                await query.edit_message_text(f"\u2139\ufe0f Response #{response_id} is already {current_status}.")
                return

            user = update.effective_user
            approved_by = user.username or str(user.id)
            success = response_repo.approve_response(response_id, approved_by)

            if success:
                logger.info(f"Response {response_id} approved by {approved_by} via Telegram")

                from services.celery_app import app as celery_app

                celery_app.send_task("services.tasks.email_tasks.send_single_response_task", args=[response_id])

                await query.edit_message_text(
                    f"\u2705 Response #{response_id} approved by {approved_by}.\nEmail will be sent shortly."
                )
            else:
                await query.edit_message_text(f"\u26a0\ufe0f Failed to approve response #{response_id}.")

        elif action == "reject":
            if current_status != "draft":
                await query.edit_message_text(f"\u2139\ufe0f Response #{response_id} is already {current_status}.")
                return

            success = response_repo.reject_response(response_id)

            if success:
                logger.info(f"Response {response_id} rejected via Telegram")
                await query.edit_message_text(f"\U0001f6ab Response #{response_id} has been rejected.")
            else:
                await query.edit_message_text(f"\u26a0\ufe0f Failed to reject response #{response_id}.")

        elif action == "view":
            draft_content = response.get("draft_content", "No content")
            from_addr = response.get("from_address", "Unknown")
            subject = response.get("subject", "No Subject")
            intent = response.get("intent", "unknown")
            status = response.get("status", "unknown")
            # Field is aliased as 'original_body' in GET_RESPONSE_WITH_EMAIL query
            original_body = response.get("original_body") or response.get("body") or "No original message"

            # Build header (fixed size)
            header = (
                f"\U0001f4c4 Response #{response_id}\n"
                f"Status: {status}\n"
                f"From: {from_addr}\n"
                f"Subject: {subject}\n"
                f"Intent: {intent}\n\n"
            )

            # Calculate available space for content (reserve 200 for buttons/formatting)
            available_space = MAX_MESSAGE_LENGTH - len(header) - 200
            half_space = available_space // 2

            # Truncate original message
            original_truncated = original_body[:half_space]
            if len(original_body) > half_space:
                original_truncated = original_truncated.rstrip() + "\n... (truncated)"

            # Truncate draft
            draft_truncated = draft_content[:half_space]
            if len(draft_content) > half_space:
                draft_truncated = draft_truncated.rstrip() + "\n... (truncated)"

            view_message = (
                f"{header}"
                f"\u2501\u2501 Original Message \u2501\u2501\n"
                f"{original_truncated}\n\n"
                f"\u2501\u2501 Draft Response \u2501\u2501\n"
                f"{draft_truncated}"
            )

            # Final safety check
            if len(view_message) > MAX_MESSAGE_LENGTH - 100:
                view_message = view_message[: MAX_MESSAGE_LENGTH - 150] + "\n... (message truncated)"

            keyboard = []
            if status == "draft":
                keyboard = [
                    [
                        InlineKeyboardButton("\u2705 Approve", callback_data=f"approve:{response_id}"),
                        InlineKeyboardButton("\u274c Reject", callback_data=f"reject:{response_id}"),
                    ],
                    [
                        InlineKeyboardButton("\u270f\ufe0f Edit", callback_data=f"edit:{response_id}"),
                    ],
                ]

            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

            await query.edit_message_text(view_message, reply_markup=reply_markup)

        elif action == "edit":
            if current_status != "draft":
                await query.edit_message_text(
                    f"\u2139\ufe0f Response #{response_id} is already {current_status} and cannot be edited."
                )
                return

            # Check if user is already editing another draft
            current_editing = context.user_data.get("editing_response_id")
            if current_editing and current_editing != response_id:
                logger.info(f"User switching edit from {current_editing} to {response_id}")

            # Store the response_id in user_data for the edit flow
            context.user_data["editing_response_id"] = response_id

            draft_content = response.get("draft_content", "No content")
            from_addr = response.get("from_address", "Unknown")
            subject = response.get("subject", "No Subject")

            # Show current draft and prompt for new content
            edit_message = (
                f"\u270f\ufe0f Editing Response #{response_id}\n"
                f"To: {from_addr}\n"
                f"Subject: {subject}\n\n"
                f"\u2501\u2501 Current Draft \u2501\u2501\n"
                f"{draft_content[:2000]}\n"
                f"{'... (truncated)' if len(draft_content) > 2000 else ''}\n\n"
                f"Reply with your edited response text.\n"
                f"Send /cancel to cancel editing."
            )

            keyboard = [
                [
                    InlineKeyboardButton("\u274c Cancel Edit", callback_data=f"cancel_edit:{response_id}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(edit_message, reply_markup=reply_markup)

        elif action == "cancel_edit":
            # Clear editing state
            context.user_data.pop("editing_response_id", None)

            await query.edit_message_text(
                f"\u274c Edit cancelled for Response #{response_id}.\nUse /pending to view drafts again."
            )

        elif action == "calendar_force":
            # Force-create calendar event despite conflicts
            try:
                from services.celery_app import app as celery_app

                celery_app.send_task(
                    "services.tasks.calendar_tasks.force_create_calendar_event_task",
                    args=[response_id],
                )
                await query.edit_message_text(
                    f"\u2705 Calendar event for Response #{response_id} will be created (ignoring conflicts)."
                )
            except Exception as e:
                logger.error(f"Failed to queue force calendar task: {e}")
                await query.edit_message_text("\u26a0\ufe0f Failed to create calendar event. Please try again.")

        elif action == "calendar_skip":
            # Skip calendar event creation
            try:
                from database.connection import get_database
                from database.queries import calendar as cal_queries

                db = get_database()
                db.execute_query(
                    cal_queries.UPDATE_RESPONSE_CALENDAR_STATUS,
                    params=(None, "skipped", response_id),
                    fetch="one",
                )
                await query.edit_message_text(f"\u23ed Calendar event skipped for Response #{response_id}.")
            except Exception as e:
                logger.error(f"Failed to skip calendar event: {e}")
                await query.edit_message_text("\u26a0\ufe0f Error updating calendar status. Please try again.")

        elif action == "calendar_details":
            # Show conflict details
            try:
                import json

                conflict_details = response.get("calendar_conflict_details")
                if conflict_details:
                    if isinstance(conflict_details, str):
                        conflict_details = json.loads(conflict_details)

                    lines = ["\u26a0\ufe0f Calendar Conflict Details\n"]
                    lines.append(f"Response #{response_id}\n")
                    for c in conflict_details:
                        lines.append(f"- {c.get('title', 'Untitled')}: {c.get('start', '?')} - {c.get('end', '?')}")

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
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await query.edit_message_text(
                        "\n".join(lines),
                        reply_markup=reply_markup,
                    )
                else:
                    await query.edit_message_text(
                        f"\u2139\ufe0f No conflict details available for Response #{response_id}."
                    )
            except Exception as e:
                logger.error(f"Failed to show conflict details: {e}")
                await query.edit_message_text("\u26a0\ufe0f Error loading conflict details. Please try again.")

        else:
            await query.edit_message_text(f"Unknown action: {action}")

    except Exception as e:
        logger.error(f"Error handling callback {data}: {e}\n{traceback.format_exc()}")
        await query.edit_message_text("\u26a0\ufe0f Error processing action. Please try again.")


async def handle_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming message when user is editing a draft.

    Receives the new draft content and updates the database.
    """
    if await _reject_unauthorized(update):
        return

    response_id = context.user_data.get("editing_response_id")

    if not response_id:
        # Not in edit mode, ignore this message
        logger.debug("Message received but not in edit mode, ignoring")
        return

    user = update.effective_user
    logger.info(f"Edit message received for response {response_id} from {user.username or user.id}")

    new_content = update.message.text

    if not new_content or len(new_content.strip()) == 0:
        await update.message.reply_text(
            "\u26a0\ufe0f Draft content cannot be empty. Please send the new response text."
        )
        return

    try:
        repos = get_repositories()
        response_repo = repos["response"]

        # Verify response still exists and is a draft
        response = response_repo.get_response_with_email(response_id)
        if not response:
            await update.message.reply_text(f"\u26a0\ufe0f Response #{response_id} not found.")
            context.user_data.pop("editing_response_id", None)
            return

        if response.get("status") != "draft":
            await update.message.reply_text(
                f"\u2139\ufe0f Response #{response_id} is no longer a draft and cannot be edited."
            )
            context.user_data.pop("editing_response_id", None)
            return

        # Update the draft content
        success = response_repo.update_content(response_id, new_content.strip())

        if success:
            logger.info(f"Response {response_id} content updated via Telegram")

            # Clear editing state
            context.user_data.pop("editing_response_id", None)

            # Show success with action buttons
            keyboard = [
                [
                    InlineKeyboardButton("\u2705 Approve", callback_data=f"approve:{response_id}"),
                    InlineKeyboardButton("\u274c Reject", callback_data=f"reject:{response_id}"),
                ],
                [
                    InlineKeyboardButton("\u270f\ufe0f Edit Again", callback_data=f"edit:{response_id}"),
                    InlineKeyboardButton("\U0001f441 View Full", callback_data=f"view:{response_id}"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Show preview of updated content
            preview = new_content[:500]
            if len(new_content) > 500:
                preview += "..."

            await update.message.reply_text(
                f"\u2705 Response #{response_id} updated successfully!\n\n"
                f"\u2501\u2501 New Draft Preview \u2501\u2501\n"
                f"{preview}",
                reply_markup=reply_markup,
            )
        else:
            await update.message.reply_text(f"\u26a0\ufe0f Failed to update Response #{response_id}. Please try again.")

    except Exception as e:
        logger.error(f"Error updating response {response_id}: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("\u26a0\ufe0f Error updating draft. Please try again.")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command to exit edit mode."""
    if await _reject_unauthorized(update):
        return

    response_id = context.user_data.pop("editing_response_id", None)

    if response_id:
        await update.message.reply_text(
            f"\u274c Edit cancelled for Response #{response_id}.\nUse /pending to view drafts."
        )
    else:
        await update.message.reply_text("\u2139\ufe0f Nothing to cancel. You're not currently editing any draft.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by Updates."""
    logger.error(f"Update {update} caused error: {context.error}")


async def set_bot_commands(application: Application) -> None:
    """
    Set the bot's command menu.

    This creates the menu that appears when users tap the '/' button.
    """
    commands = [
        BotCommand("pending", "View drafts awaiting approval"),
        BotCommand("calendar", "View upcoming calendar events"),
        BotCommand("stats", "Show email statistics"),
        BotCommand("help", "Show help and commands"),
        BotCommand("cancel", "Cancel current edit"),
        BotCommand("start", "Start the bot"),
    ]

    await application.bot.set_my_commands(commands)
    logger.info("Bot menu commands set successfully")


def create_application() -> Optional[Application]:
    """
    Create and configure the Telegram bot application.

    Returns:
        Application instance or None if token not configured.
    """
    token = settings.telegram.bot_token

    if not token or token == "your_bot_token_from_botfather":
        logger.warning("TELEGRAM_BOT_TOKEN not configured. Bot will not start.")
        return None

    application = Application.builder().token(token).post_init(set_bot_commands).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("pending", pending_command))
    application.add_handler(CommandHandler("calendar", calendar_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Message handler for receiving edited draft content
    # Only processes messages when user is in edit mode (has editing_response_id)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_message))

    application.add_error_handler(error_handler)

    return application


def main() -> None:
    """Run the Telegram bot."""
    settings.configure_logging()

    # Log startup info
    logger.info("=" * 50)
    logger.info("Starting EcoClean Telegram Bot")
    logger.info(f"Log level: {settings.app.log_level}")
    logger.info(f"Bot token configured: {bool(settings.telegram.bot_token)}")
    logger.info(f"Admin chat ID: {settings.telegram.admin_chat_id or 'Not set'}")
    logger.info("=" * 50)

    application = create_application()

    if application is None:
        logger.error("Failed to create bot application. Exiting.")
        sys.exit(1)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    logger.info("Handlers registered: /start, /help, /pending, /calendar, /stats, /cancel")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
