"""
Email intent classification using Claude API.

Classifies emails into categories:
- quote_request
- booking_request
- rescheduling
- complaint
- general_inquiry
"""

import json
import logging
from typing import Any, Dict, Optional

from anthropic import Anthropic

from config.settings import settings

from .client import get_claude_client

logger = logging.getLogger(__name__)

# Valid intent categories
VALID_INTENTS = [
    "quote_request",
    "booking_request",
    "rescheduling",
    "complaint",
    "general_inquiry",
]

CLASSIFICATION_PROMPT = """You are an AI assistant for a cleaning service company. Your task is to classify incoming customer emails by their primary intent.

Analyze the following email and classify it into exactly ONE of these categories:
- quote_request: Customer is asking for pricing or a quote for cleaning services
- booking_request: Customer wants to schedule/book a specific cleaning appointment
- rescheduling: Customer wants to change or cancel an existing appointment
- complaint: Customer is expressing dissatisfaction or reporting an issue
- general_inquiry: Customer has general questions not fitting other categories

Respond with a JSON object containing:
- "intent": The classified intent (one of the categories above)
- "confidence": Your confidence level (0.0 to 1.0)
- "reasoning": Brief explanation of why you chose this classification

Email:
From: {from_address}
Subject: {subject}

{body}

Respond ONLY with the JSON object, no other text."""


def classify_email(
    body: str, from_address: str = "", subject: str = "", client: Optional[Anthropic] = None
) -> Dict[str, Any]:
    """
    Classify an email's intent using Claude API.

    Args:
        body: The email body text
        from_address: Sender email address
        subject: Email subject line
        client: Optional Anthropic client (creates one if not provided)

    Returns:
        Dict with keys:
        - intent: Classified intent string
        - confidence: Float 0.0-1.0
        - reasoning: Explanation string
    """
    if client is None:
        client = get_claude_client()

    prompt = CLASSIFICATION_PROMPT.format(
        from_address=from_address or "unknown", subject=subject or "(No Subject)", body=body or "(Empty)"
    )

    logger.debug(f"Classifying email: {subject[:50]}...")

    try:
        response = client.messages.create(
            model=settings.claude.model, max_tokens=500, messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines (```json and ```)
            response_text = "\n".join(lines[1:-1])

        result = json.loads(response_text)

        intent = result.get("intent", "general_inquiry")
        # Validate intent
        if intent not in VALID_INTENTS:
            logger.warning(f"Invalid intent '{intent}', defaulting to general_inquiry")
            intent = "general_inquiry"

        classification = {
            "intent": intent,
            "confidence": float(result.get("confidence", 0.5)),
            "reasoning": result.get("reasoning", ""),
        }

        logger.info(f"Classified as '{classification['intent']}' (confidence: {classification['confidence']:.2f})")

        return classification

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse classification response: {e}")
        logger.error(f"Response was: {response_text}")
        return {
            "intent": "general_inquiry",
            "confidence": 0.0,
            "reasoning": f"Parse error: {str(e)}",
        }

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return {
            "intent": "general_inquiry",
            "confidence": 0.0,
            "reasoning": f"Error: {str(e)}",
        }
