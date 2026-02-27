"""
Tests for the CRM abstraction layer.

Covers:
    - NullCRMProvider returns expected defaults for every method.
    - get_crm_provider() factory behaviour under various configurations.
    - CRM data models can be instantiated with required and optional fields.
    - CRM exception hierarchy.
"""

import sys
from datetime import datetime
from unittest.mock import patch

import pytest

from config.settings import CRMSettings
from services.crm import (
    BaseCRMProvider,
    CRMConnectionError,
    CRMCustomer,
    CRMCustomerNotFoundError,
    CRMDeal,
    CRMError,
    CRMInteraction,
    CRMRateLimitError,
    CRMValidationError,
    NullCRMProvider,
    get_crm_provider,
)

# The config package re-exports ``settings`` as an attribute, shadowing the
# submodule name.  Use sys.modules to get the real module so patch.object works.
_settings_module = sys.modules["config.settings"]


# =========================================================================
# NullCRMProvider — every method returns safe defaults
# =========================================================================


class TestNullCRMProviderCustomerOps:
    """Customer-related no-op behaviour."""

    def setup_method(self) -> None:
        self.provider = NullCRMProvider()

    def test_find_customer_by_email_returns_none(self) -> None:
        assert self.provider.find_customer_by_email("test@example.com") is None

    def test_find_customer_by_phone_returns_none(self) -> None:
        assert self.provider.find_customer_by_phone("555-1234") is None

    def test_create_customer_returns_input(self) -> None:
        customer = CRMCustomer(email="new@example.com", name="Alice")
        result = self.provider.create_customer(customer)
        assert result is customer

    def test_update_customer_returns_stub(self) -> None:
        result = self.provider.update_customer("crm-123", {"name": "Bob"})
        assert isinstance(result, CRMCustomer)
        assert result.crm_id == "crm-123"

    def test_get_or_create_customer_returns_stub_and_false(self) -> None:
        customer, created = self.provider.get_or_create_customer("test@example.com", defaults={"name": "Test"})
        assert isinstance(customer, CRMCustomer)
        assert customer.email == "test@example.com"
        assert created is False


class TestNullCRMProviderInteractionOps:
    """Interaction-related no-op behaviour."""

    def setup_method(self) -> None:
        self.provider = NullCRMProvider()

    def test_log_interaction_returns_false(self) -> None:
        interaction = CRMInteraction(
            interaction_type="email_received",
            channel="email",
            occurred_at=datetime.now(),
        )
        assert self.provider.log_interaction("cust-1", interaction) is False

    def test_get_customer_interactions_returns_empty_list(self) -> None:
        result = self.provider.get_customer_interactions("cust-1")
        assert result == []


class TestNullCRMProviderDealOps:
    """Deal-related no-op behaviour."""

    def setup_method(self) -> None:
        self.provider = NullCRMProvider()

    def test_create_deal_returns_input(self) -> None:
        deal = CRMDeal(customer_id="cust-1", title="Deep clean quote", stage="new")
        result = self.provider.create_deal(deal)
        assert result is deal

    def test_update_deal_stage_returns_stub(self) -> None:
        result = self.provider.update_deal_stage("deal-1", "booked")
        assert isinstance(result, CRMDeal)
        assert result.stage == "booked"
        assert result.crm_id == "deal-1"

    def test_get_deals_for_customer_returns_empty_list(self) -> None:
        assert self.provider.get_deals_for_customer("cust-1") == []


class TestNullCRMProviderHealth:
    """Health / connectivity no-op behaviour."""

    def test_is_available_returns_false(self) -> None:
        assert NullCRMProvider().is_available() is False


class TestNullCRMProviderIsSubclass:
    """NullCRMProvider satisfies the abstract interface."""

    def test_is_subclass_of_base(self) -> None:
        assert issubclass(NullCRMProvider, BaseCRMProvider)

    def test_instance_check(self) -> None:
        assert isinstance(NullCRMProvider(), BaseCRMProvider)


# =========================================================================
# get_crm_provider() factory
# =========================================================================


class TestGetCRMProviderFactory:
    """Factory returns the correct provider based on settings."""

    def test_returns_null_when_crm_disabled(self) -> None:
        mock = _make_mock_settings(enabled=False)
        with patch.object(_settings_module, "settings", mock):
            provider = get_crm_provider()
        assert isinstance(provider, NullCRMProvider)

    def test_returns_null_for_null_provider_name(self) -> None:
        mock = _make_mock_settings(enabled=True, provider="null")
        with patch.object(_settings_module, "settings", mock):
            provider = get_crm_provider()
        assert isinstance(provider, NullCRMProvider)

    def test_returns_null_for_unknown_provider_name(self) -> None:
        mock = _make_mock_settings(enabled=True, provider="unknown_crm")
        with patch.object(_settings_module, "settings", mock):
            provider = get_crm_provider()
        assert isinstance(provider, NullCRMProvider)

    def test_returns_null_for_unknown_provider_case_insensitive(self) -> None:
        mock = _make_mock_settings(enabled=True, provider="HubSpot")
        with patch.object(_settings_module, "settings", mock):
            provider = get_crm_provider()
        assert isinstance(provider, NullCRMProvider)


# =========================================================================
# CRM data models
# =========================================================================


class TestCRMCustomerModel:
    """CRMCustomer dataclass instantiation."""

    def test_minimal_creation(self) -> None:
        customer = CRMCustomer(email="a@b.com")
        assert customer.email == "a@b.com"
        assert customer.crm_id is None
        assert customer.tags == []
        assert customer.custom_fields == {}

    def test_full_creation(self) -> None:
        now = datetime.now()
        customer = CRMCustomer(
            email="full@example.com",
            crm_id="crm-99",
            name="Full User",
            phone="555-9999",
            address="123 Main St",
            segment="residential",
            lifecycle_stage="customer",
            tags=["vip", "recurring"],
            custom_fields={"source": "web"},
            created_at=now,
            updated_at=now,
        )
        assert customer.crm_id == "crm-99"
        assert customer.segment == "residential"
        assert "vip" in customer.tags
        assert customer.custom_fields["source"] == "web"

    def test_mutable_defaults_are_independent(self) -> None:
        c1 = CRMCustomer(email="a@b.com")
        c2 = CRMCustomer(email="x@y.com")
        c1.tags.append("test")
        assert c2.tags == []


class TestCRMInteractionModel:
    """CRMInteraction dataclass instantiation."""

    def test_minimal_creation(self) -> None:
        now = datetime.now()
        interaction = CRMInteraction(
            interaction_type="email_received",
            channel="email",
            occurred_at=now,
        )
        assert interaction.interaction_type == "email_received"
        assert interaction.subject is None
        assert interaction.metadata == {}

    def test_full_creation(self) -> None:
        now = datetime.now()
        interaction = CRMInteraction(
            interaction_type="quote_sent",
            channel="email",
            occurred_at=now,
            subject="Quote #123",
            summary="Sent deep-clean quote",
            metadata={"quote_id": 123, "amount": 250.0},
        )
        assert interaction.summary == "Sent deep-clean quote"
        assert interaction.metadata["amount"] == 250.0


class TestCRMDealModel:
    """CRMDeal dataclass instantiation."""

    def test_minimal_creation(self) -> None:
        deal = CRMDeal(customer_id="c1", title="Test Deal", stage="new")
        assert deal.currency == "USD"
        assert deal.value is None
        assert deal.metadata == {}

    def test_full_creation(self) -> None:
        now = datetime.now()
        deal = CRMDeal(
            customer_id="c1",
            title="Deep Clean — 3BR House",
            stage="quoted",
            crm_id="deal-5",
            value=350.00,
            currency="USD",
            service_type="deep_clean",
            metadata={"quote_id": 42},
            created_at=now,
            updated_at=now,
        )
        assert deal.value == 350.00
        assert deal.service_type == "deep_clean"


# =========================================================================
# CRM exception hierarchy
# =========================================================================


class TestCRMExceptions:
    """Exception classes form the expected hierarchy."""

    def test_base_exception(self) -> None:
        assert issubclass(CRMError, Exception)

    @pytest.mark.parametrize(
        "exc_class",
        [CRMConnectionError, CRMCustomerNotFoundError, CRMRateLimitError, CRMValidationError],
    )
    def test_subclass_of_crm_error(self, exc_class: type) -> None:
        assert issubclass(exc_class, CRMError)

    def test_can_catch_specific_with_base(self) -> None:
        with pytest.raises(CRMError):
            raise CRMConnectionError("unreachable")

    def test_specific_exception_message(self) -> None:
        err = CRMRateLimitError("rate limit hit")
        assert str(err) == "rate limit hit"


# =========================================================================
# CRMSettings dataclass
# =========================================================================


class TestCRMSettings:
    """CRMSettings configuration behaviour."""

    def test_defaults(self) -> None:
        s = CRMSettings()
        assert s.enabled is False
        assert s.provider == "null"
        assert s.api_key == ""
        assert s.log_interactions is True

    def test_is_configured_false_when_disabled(self) -> None:
        s = CRMSettings()
        assert s.is_configured() is False

    def test_is_configured_false_when_null_provider(self) -> None:
        s = CRMSettings()
        s.enabled = True
        s.provider = "null"
        assert s.is_configured() is False

    def test_is_configured_true_when_real_provider(self) -> None:
        s = CRMSettings()
        s.enabled = True
        s.provider = "hubspot"
        assert s.is_configured() is True


# =========================================================================
# Helpers
# =========================================================================


class _FakeSettings:
    """Lightweight stand-in for the global ``settings`` object."""

    def __init__(self, crm: CRMSettings) -> None:
        self.crm = crm


def _make_mock_settings(
    enabled: bool = False,
    provider: str = "null",
    api_key: str = "",
) -> _FakeSettings:
    crm = CRMSettings()
    crm.enabled = enabled
    crm.provider = provider
    crm.api_key = api_key
    return _FakeSettings(crm=crm)
