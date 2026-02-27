"""
Unit tests for quote calculation logic.

Tests the calculate_quote function from services/claude/processor.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Check if anthropic library is available (needed by claude module)
try:
    from services.claude.processor import calculate_quote

    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    calculate_quote = None

# Skip entire module if claude module is not available
pytestmark = pytest.mark.skipif(not CLAUDE_AVAILABLE, reason="Claude module dependencies not installed (anthropic)")


class TestCalculateQuoteBasic:
    """Test basic quote calculation scenarios."""

    def test_house_standard_cleaning(self, pricing_rules, service_multipliers):
        """Test standard cleaning for a house."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "3", "confidence": 0.90},
            {"type": "bathrooms", "value": "2", "confidence": 0.90},
            {"type": "service_type", "value": "standard", "confidence": 0.85},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        assert result["property_type"] == "house"
        assert result["base_price"] == 120
        assert result["multiplier"] == 1.0
        # Base: 120 + Bedrooms: 3*25=75 + Bathrooms: 2*15=30 = 225
        assert result["total"] == 225.0

    def test_house_deep_clean(self, pricing_rules, service_multipliers):
        """Test deep cleaning for a house (1.5x multiplier)."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "3", "confidence": 0.90},
            {"type": "bathrooms", "value": "2", "confidence": 0.90},
            {"type": "service_type", "value": "deep_clean", "confidence": 0.85},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        assert result["multiplier"] == 1.5
        # (120 + 75 + 30) * 1.5 = 337.5
        assert result["total"] == 337.5

    def test_apartment_move_in(self, pricing_rules, service_multipliers):
        """Test move-in cleaning for an apartment (1.6x multiplier)."""
        entities = [
            {"type": "property_type", "value": "apartment", "confidence": 0.95},
            {"type": "bedrooms", "value": "2", "confidence": 0.90},
            {"type": "bathrooms", "value": "1", "confidence": 0.90},
            {"type": "service_type", "value": "move_in", "confidence": 0.85},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        assert result["property_type"] == "apartment"
        assert result["base_price"] == 80
        assert result["multiplier"] == 1.6
        # (80 + 2*20 + 1*12) * 1.6 = 132 * 1.6 = 211.2
        assert result["total"] == pytest.approx(211.2)

    def test_condo_move_out(self, pricing_rules, service_multipliers):
        """Test move-out cleaning for a condo (1.8x multiplier)."""
        entities = [
            {"type": "property_type", "value": "condo", "confidence": 0.95},
            {"type": "bedrooms", "value": "1", "confidence": 0.90},
            {"type": "bathrooms", "value": "1", "confidence": 0.90},
            {"type": "service_type", "value": "move_out", "confidence": 0.85},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        assert result["property_type"] == "condo"
        assert result["multiplier"] == 1.8
        # (90 + 22 + 13) * 1.8 = 125 * 1.8 = 225
        assert result["total"] == 225.0


class TestCalculateQuoteEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_bedrooms(self, pricing_rules, service_multipliers):
        """Test with zero bedrooms (studio-like)."""
        entities = [
            {"type": "property_type", "value": "apartment", "confidence": 0.95},
            {"type": "bedrooms", "value": "0", "confidence": 0.90},
            {"type": "bathrooms", "value": "1", "confidence": 0.90},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        # Base: 80 + Bathrooms: 12 = 92
        assert result["total"] == 92.0

    def test_half_bathroom(self, pricing_rules, service_multipliers):
        """Test with half bathroom (e.g., 2.5 bathrooms)."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "3", "confidence": 0.90},
            {"type": "bathrooms", "value": "2.5", "confidence": 0.90},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        # Base: 120 + Bedrooms: 75 + Bathrooms: 2.5*15=37.5 = 232.5
        assert result["total"] == 232.5

    def test_large_house(self, pricing_rules, service_multipliers):
        """Test with a large house (many bedrooms/bathrooms)."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "6", "confidence": 0.90},
            {"type": "bathrooms", "value": "4", "confidence": 0.90},
            {"type": "service_type", "value": "deep_clean", "confidence": 0.85},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        # (120 + 6*25 + 4*15) * 1.5 = (120 + 150 + 60) * 1.5 = 330 * 1.5 = 495
        assert result["total"] == 495.0

    def test_missing_service_type_defaults_to_standard(self, pricing_rules, service_multipliers):
        """Test that missing service type defaults to standard (1.0x)."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "2", "confidence": 0.90},
            {"type": "bathrooms", "value": "1", "confidence": 0.90},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        assert result["multiplier"] == 1.0
        # Base: 120 + Bedrooms: 50 + Bathrooms: 15 = 185
        assert result["total"] == 185.0

    def test_missing_bedrooms(self, pricing_rules, service_multipliers):
        """Test with missing bedrooms (only base + bathrooms)."""
        entities = [
            {"type": "property_type", "value": "apartment", "confidence": 0.95},
            {"type": "bathrooms", "value": "1", "confidence": 0.90},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        # Base: 80 + Bathrooms: 12 = 92
        assert result["total"] == 92.0

    def test_missing_bathrooms(self, pricing_rules, service_multipliers):
        """Test with missing bathrooms (only base + bedrooms)."""
        entities = [
            {"type": "property_type", "value": "apartment", "confidence": 0.95},
            {"type": "bedrooms", "value": "2", "confidence": 0.90},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        # Base: 80 + Bedrooms: 40 = 120
        assert result["total"] == 120.0

    def test_only_property_type(self, pricing_rules, service_multipliers):
        """Test with only property type (base price only)."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.80},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        assert result["total"] == 120.0  # Just base price


class TestCalculateQuoteInvalidInputs:
    """Test handling of invalid inputs."""

    def test_missing_property_type_returns_none(self, pricing_rules, service_multipliers):
        """Test that missing property type returns None."""
        entities = [
            {"type": "bedrooms", "value": "3", "confidence": 0.90},
            {"type": "bathrooms", "value": "2", "confidence": 0.90},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is None

    def test_unknown_property_type_returns_none(self, pricing_rules, service_multipliers):
        """Test that unknown property type returns None."""
        entities = [
            {"type": "property_type", "value": "spaceship", "confidence": 0.50},
            {"type": "bedrooms", "value": "3", "confidence": 0.90},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is None

    def test_empty_entities_returns_none(self, pricing_rules, service_multipliers):
        """Test that empty entities list returns None."""
        entities = []

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is None

    def test_invalid_bedroom_value_ignored(self, pricing_rules, service_multipliers):
        """Test that invalid bedroom value is gracefully ignored."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "many", "confidence": 0.90},
            {"type": "bathrooms", "value": "2", "confidence": 0.90},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        # Base: 120 + Bathrooms: 30 = 150 (bedrooms ignored)
        assert result["total"] == 150.0

    def test_invalid_bathroom_value_ignored(self, pricing_rules, service_multipliers):
        """Test that invalid bathroom value is gracefully ignored."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "3", "confidence": 0.90},
            {"type": "bathrooms", "value": "several", "confidence": 0.90},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        # Base: 120 + Bedrooms: 75 = 195 (bathrooms ignored)
        assert result["total"] == 195.0


class TestCalculateQuoteServiceTypes:
    """Test all service type multipliers."""

    @pytest.mark.parametrize(
        "service_type,expected_multiplier",
        [
            ("standard", 1.0),
            ("deep_clean", 1.5),
            ("move_in", 1.6),
            ("move_out", 1.8),
            ("post_construction", 2.0),
        ],
    )
    def test_service_multipliers(self, service_type, expected_multiplier, pricing_rules, service_multipliers):
        """Test each service type applies correct multiplier."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "2", "confidence": 0.90},
            {"type": "bathrooms", "value": "1", "confidence": 0.90},
            {"type": "service_type", "value": service_type, "confidence": 0.85},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        assert result["multiplier"] == expected_multiplier
        # Base: 120 + Bedrooms: 50 + Bathrooms: 15 = 185
        expected_total = 185.0 * expected_multiplier
        assert result["total"] == expected_total

    def test_unknown_service_type_defaults_to_standard(self, pricing_rules, service_multipliers):
        """Test that unknown service type defaults to 1.0x multiplier."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "2", "confidence": 0.90},
            {"type": "service_type", "value": "super_deluxe_premium", "confidence": 0.85},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        assert result["multiplier"] == 1.0


class TestCalculateQuoteAdjustments:
    """Test that adjustments are calculated and returned correctly."""

    def test_adjustments_list_populated(self, pricing_rules, service_multipliers):
        """Test that adjustments list contains bedroom and bathroom charges."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "3", "confidence": 0.90},
            {"type": "bathrooms", "value": "2", "confidence": 0.90},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        assert "adjustments" in result
        assert len(result["adjustments"]) >= 2

        # Check bedroom adjustment exists
        bedroom_adj = next((a for a in result["adjustments"] if "bedroom" in a["description"].lower()), None)
        assert bedroom_adj is not None
        assert bedroom_adj["amount"] == 75  # 3 * 25

        # Check bathroom adjustment exists
        bathroom_adj = next((a for a in result["adjustments"] if "bathroom" in a["description"].lower()), None)
        assert bathroom_adj is not None
        assert bathroom_adj["amount"] == 30  # 2 * 15

    def test_subtotal_calculated_correctly(self, pricing_rules, service_multipliers):
        """Test that subtotal equals base + adjustments."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "3", "confidence": 0.90},
            {"type": "bathrooms", "value": "2", "confidence": 0.90},
            {"type": "service_type", "value": "standard", "confidence": 0.85},
        ]

        result = calculate_quote(entities, pricing_rules, service_multipliers)

        assert result is not None
        expected_subtotal = result["base_price"] + sum(
            a["amount"] for a in result["adjustments"] if "service" not in a["description"].lower()
        )
        assert result["subtotal"] == expected_subtotal


class TestCalculateQuoteDefaultPricing:
    """Test with default pricing (no pricing_rules provided)."""

    def test_default_pricing_rules_used(self):
        """Test that default pricing rules are used when none provided."""
        entities = [
            {"type": "property_type", "value": "house", "confidence": 0.95},
            {"type": "bedrooms", "value": "3", "confidence": 0.90},
            {"type": "bathrooms", "value": "2", "confidence": 0.90},
        ]

        # Call without pricing_rules or service_multipliers
        result = calculate_quote(entities)

        assert result is not None
        assert result["property_type"] == "house"
        # Should use default pricing from the function
        assert result["total"] > 0
