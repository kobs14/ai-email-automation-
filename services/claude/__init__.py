"""
Claude AI service module for email processing.

Provides:
- Email intent classification
- Entity extraction
- Response generation
"""

from .classifier import VALID_INTENTS, classify_email
from .client import get_claude_client
from .extractor import extract_entities
from .processor import process_email_with_claude
from .responder import generate_response

__all__ = [
    "get_claude_client",
    "classify_email",
    "extract_entities",
    "generate_response",
    "process_email_with_claude",
    "VALID_INTENTS",
]
