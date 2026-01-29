#!/usr/bin/env python3
"""
Email ingestion script.

Fetches new emails from Gmail, parses them, and stores them in the database.
Optionally processes them through the AI classification pipeline.

Usage:
    # Fetch and store unread emails
    python scripts/fetch_emails.py

    # Fetch with custom limit
    python scripts/fetch_emails.py --max 20

    # Fetch and process through AI pipeline
    python scripts/fetch_emails.py --process

    # Fetch without marking as read
    python scripts/fetch_emails.py --no-mark-read

    # Dry run (don't save to database)
    python scripts/fetch_emails.py --dry-run
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from database.connection import Database
from database.schema import EmailRepository, EntityRepository, ResponseRepository, ConfigRepository
from services.gmail import GmailAuth, GmailClient, EmailParser
from services.gmail.parser import ParsedEmail

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmailIngestionService:
    """
    Service for fetching and storing emails from Gmail.

    Coordinates between Gmail API, parser, and database repositories.
    """

    def __init__(
        self,
        gmail_client: GmailClient,
        db: Database,
        mark_as_read: bool = True
    ):
        """
        Initialize ingestion service.

        Args:
            gmail_client: Authenticated Gmail client
            db: Database connection
            mark_as_read: Whether to mark emails as read after fetching
        """
        self.gmail = gmail_client
        self.parser = EmailParser()
        self.db = db
        self.email_repo = EmailRepository(db)
        self.mark_as_read = mark_as_read

    def fetch_and_store(
        self,
        max_results: int = 10,
        query: Optional[str] = None,
        dry_run: bool = False
    ) -> List[int]:
        """
        Fetch emails from Gmail and store in database.

        Args:
            max_results: Maximum emails to fetch
            query: Optional Gmail search query
            dry_run: If True, don't save to database

        Returns:
            List of created email IDs
        """
        # Fetch email list from Gmail
        if query:
            messages = self.gmail.fetch_emails_with_query(query, max_results)
        else:
            messages = self.gmail.fetch_unread_emails(max_results)

        if not messages:
            logger.info("No new emails found")
            return []

        logger.info(f"Found {len(messages)} emails to process")

        created_ids = []
        skipped = 0
        errors = 0

        for msg_meta in messages:
            gmail_id = msg_meta['id']

            try:
                # Check if already exists in database
                existing = self.email_repo.get_email_by_gmail_id(gmail_id)
                if existing:
                    logger.debug(f"Email {gmail_id} already exists, skipping")
                    skipped += 1
                    continue

                # Fetch full email content
                raw_email = self.gmail.get_email(gmail_id)

                # Parse email
                parsed = self.parser.parse(raw_email)

                if dry_run:
                    logger.info(f"[DRY RUN] Would store: {parsed.subject[:50]}...")
                    continue

                # Store in database
                email_id = self._store_email(parsed)
                created_ids.append(email_id)

                logger.info(f"Stored email {email_id}: {parsed.subject[:50]}...")

                # Mark as read in Gmail
                if self.mark_as_read:
                    self.gmail.mark_as_read(gmail_id)

            except Exception as e:
                logger.error(f"Failed to process email {gmail_id}: {e}")
                errors += 1
                continue

        logger.info(
            f"Ingestion complete: {len(created_ids)} stored, "
            f"{skipped} skipped, {errors} errors"
        )

        return created_ids

    def _store_email(self, parsed: ParsedEmail) -> int:
        """
        Store a parsed email in the database.

        Args:
            parsed: ParsedEmail object

        Returns:
            Created email ID
        """
        email_id = self.email_repo.create_email(
            message_id=parsed.message_id,
            from_address=parsed.from_address,
            subject=parsed.subject,
            body=parsed.body,
            received_at=parsed.received_at,
            raw_headers=parsed.raw_headers
        )

        return email_id


def process_emails_with_ai(
    email_ids: List[int],
    db: Database,
    skip_ai: bool = False
) -> dict:
    """
    Process stored emails through AI classification pipeline.

    Args:
        email_ids: List of email IDs to process
        db: Database connection
        skip_ai: If True, skip AI calls (for testing)

    Returns:
        Processing results summary
    """
    from proof_of_concept.claude_test import (
        classify_email,
        extract_entities,
        generate_response,
        calculate_quote,
        get_claude_client
    )

    email_repo = EmailRepository(db)
    entity_repo = EntityRepository(db)
    response_repo = ResponseRepository(db)
    config_repo = ConfigRepository(db)

    # Get business config
    business_info = config_repo.get_business_info()
    brand_voice = config_repo.get_brand_voice()
    pricing_rules = config_repo.get_pricing_rules()
    service_multipliers = config_repo.get_service_multipliers()

    client = None if skip_ai else get_claude_client()

    results = {
        'processed': 0,
        'errors': 0,
        'details': []
    }

    for email_id in email_ids:
        try:
            email = email_repo.get_email_by_id(email_id)
            if not email:
                continue

            logger.info(f"Processing email {email_id}: {email['subject'][:40]}...")

            # Classify
            if skip_ai:
                classification = {
                    'intent': 'quote_request',
                    'confidence': 0.9,
                    'reasoning': 'Mock classification'
                }
            else:
                classification = classify_email(
                    email_body=email['body'],
                    from_address=email['from_address'],
                    subject=email['subject'],
                    client=client
                )

            email_repo.update_intent(email_id, classification['intent'])
            logger.info(f"  Classified as: {classification['intent']}")

            # Extract entities
            if skip_ai:
                entities = []
            else:
                entities = extract_entities(
                    email_body=email['body'],
                    intent=classification['intent'],
                    from_address=email['from_address'],
                    subject=email['subject'],
                    client=client
                )

            if entities:
                entity_repo.create_entities_batch(email_id, entities)
                logger.info(f"  Extracted {len(entities)} entities")

            # Calculate quote if applicable
            quote_data = None
            if classification['intent'] == 'quote_request' and entities:
                quote_data = calculate_quote(
                    entities,
                    pricing_rules=pricing_rules,
                    service_multipliers=service_multipliers
                )
                if quote_data:
                    logger.info(f"  Quote: ${quote_data['total']:.2f}")

            # Generate response
            if skip_ai:
                response_text = f"Thank you for your {classification['intent'].replace('_', ' ')}. We will respond shortly."
            else:
                response_text = generate_response(
                    email_body=email['body'],
                    intent=classification['intent'],
                    entities=entities,
                    from_address=email['from_address'],
                    subject=email['subject'],
                    quote_data=quote_data,
                    business_info=business_info,
                    brand_voice=brand_voice,
                    client=client
                )

            response_repo.create_response(email_id, response_text)
            email_repo.mark_responded(email_id)
            logger.info(f"  Response generated and stored")

            results['processed'] += 1
            results['details'].append({
                'email_id': email_id,
                'intent': classification['intent'],
                'entities_count': len(entities),
                'quote': quote_data['total'] if quote_data else None
            })

        except Exception as e:
            logger.error(f"Failed to process email {email_id}: {e}")
            results['errors'] += 1

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch emails from Gmail and store in database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/fetch_emails.py                    # Fetch unread emails
  python scripts/fetch_emails.py --max 20           # Fetch up to 20 emails
  python scripts/fetch_emails.py --process          # Fetch and run AI pipeline
  python scripts/fetch_emails.py --query "subject:quote"  # Fetch with query
  python scripts/fetch_emails.py --dry-run          # Preview without saving
        """
    )

    parser.add_argument(
        '--max', '-m',
        type=int,
        default=10,
        help='Maximum emails to fetch (default: 10)'
    )
    parser.add_argument(
        '--query', '-q',
        help='Gmail search query (e.g., "subject:quote", "from:customer@example.com")'
    )
    parser.add_argument(
        '--process', '-p',
        action='store_true',
        help='Process fetched emails through AI pipeline'
    )
    parser.add_argument(
        '--skip-ai',
        action='store_true',
        help='Skip AI calls when processing (use mock data)'
    )
    parser.add_argument(
        '--no-mark-read',
        action='store_true',
        help='Do not mark emails as read in Gmail'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview only, do not save to database'
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Email Ingestion Service")
    print("=" * 60)

    # Initialize Gmail client
    try:
        auth = GmailAuth()
        gmail = GmailClient(auth)
        profile = gmail.get_profile()
        print(f"\n✓ Connected to Gmail: {profile['emailAddress']}")
    except Exception as e:
        print(f"\n❌ Gmail connection failed: {e}")
        print("Run 'python scripts/setup_gmail_oauth.py' first")
        return 1

    # Initialize database
    try:
        db = Database(settings.database.dsn)
        print(f"✓ Connected to database")
    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        print("Make sure PostgreSQL is running (docker-compose up -d)")
        return 1

    # Fetch and store emails
    print(f"\nFetching emails (max: {args.max})...")
    if args.query:
        print(f"Query: {args.query}")

    service = EmailIngestionService(
        gmail_client=gmail,
        db=db,
        mark_as_read=not args.no_mark_read
    )

    email_ids = service.fetch_and_store(
        max_results=args.max,
        query=args.query,
        dry_run=args.dry_run
    )

    if args.dry_run:
        print("\n[DRY RUN] No emails were saved to database")
        db.close_all_connections()
        return 0

    print(f"\n✓ Stored {len(email_ids)} new emails")

    # Process through AI pipeline if requested
    if args.process and email_ids:
        print("\n" + "-" * 40)
        print("Processing through AI pipeline...")
        print("-" * 40)

        results = process_emails_with_ai(
            email_ids=email_ids,
            db=db,
            skip_ai=args.skip_ai
        )

        print(f"\n✓ Processed: {results['processed']}")
        print(f"  Errors: {results['errors']}")

        if results['details']:
            print("\nProcessing summary:")
            for detail in results['details']:
                quote_str = f"${detail['quote']:.2f}" if detail['quote'] else "N/A"
                print(
                    f"  Email {detail['email_id']}: "
                    f"{detail['intent']} | "
                    f"{detail['entities_count']} entities | "
                    f"Quote: {quote_str}"
                )

    # Cleanup
    db.close_all_connections()

    print("\n" + "=" * 60)
    print("  Complete!")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
