"""
Email parser for Gmail API responses.

Converts Gmail API message format into our database schema format,
handling:
- Header extraction (From, Subject, Date, Message-ID)
- Body extraction (plain text and HTML)
- MIME multipart handling
- Character encoding
"""

import base64
import email.utils
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedEmail:
    """Parsed email data ready for database insertion."""

    message_id: str
    from_address: str
    subject: str
    body: str
    received_at: datetime
    raw_headers: Dict[str, Any]
    gmail_id: str  # Gmail's internal message ID
    thread_id: str  # Gmail thread ID
    labels: List[str]


class EmailParser:
    """
    Parses Gmail API message responses into structured data.

    Usage:
        parser = EmailParser()
        raw_email = gmail_client.get_email(message_id)
        parsed = parser.parse(raw_email)
    """

    # Headers we want to preserve in raw_headers
    PRESERVED_HEADERS = [
        "From",
        "To",
        "Cc",
        "Bcc",
        "Subject",
        "Date",
        "Message-ID",
        "In-Reply-To",
        "References",
        "Content-Type",
        "MIME-Version",
        "Reply-To",
    ]

    def parse(self, gmail_message: Dict[str, Any]) -> ParsedEmail:
        """
        Parse a Gmail API message into structured data.

        Args:
            gmail_message: Raw message from Gmail API (format='full')

        Returns:
            ParsedEmail dataclass with extracted data
        """
        gmail_id = gmail_message.get("id", "")
        thread_id = gmail_message.get("threadId", "")
        labels = gmail_message.get("labelIds", [])

        # Extract headers
        payload = gmail_message.get("payload", {})
        headers = self._extract_headers(payload.get("headers", []))

        # Get key fields from headers
        message_id = headers.get("Message-ID", f"gmail-{gmail_id}")
        from_address = self._parse_email_address(headers.get("From", ""))
        subject = headers.get("Subject", "(No Subject)")
        date_str = headers.get("Date", "")
        received_at = self._parse_date(date_str)

        # Extract body
        body = self._extract_body(payload)

        # Build raw headers dict
        raw_headers = {key: headers.get(key) for key in self.PRESERVED_HEADERS if headers.get(key)}
        raw_headers["gmail_id"] = gmail_id
        raw_headers["thread_id"] = thread_id
        raw_headers["labels"] = labels

        return ParsedEmail(
            message_id=message_id,
            from_address=from_address,
            subject=subject,
            body=body,
            received_at=received_at,
            raw_headers=raw_headers,
            gmail_id=gmail_id,
            thread_id=thread_id,
            labels=labels,
        )

    def _extract_headers(self, headers_list: List[Dict]) -> Dict[str, str]:
        """
        Convert Gmail headers list to dict.

        Args:
            headers_list: List of {'name': ..., 'value': ...} dicts

        Returns:
            Dict mapping header name to value
        """
        return {header["name"]: header["value"] for header in headers_list}

    def _parse_email_address(self, from_header: str) -> str:
        """
        Extract email address from From header.

        Handles formats like:
        - "John Smith <john@example.com>"
        - "john@example.com"
        - "<john@example.com>"

        Args:
            from_header: Raw From header value

        Returns:
            Email address only
        """
        if not from_header:
            return ""

        # Use email.utils to parse
        name, email_addr = email.utils.parseaddr(from_header)

        if email_addr:
            return email_addr.lower()

        # Fallback: try regex
        match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", from_header)
        if match:
            return match.group(0).lower()

        return from_header.strip().lower()

    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse email date header into datetime.

        Args:
            date_str: RFC 2822 format date string

        Returns:
            Parsed datetime (UTC)
        """
        if not date_str:
            return datetime.now()

        try:
            # Parse RFC 2822 date
            parsed = email.utils.parsedate_to_datetime(date_str)
            return parsed

        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return datetime.now()

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """
        Extract email body from Gmail payload.

        Handles multipart messages, preferring plain text over HTML.

        Args:
            payload: Gmail message payload

        Returns:
            Email body as plain text
        """
        mime_type = payload.get("mimeType", "")

        # Simple single-part message
        if mime_type == "text/plain":
            return self._decode_body(payload.get("body", {}))

        if mime_type == "text/html":
            html = self._decode_body(payload.get("body", {}))
            return self._html_to_text(html)

        # Multipart message - look for parts
        parts = payload.get("parts", [])
        if not parts:
            # Try body directly
            body_data = payload.get("body", {})
            if body_data.get("data"):
                return self._decode_body(body_data)
            return ""

        # Search for text/plain first, then text/html
        plain_text = self._find_part_by_type(parts, "text/plain")
        if plain_text:
            return plain_text

        html_text = self._find_part_by_type(parts, "text/html")
        if html_text:
            return self._html_to_text(html_text)

        # Recurse into nested multipart
        for part in parts:
            nested_parts = part.get("parts", [])
            if nested_parts:
                result = self._extract_body(part)
                if result:
                    return result

        return ""

    def _find_part_by_type(self, parts: List[Dict], mime_type: str) -> Optional[str]:
        """
        Find and decode a specific MIME type from parts.

        Args:
            parts: List of message parts
            mime_type: MIME type to find

        Returns:
            Decoded content or None
        """
        for part in parts:
            if part.get("mimeType") == mime_type:
                return self._decode_body(part.get("body", {}))

            # Check nested parts
            nested = part.get("parts", [])
            if nested:
                result = self._find_part_by_type(nested, mime_type)
                if result:
                    return result

        return None

    def _decode_body(self, body: Dict[str, Any]) -> str:
        """
        Decode base64url encoded body data.

        Args:
            body: Gmail body object with 'data' field

        Returns:
            Decoded string
        """
        data = body.get("data", "")
        if not data:
            return ""

        try:
            # Gmail uses base64url encoding
            decoded = base64.urlsafe_b64decode(data)
            return decoded.decode("utf-8", errors="replace")

        except Exception as e:
            logger.warning(f"Failed to decode body: {e}")
            return ""

    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text.

        Simple conversion - for better results consider using
        beautifulsoup4 or html2text.

        Args:
            html: HTML string

        Returns:
            Plain text approximation
        """
        if not html:
            return ""

        # Remove script and style elements
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Convert <br> and </p> to newlines
        text = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", "\n", text, flags=re.IGNORECASE)

        # Convert <li> to bullet points
        text = re.sub(r"<li[^>]*>", "\n• ", text, flags=re.IGNORECASE)

        # Remove all other HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = unescape(text)

        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)  # Multiple newlines to double
        text = re.sub(r" +", " ", text)  # Multiple spaces to single
        text = text.strip()

        return text

    def parse_batch(self, gmail_messages: List[Dict[str, Any]]) -> List[ParsedEmail]:
        """
        Parse multiple Gmail messages.

        Args:
            gmail_messages: List of raw Gmail API messages

        Returns:
            List of ParsedEmail objects
        """
        parsed = []
        for msg in gmail_messages:
            try:
                parsed.append(self.parse(msg))
            except Exception as e:
                logger.error(f"Failed to parse message {msg.get('id')}: {e}")
                continue

        return parsed
