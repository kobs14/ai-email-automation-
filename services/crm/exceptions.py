"""
CRM-specific exception classes.

Provides a hierarchy of exceptions for CRM operations,
allowing callers to handle errors at the appropriate granularity.
"""


class CRMError(Exception):
    """Base exception for all CRM-related errors."""


class CRMConnectionError(CRMError):
    """Raised when the CRM service is unreachable or returns a connection error."""


class CRMCustomerNotFoundError(CRMError):
    """Raised when a customer lookup fails to find a matching record."""


class CRMRateLimitError(CRMError):
    """Raised when the CRM provider's API rate limit is exceeded."""


class CRMValidationError(CRMError):
    """Raised when data sent to the CRM fails validation."""
