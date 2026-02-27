"""
Pytest configuration and shared fixtures.

Fixtures defined here are available to all tests automatically.
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Pricing Fixtures
# =============================================================================


@pytest.fixture
def pricing_rules():
    """Standard pricing rules for testing."""
    return {
        "house": {"base": 120, "per_bedroom": 25, "per_bathroom": 15},
        "apartment": {"base": 80, "per_bedroom": 20, "per_bathroom": 12},
        "condo": {"base": 90, "per_bedroom": 22, "per_bathroom": 13},
        "studio": {"base": 60, "per_bathroom": 10},
        "office": {"base": 150, "per_sqft": 0.10},
    }


@pytest.fixture
def service_multipliers():
    """Service type multipliers for testing."""
    return {
        "standard": {"multiplier": 1.0, "description": "Standard cleaning"},
        "deep_clean": {"multiplier": 1.5, "description": "Deep cleaning"},
        "move_in": {"multiplier": 1.6, "description": "Move-in cleaning"},
        "move_out": {"multiplier": 1.8, "description": "Move-out cleaning"},
        "post_construction": {"multiplier": 2.0, "description": "Post-construction"},
    }


# =============================================================================
# Entity Fixtures
# =============================================================================


@pytest.fixture
def sample_entities_house():
    """Sample extracted entities for a house quote request."""
    return [
        {"type": "property_type", "value": "house", "confidence": 0.95},
        {"type": "bedrooms", "value": "3", "confidence": 0.90},
        {"type": "bathrooms", "value": "2", "confidence": 0.90},
        {"type": "service_type", "value": "deep_clean", "confidence": 0.85},
        {"type": "contact_phone", "value": "(555) 123-4567", "confidence": 0.95},
    ]


@pytest.fixture
def sample_entities_apartment():
    """Sample extracted entities for an apartment quote request."""
    return [
        {"type": "property_type", "value": "apartment", "confidence": 0.95},
        {"type": "bedrooms", "value": "2", "confidence": 0.90},
        {"type": "bathrooms", "value": "1", "confidence": 0.90},
        {"type": "service_type", "value": "move_in", "confidence": 0.85},
    ]


@pytest.fixture
def sample_entities_minimal():
    """Minimal entities - just property type."""
    return [
        {"type": "property_type", "value": "house", "confidence": 0.80},
    ]


@pytest.fixture
def sample_entities_empty():
    """Empty entities list."""
    return []


@pytest.fixture
def sample_entities_invalid():
    """Entities with invalid/unknown property type."""
    return [
        {"type": "property_type", "value": "spaceship", "confidence": 0.50},
        {"type": "bedrooms", "value": "3", "confidence": 0.90},
    ]


# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables for testing."""
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "test_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")
    monkeypatch.setenv("POSTGRES_DB", "test_db")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


@pytest.fixture
def mock_env_missing_password(monkeypatch):
    """Environment with missing password."""
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_USER", "test_user")
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)


@pytest.fixture
def mock_env_missing_api_key(monkeypatch):
    """Environment with missing API key."""
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
