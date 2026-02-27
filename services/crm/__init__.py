"""
CRM integration package.

Provides an abstract CRM interface so concrete providers (HubSpot,
Salesforce, Zoho, etc.) can be plugged in without changing business logic.

Usage:
    from services.crm import get_crm_provider

    crm = get_crm_provider()
    customer, created = crm.get_or_create_customer("alice@example.com")

The factory reads ``settings.crm`` to decide which provider to instantiate.
When CRM is disabled (the default), a ``NullCRMProvider`` is returned that
does nothing, keeping the system backward-compatible.
"""

import logging

from services.crm.base import BaseCRMProvider
from services.crm.exceptions import (
    CRMConnectionError,
    CRMCustomerNotFoundError,
    CRMError,
    CRMRateLimitError,
    CRMValidationError,
)
from services.crm.models import CRMCustomer, CRMDeal, CRMInteraction
from services.crm.null_provider import NullCRMProvider

logger = logging.getLogger(__name__)

__all__ = [
    # Factory
    "get_crm_provider",
    # Base class
    "BaseCRMProvider",
    # Default provider
    "NullCRMProvider",
    # Data models
    "CRMCustomer",
    "CRMDeal",
    "CRMInteraction",
    # Exceptions
    "CRMError",
    "CRMConnectionError",
    "CRMCustomerNotFoundError",
    "CRMRateLimitError",
    "CRMValidationError",
]


def get_crm_provider() -> BaseCRMProvider:
    """
    Factory: return the configured CRM provider instance.

    Reads ``settings.crm`` to determine which backend to use.
    Falls back to ``NullCRMProvider`` when CRM is disabled or when
    the configured provider name is unrecognised.

    Returns:
        A concrete ``BaseCRMProvider`` implementation.
    """
    from config.settings import settings

    if not settings.crm.enabled:
        logger.debug("CRM disabled — using NullCRMProvider")
        return NullCRMProvider()

    provider_name = settings.crm.provider.lower()

    if provider_name == "null":
        return NullCRMProvider()

    # Future concrete providers:
    # if provider_name == "hubspot":
    #     from services.crm.hubspot import HubSpotCRMProvider
    #     return HubSpotCRMProvider(settings.crm)
    #
    # if provider_name == "salesforce":
    #     from services.crm.salesforce import SalesforceCRMProvider
    #     return SalesforceCRMProvider(settings.crm)

    logger.warning(
        "Unknown CRM provider '%s', falling back to NullCRMProvider",
        provider_name,
    )
    return NullCRMProvider()
