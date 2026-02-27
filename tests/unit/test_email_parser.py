"""
Unit tests for Gmail email parser.

Tests the EmailParser class from services/gmail/parser.py
"""

import base64
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Check if google libraries are available (needed by gmail module)
try:
    from services.gmail.parser import EmailParser, ParsedEmail

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    EmailParser = None
    ParsedEmail = None

# Skip entire module if gmail module is not available
pytestmark = pytest.mark.skipif(not GMAIL_AVAILABLE, reason="Gmail module dependencies not installed (google-auth)")


class TestEmailParserBasic:
    """Test basic email parsing functionality."""

    @pytest.fixture
    def parser(self):
        return EmailParser()

    @pytest.fixture
    def simple_email(self):
        """Simple plain text email from Gmail API format."""
        return {
            "id": "abc123",
            "threadId": "thread456",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "John Smith <john@example.com>"},
                    {"name": "To", "value": "business@company.com"},
                    {"name": "Subject", "value": "Cleaning quote request"},
                    {"name": "Date", "value": "Mon, 20 Jan 2025 10:30:00 -0500"},
                    {"name": "Message-ID", "value": "<unique-id-123@mail.example.com>"},
                ],
                "body": {
                    "data": base64.urlsafe_b64encode(b"Hi, I need a quote for cleaning my house.").decode("utf-8")
                },
            },
        }

    def test_parse_returns_parsed_email(self, parser, simple_email):
        """Test that parse returns a ParsedEmail object."""
        result = parser.parse(simple_email)
        assert isinstance(result, ParsedEmail)

    def test_parse_extracts_gmail_id(self, parser, simple_email):
        """Test Gmail ID extraction."""
        result = parser.parse(simple_email)
        assert result.gmail_id == "abc123"

    def test_parse_extracts_thread_id(self, parser, simple_email):
        """Test thread ID extraction."""
        result = parser.parse(simple_email)
        assert result.thread_id == "thread456"

    def test_parse_extracts_labels(self, parser, simple_email):
        """Test label extraction."""
        result = parser.parse(simple_email)
        assert "INBOX" in result.labels
        assert "UNREAD" in result.labels

    def test_parse_extracts_subject(self, parser, simple_email):
        """Test subject extraction."""
        result = parser.parse(simple_email)
        assert result.subject == "Cleaning quote request"

    def test_parse_extracts_body(self, parser, simple_email):
        """Test body extraction and decoding."""
        result = parser.parse(simple_email)
        assert result.body == "Hi, I need a quote for cleaning my house."

    def test_parse_extracts_message_id(self, parser, simple_email):
        """Test Message-ID extraction."""
        result = parser.parse(simple_email)
        assert result.message_id == "<unique-id-123@mail.example.com>"

    def test_parse_stores_raw_headers(self, parser, simple_email):
        """Test that raw headers are preserved."""
        result = parser.parse(simple_email)
        assert "From" in result.raw_headers
        assert "Subject" in result.raw_headers
        assert result.raw_headers["gmail_id"] == "abc123"


class TestEmailAddressParsing:
    """Test email address extraction from From header."""

    @pytest.fixture
    def parser(self):
        return EmailParser()

    @pytest.mark.parametrize(
        "from_header,expected",
        [
            # Standard format: Name <email>
            ("John Smith <john@example.com>", "john@example.com"),
            # Email only
            ("john@example.com", "john@example.com"),
            # Angle brackets only
            ("<john@example.com>", "john@example.com"),
            # Quoted name
            ('"John Smith" <john@example.com>', "john@example.com"),
            # Name with special chars
            ("John O'Brien <john@example.com>", "john@example.com"),
            # Uppercase email (should lowercase)
            ("John Smith <JOHN@EXAMPLE.COM>", "john@example.com"),
            # Multiple spaces
            ("John  Smith  <john@example.com>", "john@example.com"),
        ],
    )
    def test_parse_email_address_formats(self, parser, from_header, expected):
        """Test various email address formats."""
        result = parser._parse_email_address(from_header)
        assert result == expected

    def test_parse_empty_from_header(self, parser):
        """Test empty From header."""
        result = parser._parse_email_address("")
        assert result == ""

    def test_parse_none_from_header(self, parser):
        """Test None From header."""
        result = parser._parse_email_address(None)
        assert result == ""


class TestDateParsing:
    """Test email date parsing."""

    @pytest.fixture
    def parser(self):
        return EmailParser()

    def test_parse_rfc2822_date(self, parser):
        """Test standard RFC 2822 date format."""
        date_str = "Mon, 20 Jan 2025 10:30:00 -0500"
        result = parser._parse_date(date_str)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 20

    def test_parse_date_with_timezone(self, parser):
        """Test date with timezone."""
        date_str = "Tue, 21 Jan 2025 15:45:30 +0000"
        result = parser._parse_date(date_str)
        assert result.hour == 15
        assert result.minute == 45

    def test_parse_empty_date_returns_now(self, parser):
        """Test empty date returns current time."""
        result = parser._parse_date("")
        assert isinstance(result, datetime)
        # Should be close to now
        assert (datetime.now() - result.replace(tzinfo=None)).seconds < 5

    def test_parse_invalid_date_returns_now(self, parser):
        """Test invalid date returns current time."""
        result = parser._parse_date("not a date")
        assert isinstance(result, datetime)


class TestBodyDecoding:
    """Test email body decoding."""

    @pytest.fixture
    def parser(self):
        return EmailParser()

    def test_decode_base64url_body(self, parser):
        """Test base64url decoding."""
        text = "Hello, this is a test email!"
        encoded = base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")
        body = {"data": encoded}

        result = parser._decode_body(body)
        assert result == text

    def test_decode_empty_body(self, parser):
        """Test empty body."""
        result = parser._decode_body({})
        assert result == ""

    def test_decode_body_with_unicode(self, parser):
        """Test body with unicode characters."""
        text = "Hello! Special chars: \u00e9\u00e0\u00fc"
        encoded = base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")
        body = {"data": encoded}

        result = parser._decode_body(body)
        assert result == text

    def test_decode_body_with_newlines(self, parser):
        """Test body with newlines."""
        text = "Line 1\nLine 2\nLine 3"
        encoded = base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")
        body = {"data": encoded}

        result = parser._decode_body(body)
        assert result == text


class TestHtmlToText:
    """Test HTML to plain text conversion."""

    @pytest.fixture
    def parser(self):
        return EmailParser()

    def test_strip_html_tags(self, parser):
        """Test basic HTML tag stripping."""
        html = "<p>Hello <b>World</b></p>"
        result = parser._html_to_text(html)
        assert "Hello" in result
        assert "World" in result
        assert "<p>" not in result
        assert "<b>" not in result

    def test_convert_br_to_newline(self, parser):
        """Test <br> conversion to newline."""
        html = "Line 1<br>Line 2<br/>Line 3"
        result = parser._html_to_text(html)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_convert_p_to_newline(self, parser):
        """Test </p> adds newline."""
        html = "<p>Paragraph 1</p><p>Paragraph 2</p>"
        result = parser._html_to_text(html)
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result

    def test_strip_script_tags(self, parser):
        """Test script tag removal."""
        html = '<p>Hello</p><script>alert("bad")</script><p>World</p>'
        result = parser._html_to_text(html)
        assert "Hello" in result
        assert "World" in result
        assert "alert" not in result
        assert "script" not in result

    def test_strip_style_tags(self, parser):
        """Test style tag removal."""
        html = "<style>.red { color: red; }</style><p>Hello</p>"
        result = parser._html_to_text(html)
        assert "Hello" in result
        assert "color" not in result

    def test_decode_html_entities(self, parser):
        """Test HTML entity decoding."""
        html = "<p>Price: $100 &amp; tax &lt;included&gt;</p>"
        result = parser._html_to_text(html)
        assert "&" in result
        assert "<included>" in result

    def test_convert_list_items(self, parser):
        """Test <li> conversion to bullet points."""
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = parser._html_to_text(html)
        assert "Item 1" in result
        assert "Item 2" in result

    def test_empty_html(self, parser):
        """Test empty HTML."""
        result = parser._html_to_text("")
        assert result == ""

    def test_none_html(self, parser):
        """Test None HTML."""
        result = parser._html_to_text(None)
        assert result == ""


class TestMultipartParsing:
    """Test multipart email parsing."""

    @pytest.fixture
    def parser(self):
        return EmailParser()

    @pytest.fixture
    def multipart_email(self):
        """Multipart email with text/plain and text/html parts."""
        plain_text = "This is the plain text version."
        html_text = "<html><body><p>This is the <b>HTML</b> version.</p></body></html>"

        return {
            "id": "multi123",
            "threadId": "thread789",
            "labelIds": ["INBOX"],
            "payload": {
                "mimeType": "multipart/alternative",
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Multipart test"},
                    {"name": "Date", "value": "Mon, 20 Jan 2025 10:30:00 -0500"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": base64.urlsafe_b64encode(plain_text.encode("utf-8")).decode("utf-8")},
                    },
                    {
                        "mimeType": "text/html",
                        "body": {"data": base64.urlsafe_b64encode(html_text.encode("utf-8")).decode("utf-8")},
                    },
                ],
            },
        }

    def test_multipart_prefers_plain_text(self, parser, multipart_email):
        """Test that plain text is preferred over HTML."""
        result = parser.parse(multipart_email)
        assert result.body == "This is the plain text version."

    def test_multipart_falls_back_to_html(self, parser):
        """Test fallback to HTML when no plain text."""
        html_text = "<p>Only HTML here</p>"
        email = {
            "id": "html-only",
            "threadId": "thread",
            "labelIds": [],
            "payload": {
                "mimeType": "multipart/alternative",
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "HTML only"},
                    {"name": "Date", "value": "Mon, 20 Jan 2025 10:30:00 -0500"},
                ],
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {"data": base64.urlsafe_b64encode(html_text.encode("utf-8")).decode("utf-8")},
                    }
                ],
            },
        }

        result = parser.parse(email)
        assert "Only HTML here" in result.body


class TestHeaderExtraction:
    """Test header extraction from Gmail format."""

    @pytest.fixture
    def parser(self):
        return EmailParser()

    def test_extract_headers_to_dict(self, parser):
        """Test conversion of headers list to dict."""
        headers = [
            {"name": "From", "value": "sender@example.com"},
            {"name": "To", "value": "recipient@example.com"},
            {"name": "Subject", "value": "Test"},
        ]

        result = parser._extract_headers(headers)

        assert result["From"] == "sender@example.com"
        assert result["To"] == "recipient@example.com"
        assert result["Subject"] == "Test"

    def test_extract_empty_headers(self, parser):
        """Test empty headers list."""
        result = parser._extract_headers([])
        assert result == {}


class TestParseBatch:
    """Test batch parsing of multiple emails."""

    @pytest.fixture
    def parser(self):
        return EmailParser()

    def test_parse_batch_multiple_emails(self, parser):
        """Test parsing multiple emails at once."""
        emails = [
            {
                "id": f"email{i}",
                "threadId": f"thread{i}",
                "labelIds": ["INBOX"],
                "payload": {
                    "mimeType": "text/plain",
                    "headers": [
                        {"name": "From", "value": f"sender{i}@example.com"},
                        {"name": "Subject", "value": f"Email {i}"},
                        {"name": "Date", "value": "Mon, 20 Jan 2025 10:30:00 -0500"},
                    ],
                    "body": {"data": base64.urlsafe_b64encode(f"Body of email {i}".encode("utf-8")).decode("utf-8")},
                },
            }
            for i in range(3)
        ]

        results = parser.parse_batch(emails)

        assert len(results) == 3
        assert all(isinstance(r, ParsedEmail) for r in results)
        assert results[0].gmail_id == "email0"
        assert results[2].gmail_id == "email2"

    def test_parse_batch_empty_list(self, parser):
        """Test parsing empty list."""
        results = parser.parse_batch([])
        assert results == []

    def test_parse_batch_skips_invalid(self, parser):
        """Test that invalid emails are skipped."""
        emails = [
            {
                "id": "valid",
                "threadId": "thread",
                "labelIds": [],
                "payload": {
                    "mimeType": "text/plain",
                    "headers": [
                        {"name": "From", "value": "sender@example.com"},
                        {"name": "Subject", "value": "Valid"},
                        {"name": "Date", "value": "Mon, 20 Jan 2025 10:30:00 -0500"},
                    ],
                    "body": {"data": base64.urlsafe_b64encode(b"Valid body").decode()},
                },
            },
            # Invalid email (missing payload)
            {"id": "invalid"},
        ]

        results = parser.parse_batch(emails)

        # Should have at least the valid one
        assert len(results) >= 1
        assert results[0].gmail_id == "valid"


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def parser(self):
        return EmailParser()

    def test_missing_subject_uses_default(self, parser):
        """Test missing subject uses default."""
        email = {
            "id": "no-subject",
            "threadId": "thread",
            "labelIds": [],
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Date", "value": "Mon, 20 Jan 2025 10:30:00 -0500"},
                ],
                "body": {"data": base64.urlsafe_b64encode(b"Body").decode()},
            },
        }

        result = parser.parse(email)
        assert result.subject == "(No Subject)"

    def test_missing_message_id_uses_gmail_id(self, parser):
        """Test missing Message-ID uses Gmail ID."""
        email = {
            "id": "gmail-id-123",
            "threadId": "thread",
            "labelIds": [],
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Test"},
                    {"name": "Date", "value": "Mon, 20 Jan 2025 10:30:00 -0500"},
                ],
                "body": {"data": base64.urlsafe_b64encode(b"Body").decode()},
            },
        }

        result = parser.parse(email)
        assert result.message_id == "gmail-gmail-id-123"

    def test_empty_body(self, parser):
        """Test email with empty body."""
        email = {
            "id": "empty-body",
            "threadId": "thread",
            "labelIds": [],
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Empty"},
                    {"name": "Date", "value": "Mon, 20 Jan 2025 10:30:00 -0500"},
                ],
                "body": {},
            },
        }

        result = parser.parse(email)
        assert result.body == ""
