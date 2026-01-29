"""
Entity extraction from emails using Claude API.

Extracts relevant information based on email intent:
- Property details (type, bedrooms, bathrooms)
- Dates and times
- Contact information
- Service preferences
"""

import json
import logging
from typing import Any, Dict, List, Optional

from anthropic import Anthropic

from config.settings import settings
from .client import get_claude_client

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an AI assistant for a cleaning service company. Your task is to extract relevant information from customer emails.

The email has been classified as: {intent}

Based on this intent, extract the following entities (only include those that are mentioned):

For quote_request:
- property_type: Type of property (house, apartment, condo, office, studio)
- bedrooms: Number of bedrooms
- bathrooms: Number of bathrooms
- square_footage: Property size in square feet
- service_type: Type of cleaning (standard, deep_clean, move_in, move_out, post_construction, one_time)
- preferred_date: When they want the service
- preferred_time: Time preference
- frequency: Recurring schedule interest (weekly, bi-weekly, monthly)
- special_requests: Any special requirements or add-ons
- address: Property address if mentioned
- contact_phone: Phone number if provided
- contact_name: Customer name if provided

For booking_request:
- property_type, bedrooms, bathrooms, service_type
- requested_date: Specific date requested
- requested_time: Specific time requested
- address: Property address
- contact_phone: Phone number
- contact_name: Customer name
- special_instructions: Any specific instructions

For rescheduling:
- original_date: The current/original appointment date
- new_preferred_date: When they want to reschedule to
- new_preferred_time: New time preference
- reason: Why they're rescheduling
- contact_name: Customer name

For complaint:
- issue_type: Type of issue (service_quality, property_damage, scheduling, billing, staff_behavior)
- service_date: When the service occurred
- specific_concerns: Detailed description of the issues
- desired_resolution: What outcome they're looking for
- contact_name: Customer name

For general_inquiry:
- topic: What the inquiry is about
- specific_question: The specific questions asked
- contact_name: Customer name

Email:
From: {from_address}
Subject: {subject}

{body}

Respond with a JSON object containing an "entities" array. Each entity should have:
- "type": The entity type (from the list above)
- "value": The extracted value
- "confidence": Your confidence (0.0 to 1.0)

Only include entities that are clearly present in the email. Respond ONLY with the JSON object."""


def extract_entities(
    body: str,
    intent: str,
    from_address: str = "",
    subject: str = "",
    client: Optional[Anthropic] = None
) -> List[Dict[str, Any]]:
    """
    Extract relevant entities from an email using Claude API.

    Args:
        body: The email body text
        intent: The classified intent
        from_address: Sender email address
        subject: Email subject line
        client: Optional Anthropic client

    Returns:
        List of dicts with keys: type, value, confidence
    """
    if client is None:
        client = get_claude_client()

    prompt = EXTRACTION_PROMPT.format(
        intent=intent,
        from_address=from_address or "unknown",
        subject=subject or "(No Subject)",
        body=body or "(Empty)"
    )

    logger.debug(f"Extracting entities for {intent} email...")

    try:
        response = client.messages.create(
            model=settings.claude.model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        result = json.loads(response_text)
        entities = result.get("entities", [])

        # Normalize the output
        normalized = [
            {
                "type": e.get("type", "unknown"),
                "value": str(e.get("value", "")),
                "confidence": float(e.get("confidence", 0.5))
            }
            for e in entities
        ]

        logger.info(f"Extracted {len(normalized)} entities")
        for e in normalized:
            logger.debug(f"  - {e['type']}: {e['value'][:50]}...")

        return normalized

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extraction response: {e}")
        logger.error(f"Response was: {response_text}")
        return []

    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        return []


def entities_to_dict(entities: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Convert entities list to a simple dict for easier access.

    Args:
        entities: List of entity dicts with type/value/confidence

    Returns:
        Dict mapping entity type to value
    """
    return {e["type"]: e["value"] for e in entities}
