"""
Claude AI service module for email processing.

Provides:
- Email intent classification
- Entity extraction
- Response generation
"""

from .client import get_claude_client
from .classifier import classify_email, VALID_INTENTS
from .extractor import extract_entities
from .responder import generate_response
from .processor import process_email_with_claude

__all__ = [
    'get_claude_client',
    'classify_email',
    'extract_entities',
    'generate_response',
    'process_email_with_claude',
    'VALID_INTENTS',
]
