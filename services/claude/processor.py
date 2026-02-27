"""
Full email processing pipeline using Claude API.

Combines classification, entity extraction, quote calculation,
and response generation into a single workflow.
"""

import logging
from typing import Any, Dict, List, Optional

from anthropic import Anthropic

from .classifier import classify_email
from .client import get_claude_client
from .extractor import entities_to_dict, extract_entities
from .responder import generate_response

logger = logging.getLogger(__name__)

# Default pricing rules
DEFAULT_PRICING_RULES = {
    "house": {"base": 120, "per_bedroom": 25, "per_bathroom": 15},
    "apartment": {"base": 80, "per_bedroom": 20, "per_bathroom": 12},
    "condo": {"base": 90, "per_bedroom": 22, "per_bathroom": 13},
    "studio": {"base": 60, "per_bathroom": 10},
    "office": {"base": 150, "per_sqft": 0.10},
}

# Service type multipliers
DEFAULT_SERVICE_MULTIPLIERS = {
    "standard": {"multiplier": 1.0, "description": "Standard cleaning"},
    "deep_clean": {"multiplier": 1.5, "description": "Deep cleaning"},
    "move_in": {"multiplier": 1.6, "description": "Move-in cleaning"},
    "move_out": {"multiplier": 1.8, "description": "Move-out cleaning"},
    "post_construction": {"multiplier": 2.0, "description": "Post-construction"},
    "one_time": {"multiplier": 1.1, "description": "One-time cleaning"},
}


def calculate_quote(
    entities: List[Dict], pricing_rules: Optional[Dict] = None, service_multipliers: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Calculate a quote based on extracted entities.

    Args:
        entities: Extracted entities from the email
        pricing_rules: Pricing configuration
        service_multipliers: Service type multipliers

    Returns:
        Quote breakdown dict or None if insufficient information
    """
    if pricing_rules is None:
        pricing_rules = DEFAULT_PRICING_RULES
    if service_multipliers is None:
        service_multipliers = DEFAULT_SERVICE_MULTIPLIERS

    # Convert entities list to dict for easier access
    entity_dict = entities_to_dict(entities)

    # Get property type
    property_type = entity_dict.get("property_type", "").lower()
    if property_type not in pricing_rules:
        # Try to match partial
        for key in pricing_rules:
            if key in property_type:
                property_type = key
                break
        else:
            logger.debug(f"Cannot calculate quote: unknown property type '{property_type}'")
            return None

    pricing = pricing_rules[property_type]
    base_price = pricing.get("base", 100)
    adjustments = []

    # Add bedroom charges
    bedrooms = entity_dict.get("bedrooms", "0")
    try:
        # Handle "3 bedrooms" or just "3"
        num_bedrooms = int(float(bedrooms.split()[0]))
        if num_bedrooms > 0 and "per_bedroom" in pricing:
            bedroom_charge = num_bedrooms * pricing["per_bedroom"]
            adjustments.append({"description": f"{num_bedrooms} bedroom(s)", "amount": bedroom_charge})
    except (ValueError, IndexError):
        pass

    # Add bathroom charges
    bathrooms = entity_dict.get("bathrooms", "0")
    try:
        # Handle "3.5" or "3"
        num_bathrooms = float(bathrooms.split()[0])
        if num_bathrooms > 0 and "per_bathroom" in pricing:
            bathroom_charge = num_bathrooms * pricing["per_bathroom"]
            adjustments.append({"description": f"{num_bathrooms} bathroom(s)", "amount": bathroom_charge})
    except (ValueError, IndexError):
        pass

    # Calculate subtotal
    subtotal = base_price + sum(a["amount"] for a in adjustments)

    # Apply service type multiplier
    service_type = entity_dict.get("service_type", "standard").lower()
    service_type = service_type.replace(" ", "_").replace("-", "_")

    multiplier_data = service_multipliers.get(service_type, {"multiplier": 1.0})
    multiplier = multiplier_data.get("multiplier", 1.0)

    if multiplier != 1.0:
        service_desc = service_type.replace("_", " ").title()
        adjustments.append(
            {"description": f"{service_desc} service ({multiplier}x)", "amount": subtotal * (multiplier - 1)}
        )

    total = subtotal * multiplier

    quote = {
        "property_type": property_type,
        "base_price": base_price,
        "adjustments": adjustments,
        "subtotal": subtotal,
        "multiplier": multiplier,
        "total": total,
    }

    logger.info(f"Calculated quote: ${total:.2f} for {property_type}")
    return quote


def process_email_with_claude(
    body: str,
    from_address: str = "",
    subject: str = "",
    generate_response_flag: bool = True,
    client: Optional[Anthropic] = None,
) -> Dict[str, Any]:
    """
    Process an email through the full Claude pipeline.

    Steps:
    1. Classify intent
    2. Extract entities
    3. Calculate quote (if quote_request)
    4. Generate response (optional)

    Args:
        body: Email body text
        from_address: Sender email address
        subject: Email subject line
        generate_response_flag: Whether to generate a response
        client: Optional Anthropic client

    Returns:
        Dict containing:
        - classification: Intent classification result
        - entities: Extracted entities list
        - quote: Quote calculation (if applicable)
        - response: Generated response text (if requested)
    """
    if client is None:
        client = get_claude_client()

    logger.info(f"Processing email: {subject[:50]}...")

    result = {}

    # Step 1: Classification
    logger.debug("Step 1: Classifying intent...")
    classification = classify_email(body=body, from_address=from_address, subject=subject, client=client)
    result["classification"] = classification
    intent = classification["intent"]

    # Step 2: Entity Extraction
    logger.debug("Step 2: Extracting entities...")
    entities = extract_entities(body=body, intent=intent, from_address=from_address, subject=subject, client=client)
    result["entities"] = entities

    # Step 3: Quote Calculation (if applicable)
    quote_data = None
    if intent == "quote_request":
        logger.debug("Step 3: Calculating quote...")
        quote_data = calculate_quote(entities)
        result["quote"] = quote_data
    else:
        logger.debug("Step 3: Skipping quote (not a quote request)")
        result["quote"] = None

    # Step 4: Response Generation (optional)
    if generate_response_flag:
        logger.debug("Step 4: Generating response...")
        response = generate_response(
            body=body,
            intent=intent,
            entities=entities,
            from_address=from_address,
            subject=subject,
            quote_data=quote_data,
            client=client,
        )
        result["response"] = response
    else:
        logger.debug("Step 4: Skipping response generation")
        result["response"] = None

    logger.info(
        f"Email processed: intent={intent}, "
        f"entities={len(entities)}, "
        f"quote={'yes' if quote_data else 'no'}, "
        f"response={'yes' if result.get('response') else 'no'}"
    )

    return result
