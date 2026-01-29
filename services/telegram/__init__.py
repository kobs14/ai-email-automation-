"""
Telegram bot service for email automation notifications and approvals.

This package provides:
- Bot commands for managing email response drafts
- Real-time notifications for new drafts
- Inline approval/rejection functionality

Components:
- bot.py: Main bot handlers and commands
- notifications.py: Notification sending functions
"""

from .notifications import (
    notify_new_draft,
    notify_send_success,
    notify_send_failure,
)

__all__ = [
    'notify_new_draft',
    'notify_send_success',
    'notify_send_failure',
]
