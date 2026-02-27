"""Validation functions for configuration requests."""

import json
from typing import Dict, List, Optional, Tuple


def validate_config_update(data: Optional[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate config value update.

    Args:
        data: Request JSON body

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not data:
        return False, ["Request body is required"]

    if "value" not in data:
        errors.append("Config value is required")
    else:
        value = data["value"]
        if not isinstance(value, (dict, list, str, int, float, bool)):
            errors.append("Config value must be a valid JSON type")

        try:
            json.dumps(value)
        except (TypeError, ValueError):
            errors.append("Config value must be JSON-serializable")

    return len(errors) == 0, errors
