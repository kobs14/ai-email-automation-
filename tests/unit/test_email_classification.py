"""
Unit tests for email classification.

Tests the classify_email function from services/claude/classifier.py
Note: These tests mock the Claude API to avoid actual API calls.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Check if anthropic library is available (needed by claude module)
try:
    from services.claude.classifier import VALID_INTENTS, classify_email

    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    classify_email = None
    VALID_INTENTS = None

# Skip entire module if claude module is not available
pytestmark = pytest.mark.skipif(not CLAUDE_AVAILABLE, reason="Claude module dependencies not installed (anthropic)")


class TestClassifyEmailMocked:
    """Test classification with mocked Claude API."""

    def test_classifies_quote_request(self):
        """Test email is classified as quote_request."""
        with patch("services.claude.classifier.get_claude_client") as mock_get_client:
            # Mock Claude response
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [
                Mock(text='{"intent": "quote_request", "confidence": 0.95, "reasoning": "Customer asking for price"}')
            ]
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = classify_email(
                body="I need a quote for cleaning my house", subject="Quote request", from_address="test@example.com"
            )

            assert result["intent"] == "quote_request"
            assert result["confidence"] == 0.95
            assert "reasoning" in result

    def test_classifies_booking_request(self):
        """Test email is classified as booking_request."""
        with patch("services.claude.classifier.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [
                Mock(text='{"intent": "booking_request", "confidence": 0.90, "reasoning": "Customer wants to book"}')
            ]
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = classify_email(
                body="I want to book a cleaning for next week", subject="Booking", from_address="test@example.com"
            )

            assert result["intent"] == "booking_request"
            assert result["confidence"] == 0.90

    def test_classifies_rescheduling(self):
        """Test email is classified as rescheduling."""
        with patch("services.claude.classifier.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [
                Mock(text='{"intent": "rescheduling", "confidence": 0.85, "reasoning": "Customer needs to reschedule"}')
            ]
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = classify_email(
                body="I need to reschedule my appointment", subject="Reschedule", from_address="test@example.com"
            )

            assert result["intent"] == "rescheduling"

    def test_classifies_complaint(self):
        """Test email is classified as complaint."""
        with patch("services.claude.classifier.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [
                Mock(text='{"intent": "complaint", "confidence": 0.88, "reasoning": "Customer unhappy"}')
            ]
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = classify_email(
                body="I'm unhappy with the service", subject="Complaint", from_address="test@example.com"
            )

            assert result["intent"] == "complaint"

    def test_classifies_general_inquiry(self):
        """Test email is classified as general_inquiry."""
        with patch("services.claude.classifier.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [
                Mock(text='{"intent": "general_inquiry", "confidence": 0.75, "reasoning": "General question"}')
            ]
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = classify_email(
                body="What services do you offer?", subject="Question", from_address="test@example.com"
            )

            assert result["intent"] == "general_inquiry"

    def test_handles_json_in_code_block(self):
        """Test parsing JSON wrapped in markdown code block."""
        with patch("services.claude.classifier.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            # Response wrapped in code block
            mock_response.content = [
                Mock(text='```json\n{"intent": "quote_request", "confidence": 0.9, "reasoning": "test"}\n```')
            ]
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = classify_email(body="test", subject="test", from_address="test@example.com")

            assert result["intent"] == "quote_request"

    def test_handles_invalid_json(self):
        """Test graceful handling of invalid JSON response."""
        with patch("services.claude.classifier.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(text="not valid json")]
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = classify_email(body="test", subject="test", from_address="test@example.com")

            # Should return default general_inquiry
            assert result["intent"] == "general_inquiry"
            assert result["confidence"] == 0.0
            assert "Parse error" in result["reasoning"]

    def test_handles_invalid_intent(self):
        """Test handling of invalid intent in response."""
        with patch("services.claude.classifier.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(text='{"intent": "invalid_intent", "confidence": 0.9, "reasoning": "test"}')]
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = classify_email(body="test", subject="test", from_address="test@example.com")

            # Should default to general_inquiry for invalid intent
            assert result["intent"] == "general_inquiry"

    def test_handles_api_error(self):
        """Test graceful handling of API errors."""
        with patch("services.claude.classifier.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_get_client.return_value = mock_client

            result = classify_email(body="test", subject="test", from_address="test@example.com")

            assert result["intent"] == "general_inquiry"
            assert result["confidence"] == 0.0
            assert "Error" in result["reasoning"]


class TestValidIntents:
    """Test VALID_INTENTS constant."""

    def test_valid_intents_list(self):
        """Test that VALID_INTENTS contains expected values."""
        assert "quote_request" in VALID_INTENTS
        assert "booking_request" in VALID_INTENTS
        assert "rescheduling" in VALID_INTENTS
        assert "complaint" in VALID_INTENTS
        assert "general_inquiry" in VALID_INTENTS
        assert len(VALID_INTENTS) == 5
