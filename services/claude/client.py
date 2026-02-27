"""
Claude API client helper.

Provides a configured Anthropic client instance.
"""

import logging
from typing import Optional

from anthropic import Anthropic

from config.settings import settings

logger = logging.getLogger(__name__)

# Module-level client cache
_client: Optional[Anthropic] = None


def get_claude_client() -> Anthropic:
    """
    Get or create a configured Anthropic client.

    Returns:
        Configured Anthropic client instance

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not configured
    """
    global _client

    if _client is not None:
        return _client

    if not settings.claude.validate():
        raise ValueError("ANTHROPIC_API_KEY is not configured. Set it in .env file.")

    _client = Anthropic(api_key=settings.claude.api_key)
    logger.info(f"Claude client initialized with model: {settings.claude.model}")

    return _client


def reset_client() -> None:
    """Reset the cached client (useful for testing)."""
    global _client
    _client = None
