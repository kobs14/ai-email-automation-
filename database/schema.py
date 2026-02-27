"""
High-level database operations using raw SQL.

This layer provides repository classes that sit above the queries module
and handle business logic, data transformation, and error handling.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .connection import Database
from .queries import config as config_queries
from .queries import emails as email_queries
from .queries import entities as entity_queries
from .queries import responses as response_queries
from .queries import users as user_queries

logger = logging.getLogger(__name__)


class EmailRepository:
    """
    Data access layer for the emails table.

    Handles all CRUD operations for email records with proper
    error handling and data transformation.
    """

    def __init__(self, db: Database):
        """
        Initialize the repository.

        Args:
            db: Database instance with connection pool
        """
        self.db = db

    def create_email(
        self,
        message_id: str,
        from_address: str,
        subject: str,
        body: str,
        received_at: datetime,
        raw_headers: Optional[Dict] = None,
    ) -> int:
        """
        Insert a new email record.

        Args:
            message_id: Unique email identifier (e.g., Message-ID header)
            from_address: Sender email address
            subject: Email subject line
            body: Email body content
            received_at: Timestamp when email was received
            raw_headers: Optional dict of email headers

        Returns:
            The ID of the newly created email record

        Raises:
            DatabaseError: If insert fails
        """
        headers_json = json.dumps(raw_headers) if raw_headers else None

        result = self.db.execute_query(
            email_queries.INSERT_EMAIL,
            params=(message_id, from_address, subject, body, received_at, headers_json),
            fetch="one",
        )

        email_id = result["id"]
        logger.info(f"Created email record: id={email_id}, message_id={message_id}")
        return email_id

    def get_email_by_id(self, email_id: int) -> Optional[Dict]:
        """
        Fetch an email by its ID.

        Args:
            email_id: The email's primary key

        Returns:
            Email record as dict, or None if not found
        """
        result = self.db.execute_query(email_queries.GET_EMAIL_BY_ID, params=(email_id,), fetch="one")
        return dict(result) if result else None

    def get_email_by_message_id(self, message_id: str) -> Optional[Dict]:
        """
        Fetch an email by its message ID.

        Args:
            message_id: The unique email message identifier

        Returns:
            Email record as dict, or None if not found
        """
        result = self.db.execute_query(email_queries.GET_EMAIL_BY_MESSAGE_ID, params=(message_id,), fetch="one")
        return dict(result) if result else None

    def email_exists(self, message_id: str) -> bool:
        """
        Check if an email with the given message ID exists.

        Args:
            message_id: The email message identifier to check

        Returns:
            True if email exists, False otherwise
        """
        result = self.db.execute_query(email_queries.EMAIL_EXISTS_BY_MESSAGE_ID, params=(message_id,), fetch="one")
        return result["exists"] if result else False

    def get_email_by_gmail_id(self, gmail_id: str) -> Optional[Dict]:
        """
        Fetch an email by its Gmail message ID (stored in raw_headers).

        Args:
            gmail_id: The Gmail internal message ID

        Returns:
            Email record as dict, or None if not found
        """
        result = self.db.execute_query(email_queries.GET_EMAIL_BY_GMAIL_ID, params=(gmail_id,), fetch="one")
        return dict(result) if result else None

    def gmail_id_exists(self, gmail_id: str) -> bool:
        """
        Check if an email with the given Gmail ID already exists.

        Args:
            gmail_id: The Gmail internal message ID

        Returns:
            True if email exists, False otherwise
        """
        result = self.db.execute_query(email_queries.EMAIL_EXISTS_BY_GMAIL_ID, params=(gmail_id,), fetch="one")
        return result["exists"] if result else False

    def update_status(self, email_id: int, status: str) -> bool:
        """
        Update an email's processing status.

        Args:
            email_id: The email's primary key
            status: New status (pending, classified, responded, failed)

        Returns:
            True if update succeeded, False otherwise
        """
        result = self.db.execute_query(email_queries.UPDATE_EMAIL_STATUS, params=(status, email_id), fetch="one")

        if result:
            logger.info(f"Updated email {email_id} status to '{status}'")
            return True
        return False

    def update_intent(self, email_id: int, intent: str) -> bool:
        """
        Update an email's classified intent and mark as classified.

        Args:
            email_id: The email's primary key
            intent: Classified intent (quote_request, booking_request, etc.)

        Returns:
            True if update succeeded, False otherwise
        """
        result = self.db.execute_query(email_queries.UPDATE_EMAIL_INTENT, params=(intent, email_id), fetch="one")

        if result:
            logger.info(f"Classified email {email_id} as '{intent}'")
            return True
        return False

    def mark_responded(self, email_id: int) -> bool:
        """Mark an email as having been responded to."""
        result = self.db.execute_query(email_queries.MARK_EMAIL_RESPONDED, params=(email_id,), fetch="one")
        return result is not None

    def mark_failed(self, email_id: int) -> bool:
        """Mark an email as failed processing."""
        result = self.db.execute_query(email_queries.MARK_EMAIL_FAILED, params=(email_id,), fetch="one")
        return result is not None

    def get_pending_emails(self, limit: int = 10) -> List[Dict]:
        """
        Get emails pending processing.

        Args:
            limit: Maximum number of emails to return

        Returns:
            List of pending email records
        """
        results = self.db.execute_query(email_queries.GET_PENDING_EMAILS, params=(limit,), fetch="all")
        return [dict(r) for r in results] if results else []

    def get_emails_by_status(self, status: str, limit: int = 50) -> List[Dict]:
        """Get emails with a specific status."""
        results = self.db.execute_query(email_queries.GET_EMAILS_BY_STATUS, params=(status, limit), fetch="all")
        return [dict(r) for r in results] if results else []

    def get_emails_by_intent(self, intent: str, limit: int = 50) -> List[Dict]:
        """Get emails with a specific classified intent."""
        results = self.db.execute_query(email_queries.GET_EMAILS_BY_INTENT, params=(intent, limit), fetch="all")
        return [dict(r) for r in results] if results else []

    def get_recent_emails(self, limit: int = 20) -> List[Dict]:
        """Get the most recent emails."""
        results = self.db.execute_query(email_queries.GET_RECENT_EMAILS, params=(limit,), fetch="all")
        return [dict(r) for r in results] if results else []

    def count_by_status(self) -> Dict[str, int]:
        """Get count of emails grouped by status."""
        results = self.db.execute_query(email_queries.COUNT_EMAILS_BY_STATUS, fetch="all")
        return {r["status"]: r["count"] for r in results} if results else {}

    def count_pending(self) -> int:
        """Get count of pending emails."""
        result = self.db.execute_query(email_queries.COUNT_PENDING_EMAILS, fetch="one")
        return result["count"] if result else 0

    def delete_email(self, email_id: int) -> bool:
        """Delete an email by ID (cascades to entities and responses)."""
        result = self.db.execute_query(email_queries.DELETE_EMAIL_BY_ID, params=(email_id,), fetch="one")
        return result is not None

    def create_if_not_exists(
        self,
        gmail_id: str,
        message_id: str,
        from_address: str,
        subject: str,
        body: str,
        received_at: datetime,
        raw_headers: Optional[Dict] = None,
    ) -> tuple[Optional[int], bool]:
        """
        Create an email if it doesn't already exist (by gmail_id).

        Args:
            gmail_id: Gmail internal message ID
            message_id: Email Message-ID header
            from_address: Sender email address
            subject: Email subject line
            body: Email body content
            received_at: Timestamp when email was received
            raw_headers: Optional dict of email headers (should include gmail_id)

        Returns:
            Tuple of (email_id, created) where:
            - email_id: The ID of the existing or newly created email
            - created: True if a new email was created, False if it already existed
        """
        # Check if email already exists
        if self.gmail_id_exists(gmail_id):
            existing = self.get_email_by_gmail_id(gmail_id)
            if existing:
                logger.debug(f"Email with gmail_id={gmail_id} already exists (id={existing['id']})")
                return existing["id"], False

        # Create new email
        email_id = self.create_email(
            message_id=message_id,
            from_address=from_address,
            subject=subject,
            body=body,
            received_at=received_at,
            raw_headers=raw_headers,
        )
        return email_id, True


class EntityRepository:
    """
    Data access layer for the extracted_entities table.

    Handles storage and retrieval of AI-extracted entities from emails.
    """

    def __init__(self, db: Database):
        """
        Initialize the repository.

        Args:
            db: Database instance with connection pool
        """
        self.db = db

    def create_entity(self, email_id: int, entity_type: str, entity_value: str, confidence: float = 1.0) -> int:
        """
        Insert a single extracted entity.

        Args:
            email_id: ID of the source email
            entity_type: Type of entity (e.g., 'property_type', 'bedrooms')
            entity_value: Extracted value
            confidence: Confidence score (0.0 to 1.0)

        Returns:
            ID of the created entity
        """
        result = self.db.execute_query(
            entity_queries.INSERT_ENTITY, params=(email_id, entity_type, entity_value, confidence), fetch="one"
        )

        entity_id = result["id"]
        logger.debug(f"Created entity: {entity_type}={entity_value} for email {email_id}")
        return entity_id

    def create_entities_batch(self, email_id: int, entities: List[Dict[str, Any]]) -> List[int]:
        """
        Bulk insert multiple entities for an email.

        Args:
            email_id: ID of the source email
            entities: List of dicts with keys: type, value, confidence

        Returns:
            List of created entity IDs

        Example:
            entities = [
                {"type": "property_type", "value": "house", "confidence": 0.95},
                {"type": "bedrooms", "value": "3", "confidence": 0.90},
            ]
            ids = repo.create_entities_batch(email_id=1, entities=entities)
        """
        if not entities:
            return []

        values = [(email_id, e["type"], e["value"], e.get("confidence", 1.0)) for e in entities]

        results = self.db.execute_values(entity_queries.INSERT_ENTITIES_BATCH, values, fetch=True)

        entity_ids = [r["id"] for r in results] if results else []
        logger.info(f"Created {len(entity_ids)} entities for email {email_id}")
        return entity_ids

    def get_entities_by_email(self, email_id: int) -> List[Dict]:
        """
        Get all entities extracted from an email.

        Args:
            email_id: The source email's ID

        Returns:
            List of entity records
        """
        results = self.db.execute_query(entity_queries.GET_ENTITIES_BY_EMAIL, params=(email_id,), fetch="all")
        return [dict(r) for r in results] if results else []

    def get_entities_as_dict(self, email_id: int) -> Dict[str, Any]:
        """
        Get entities as a simple type->value dictionary.

        Useful for passing extracted data to response generation.

        Args:
            email_id: The source email's ID

        Returns:
            Dict mapping entity types to their values
        """
        results = self.db.execute_query(entity_queries.GET_ENTITIES_BY_EMAIL_AS_DICT, params=(email_id,), fetch="all")

        if not results:
            return {}

        # Return highest confidence value for each type
        entities = {}
        for r in results:
            if r["entity_type"] not in entities:
                entities[r["entity_type"]] = r["entity_value"]

        return entities

    def get_entity_by_type(self, email_id: int, entity_type: str) -> Optional[Dict]:
        """Get the highest-confidence entity of a specific type."""
        result = self.db.execute_query(entity_queries.GET_ENTITY_BY_TYPE, params=(email_id, entity_type), fetch="one")
        return dict(result) if result else None

    def get_high_confidence_entities(self, email_id: int, min_confidence: float = 0.8) -> List[Dict]:
        """Get entities above a confidence threshold."""
        results = self.db.execute_query(
            entity_queries.GET_HIGH_CONFIDENCE_ENTITIES, params=(email_id, min_confidence), fetch="all"
        )
        return [dict(r) for r in results] if results else []

    def delete_entities_by_email(self, email_id: int) -> int:
        """Delete all entities for an email. Returns count deleted."""
        results = self.db.execute_query(entity_queries.DELETE_ENTITIES_BY_EMAIL, params=(email_id,), fetch="all")
        return len(results) if results else 0

    def count_for_email(self, email_id: int) -> int:
        """Count entities extracted from an email."""
        result = self.db.execute_query(entity_queries.COUNT_ENTITIES_FOR_EMAIL, params=(email_id,), fetch="one")
        return result["count"] if result else 0


class ResponseRepository:
    """
    Data access layer for the responses table.

    Handles storage and management of AI-generated response drafts.
    """

    def __init__(self, db: Database):
        """
        Initialize the repository.

        Args:
            db: Database instance with connection pool
        """
        self.db = db

    def create_response(self, email_id: int, draft_content: str, status: str = "draft") -> int:
        """
        Create a new response draft.

        Args:
            email_id: ID of the email being responded to
            draft_content: The generated response text
            status: Initial status (default: 'draft')

        Returns:
            ID of the created response
        """
        result = self.db.execute_query(
            response_queries.INSERT_RESPONSE, params=(email_id, draft_content, status), fetch="one"
        )

        response_id = result["id"]
        logger.info(f"Created response draft: id={response_id} for email {email_id}")
        return response_id

    def get_response_by_id(self, response_id: int) -> Optional[Dict]:
        """Get a response by its ID."""
        result = self.db.execute_query(response_queries.GET_RESPONSE_BY_ID, params=(response_id,), fetch="one")
        return dict(result) if result else None

    def get_response_for_email(self, email_id: int) -> Optional[Dict]:
        """Get the most recent response for an email."""
        result = self.db.execute_query(response_queries.GET_RESPONSE_BY_EMAIL_ID, params=(email_id,), fetch="one")
        return dict(result) if result else None

    def update_content(self, response_id: int, content: str) -> bool:
        """Update the draft content of a response."""
        result = self.db.execute_query(
            response_queries.UPDATE_RESPONSE_CONTENT, params=(content, response_id), fetch="one"
        )
        return result is not None

    def update_status(self, response_id: int, status: str) -> bool:
        """Update the status of a response."""
        result = self.db.execute_query(
            response_queries.UPDATE_RESPONSE_STATUS, params=(status, status, response_id), fetch="one"
        )

        if result:
            logger.info(f"Updated response {response_id} status to '{status}'")
            return True
        return False

    def approve_response(self, response_id: int, approved_by: str) -> bool:
        """
        Mark a response as approved.

        Args:
            response_id: The response's ID
            approved_by: Identifier of who approved (e.g., username)

        Returns:
            True if approval succeeded
        """
        result = self.db.execute_query(
            response_queries.APPROVE_RESPONSE, params=(approved_by, response_id), fetch="one"
        )

        if result:
            logger.info(f"Response {response_id} approved by {approved_by}")
            return True
        return False

    def reject_response(self, response_id: int) -> bool:
        """Mark a response as rejected."""
        result = self.db.execute_query(response_queries.REJECT_RESPONSE, params=(response_id,), fetch="one")
        return result is not None

    def mark_sent(self, response_id: int) -> bool:
        """Mark a response as sent."""
        result = self.db.execute_query(response_queries.MARK_RESPONSE_SENT, params=(response_id,), fetch="one")

        if result:
            logger.info(f"Response {response_id} marked as sent")
            return True
        return False

    def get_pending_drafts(self) -> List[Dict]:
        """Get all responses in draft status (pending review)."""
        results = self.db.execute_query(response_queries.GET_PENDING_DRAFTS, fetch="all")
        return [dict(r) for r in results] if results else []

    def get_approved_unsent(self) -> List[Dict]:
        """Get approved responses that haven't been sent yet."""
        results = self.db.execute_query(response_queries.GET_APPROVED_UNSENT_RESPONSES, fetch="all")
        return [dict(r) for r in results] if results else []

    def get_responses_by_status(self, status: str, limit: int = 50) -> List[Dict]:
        """Get responses with a specific status."""
        results = self.db.execute_query(response_queries.GET_RESPONSES_BY_STATUS, params=(status, limit), fetch="all")
        return [dict(r) for r in results] if results else []

    def count_pending_drafts(self) -> int:
        """Count responses awaiting review."""
        result = self.db.execute_query(response_queries.COUNT_PENDING_DRAFTS, fetch="one")
        return result["count"] if result else 0

    def delete_response(self, response_id: int) -> bool:
        """Delete a response by ID."""
        result = self.db.execute_query(response_queries.DELETE_RESPONSE_BY_ID, params=(response_id,), fetch="one")
        return result is not None

    # -------------------------------------------------------------------------
    # Email Sending Methods
    # -------------------------------------------------------------------------

    def record_send_error(self, response_id: int, error_message: str) -> Optional[Dict]:
        """
        Record a send error and increment attempt counter.

        Args:
            response_id: The response's ID
            error_message: Description of the error

        Returns:
            Updated response data or None if not found
        """
        result = self.db.execute_query(
            response_queries.RECORD_SEND_ERROR, params=(error_message, response_id), fetch="one"
        )

        if result:
            logger.warning(f"Response {response_id} send failed (attempt {result['send_attempts']}): {error_message}")
            return dict(result)
        return None

    def mark_sent_with_message_id(self, response_id: int, sent_message_id: str) -> bool:
        """
        Mark a response as successfully sent and record the Gmail message ID.

        Args:
            response_id: The response's ID
            sent_message_id: Gmail message ID of the sent email

        Returns:
            True if update succeeded
        """
        result = self.db.execute_query(
            response_queries.MARK_SENT_WITH_MESSAGE_ID, params=(sent_message_id, response_id), fetch="one"
        )

        if result:
            logger.info(f"Response {response_id} marked as sent (message_id={sent_message_id})")
            return True
        return False

    def mark_failed(self, response_id: int, error_message: str) -> bool:
        """
        Mark a response as permanently failed.

        Args:
            response_id: The response's ID
            error_message: Description of the failure

        Returns:
            True if update succeeded
        """
        result = self.db.execute_query(
            response_queries.MARK_RESPONSE_FAILED, params=(error_message, response_id), fetch="one"
        )

        if result:
            logger.error(f"Response {response_id} marked as failed: {error_message}")
            return True
        return False

    def get_approved_for_sending(self, max_attempts: int = 3, limit: int = 10) -> List[Dict]:
        """
        Get approved responses that are ready to be sent.

        Args:
            max_attempts: Maximum send attempts to include
            limit: Maximum number of responses to return

        Returns:
            List of response records with associated email data
        """
        results = self.db.execute_query(
            response_queries.GET_APPROVED_RESPONSES_FOR_SENDING, params=(max_attempts, limit), fetch="all"
        )
        return [dict(r) for r in results] if results else []

    def get_response_with_email(self, response_id: int) -> Optional[Dict]:
        """
        Get a response with its associated email data.

        Args:
            response_id: The response's ID

        Returns:
            Response record with email data, or None if not found
        """
        result = self.db.execute_query(response_queries.GET_RESPONSE_WITH_EMAIL, params=(response_id,), fetch="one")
        return dict(result) if result else None

    def get_failed_responses(self, limit: int = 50) -> List[Dict]:
        """Get responses that failed to send."""
        results = self.db.execute_query(response_queries.GET_FAILED_RESPONSES, params=(limit,), fetch="all")
        return [dict(r) for r in results] if results else []

    def reset_for_retry(self, response_id: int) -> bool:
        """
        Reset a failed response to approved status for retry.

        Args:
            response_id: The response's ID

        Returns:
            True if reset succeeded
        """
        result = self.db.execute_query(response_queries.RESET_RESPONSE_FOR_RETRY, params=(response_id,), fetch="one")

        if result:
            logger.info(f"Response {response_id} reset for retry")
            return True
        return False


class ConfigRepository:
    """
    Data access layer for the business_config table.

    Handles storage and retrieval of business configuration,
    pricing rules, and AI prompt settings stored as JSONB.
    """

    def __init__(self, db: Database):
        """
        Initialize the repository.

        Args:
            db: Database instance with connection pool
        """
        self.db = db
        self._cache: Dict[str, Any] = {}

    def set_config(self, key: str, value: Dict, description: Optional[str] = None) -> bool:
        """
        Set or update a configuration value.

        Args:
            key: Configuration key
            value: Configuration value (will be stored as JSONB)
            description: Optional human-readable description

        Returns:
            True if operation succeeded
        """
        value_json = json.dumps(value)

        result = self.db.execute_query(config_queries.UPSERT_CONFIG, params=(key, value_json, description), fetch="one")

        if result:
            # Invalidate cache
            self._cache.pop(key, None)
            logger.info(f"Set config: {key}")
            return True
        return False

    def get_config(self, key: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            use_cache: Whether to use cached value if available

        Returns:
            Configuration value as dict, or None if not found
        """
        if use_cache and key in self._cache:
            return self._cache[key]

        result = self.db.execute_query(config_queries.GET_CONFIG, params=(key,), fetch="one")

        if result and result["value"]:
            value = result["value"]
            # Handle both string and pre-parsed JSONB
            if isinstance(value, str):
                value = json.loads(value)
            self._cache[key] = value
            return value
        return None

    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration entries.

        Returns:
            Dict mapping config keys to their values
        """
        results = self.db.execute_query(config_queries.GET_ALL_CONFIG, fetch="all")

        if not results:
            return {}

        config = {}
        for r in results:
            value = r["value"]
            if isinstance(value, str):
                value = json.loads(value)
            config[r["key"]] = value

        return config

    def config_exists(self, key: str) -> bool:
        """Check if a configuration key exists."""
        result = self.db.execute_query(config_queries.CONFIG_EXISTS, params=(key,), fetch="one")
        return result["exists"] if result else False

    def delete_config(self, key: str) -> bool:
        """Delete a configuration entry."""
        result = self.db.execute_query(config_queries.DELETE_CONFIG, params=(key,), fetch="one")

        if result:
            self._cache.pop(key, None)
            logger.info(f"Deleted config: {key}")
            return True
        return False

    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._cache.clear()

    # Convenience methods for common configs

    def get_pricing_rules(self) -> Optional[Dict]:
        """Get pricing rules configuration."""
        return self.get_config("pricing_rules")

    def get_service_multipliers(self) -> Optional[Dict]:
        """Get service type multipliers."""
        return self.get_config("service_multipliers")

    def get_business_info(self) -> Optional[Dict]:
        """Get business information."""
        return self.get_config("business_info")

    def get_brand_voice(self) -> Optional[Dict]:
        """Get brand voice guidelines for AI responses."""
        return self.get_config("brand_voice")

    def get_entity_extraction_rules(self, intent: Optional[str] = None) -> Any:
        """
        Get entity extraction rules.

        Args:
            intent: Optional intent to get rules for. If None, returns all rules.

        Returns:
            Extraction rules dict or list of fields for specific intent
        """
        rules = self.get_config("entity_extraction_rules")

        if rules and intent:
            return rules.get(intent, [])
        return rules

    def get_response_template(self, intent: str) -> Optional[Dict]:
        """Get response template guidelines for a specific intent."""
        templates = self.get_config("response_templates")

        if templates:
            return templates.get(intent)
        return None


class UserRepository:
    """
    Data access layer for the users table.

    Handles user authentication and management operations.
    """

    def __init__(self, db: Database):
        """
        Initialize the repository.

        Args:
            db: Database instance with connection pool
        """
        self.db = db

    def create_user(self, username: str, email: str, password_hash: str, role: str = "viewer") -> Optional[Dict]:
        """
        Create a new user.

        Args:
            username: Unique username
            email: Unique email address
            password_hash: bcrypt hashed password
            role: User role (admin, operator, viewer)

        Returns:
            Created user record or None on failure
        """
        result = self.db.execute_query(
            user_queries.INSERT_USER, params=(username, email, password_hash, role), fetch="one"
        )
        if result:
            logger.info(f"Created user: {username} with role {role}")
            return dict(result)
        return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Fetch a user by ID."""
        result = self.db.execute_query(user_queries.GET_USER_BY_ID, params=(user_id,), fetch="one")
        return dict(result) if result else None

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Fetch a user by username."""
        result = self.db.execute_query(user_queries.GET_USER_BY_USERNAME, params=(username,), fetch="one")
        return dict(result) if result else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Fetch a user by email."""
        result = self.db.execute_query(user_queries.GET_USER_BY_EMAIL, params=(email,), fetch="one")
        return dict(result) if result else None

    def update_last_login(self, user_id: int) -> bool:
        """Record a user's login timestamp."""
        result = self.db.execute_query(user_queries.UPDATE_USER_LAST_LOGIN, params=(user_id,), fetch="one")
        return result is not None

    def update_password(self, user_id: int, password_hash: str) -> bool:
        """Update a user's password hash."""
        result = self.db.execute_query(user_queries.UPDATE_USER_PASSWORD, params=(password_hash, user_id), fetch="one")
        return result is not None

    def get_all_users(self) -> List[Dict]:
        """Get all users."""
        results = self.db.execute_query(user_queries.GET_ALL_USERS, fetch="all")
        return [dict(r) for r in results] if results else []

    def username_exists(self, username: str) -> bool:
        """Check if a username is already taken."""
        result = self.db.execute_query(user_queries.USER_EXISTS_BY_USERNAME, params=(username,), fetch="one")
        return result["exists"] if result else False
