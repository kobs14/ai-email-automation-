"""Validation functions for response management requests."""

from typing import Dict, List, Optional, Tuple


def validate_response_content(data: Optional[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate response content update.

    Args:
        data: Request JSON body

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not data:
        return False, ["Request body is required"]

    content = data.get("content", "")
    if not content or not content.strip():
        errors.append("Response content is required")
    elif len(content) > 50000:
        errors.append("Response content must be 50,000 characters or fewer")

    return len(errors) == 0, errors
