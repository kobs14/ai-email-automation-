"""
Email response generation using Claude API.

Generates professional responses based on:
- Email intent
- Extracted entities
- Quote data (if applicable)
- Business branding
"""

import logging
from typing import Dict, List, Optional

from anthropic import Anthropic

from config.settings import settings

from .client import get_claude_client

logger = logging.getLogger(__name__)

# Default business info
DEFAULT_BUSINESS_INFO = {
    "name": "EcoClean Services",
    "email": "info@ecoclean.com",
    "phone": "(555) 123-4567",
}

# Default brand voice
DEFAULT_BRAND_VOICE = {
    "tone": "friendly, professional, helpful",
    "signature": "Best regards,\nThe EcoClean Team\n\n(555) 123-4567\ninfo@ecoclean.com",
}

RESPONSE_PROMPT = """You are a professional customer service representative for {business_name}, a cleaning service company.

Generate a response to the following customer email. The email has been classified as: {intent}

Extracted information:
{entities_formatted}

{quote_section}

Guidelines for your response:
{brand_guidelines}

Email being responded to:
From: {from_address}
Subject: {subject}

{body}

Write a professional, friendly response that:
1. Acknowledges their request/concern
2. Addresses their specific needs based on the extracted information
3. {intent_specific_instruction}
4. Includes a clear call to action or next steps
5. Ends with the signature provided

Keep the response concise (under 250 words) unless more detail is needed.

Write ONLY the email response text, no JSON or additional formatting."""


def _format_entities_for_prompt(entities: List[Dict]) -> str:
    """Format entities into a readable string for the prompt."""
    if not entities:
        return "No specific details extracted."

    lines = []
    for e in entities:
        lines.append(f"- {e['type']}: {e['value']}")
    return "\n".join(lines)


def _get_intent_instruction(intent: str) -> str:
    """Get intent-specific instructions for response generation."""
    instructions = {
        "quote_request": "Provides a clear pricing breakdown if quote data is available, or explains what information is needed to provide a quote",
        "booking_request": "Confirms availability and provides booking confirmation or asks for any missing details needed to complete the booking",
        "rescheduling": "Confirms the rescheduling request and provides alternative dates if the requested date isn't available",
        "complaint": "Expresses genuine empathy, takes responsibility appropriately, and offers a concrete resolution",
        "general_inquiry": "Answers their questions thoroughly and offers additional helpful information",
    }
    return instructions.get(intent, "Addresses their needs appropriately")


def _format_quote_section(quote_data: Optional[Dict], intent: str) -> str:
    """Format quote data for the prompt if available."""
    if not quote_data or intent != "quote_request":
        return ""

    lines = ["Calculated Quote Information:"]
    if "base_price" in quote_data:
        lines.append(f"- Base price: ${quote_data['base_price']:.2f}")
    if "adjustments" in quote_data:
        for adj in quote_data["adjustments"]:
            lines.append(f"- {adj['description']}: ${adj['amount']:.2f}")
    if "total" in quote_data:
        lines.append(f"- TOTAL: ${quote_data['total']:.2f}")

    return "\n".join(lines)


def generate_response(
    body: str,
    intent: str,
    entities: List[Dict],
    from_address: str = "",
    subject: str = "",
    quote_data: Optional[Dict] = None,
    business_info: Optional[Dict] = None,
    brand_voice: Optional[Dict] = None,
    client: Optional[Anthropic] = None,
) -> str:
    """
    Generate a professional email response using Claude API.

    Args:
        body: The original email body
        intent: Classified intent
        entities: Extracted entities
        from_address: Sender email
        subject: Email subject
        quote_data: Optional calculated quote information
        business_info: Business details (name, contact info)
        brand_voice: Brand guidelines for tone/style
        client: Optional Anthropic client

    Returns:
        Generated response text
    """
    if client is None:
        client = get_claude_client()

    # Use defaults if not provided
    if business_info is None:
        business_info = DEFAULT_BUSINESS_INFO
    if brand_voice is None:
        brand_voice = DEFAULT_BRAND_VOICE

    # Format brand guidelines
    tone = brand_voice.get("tone", "professional and friendly")
    signature = brand_voice.get("signature", "Best regards,\nThe Team")
    brand_guidelines = f"- Tone: {tone}\n- Signature to use:\n{signature}"

    prompt = RESPONSE_PROMPT.format(
        business_name=business_info.get("name", "EcoClean Services"),
        intent=intent,
        entities_formatted=_format_entities_for_prompt(entities),
        quote_section=_format_quote_section(quote_data, intent),
        brand_guidelines=brand_guidelines,
        from_address=from_address or "unknown",
        subject=subject or "(No Subject)",
        body=body or "(Empty)",
        intent_specific_instruction=_get_intent_instruction(intent),
    )

    logger.debug(f"Generating response for {intent} email...")

    try:
        response = client.messages.create(
            model=settings.claude.model,
            max_tokens=settings.claude.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text.strip()
        logger.info(f"Generated response ({len(response_text)} chars)")

        return response_text

    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return ""
