"""Validation functions for authentication requests."""

from typing import Dict, List, Optional, Tuple


def validate_login(data: Optional[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate login request body.

    Args:
        data: Request JSON body

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not data:
        return False, ["Request body is required"]

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username:
        errors.append("Username is required")
    elif len(username) > 100:
        errors.append("Username must be 100 characters or fewer")

    if not password:
        errors.append("Password is required")

    return len(errors) == 0, errors
