"""
Celery tasks for email processing.

Tasks:
- fetch_emails_task: Fetch new emails from Gmail
- process_pending_emails_task: Process emails awaiting classification
- process_single_email_task: Process a specific email by ID
"""

import logging
from typing import Any, Dict, List

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


def get_repositories():
    """Get repository instances with database connection."""
    from database.connection import get_database
    from database.schema import EmailRepository, EntityRepository, ResponseRepository

    db = get_database()
    return {
        'email': EmailRepository(db),
        'entity': EntityRepository(db),
        'response': ResponseRepository(db),
    }


def get_email_repository():
    """Get EmailRepository instance with database connection."""
    return get_repositories()['email']


@shared_task(
    bind=True,
    name='services.tasks.email_tasks.fetch_emails_task',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def fetch_emails_task(self, max_results: int = 10) -> Dict[str, Any]:
    """
    Fetch new unread emails from Gmail.

    This task:
    1. Connects to Gmail API
    2. Fetches unread emails
    3. Parses and stores them in the database
    4. Queues them for processing

    Args:
        max_results: Maximum number of emails to fetch per run

    Returns:
        Dict with fetch results (count, message_ids, errors)
    """
    from services.gmail.auth import GmailAuth
    from services.gmail.client import GmailClient
    from services.gmail.parser import EmailParser

    logger.info(f"Starting email fetch task (max_results={max_results})")

    try:
        # Initialize Gmail client
        auth = GmailAuth()
        client = GmailClient(auth)
        parser = EmailParser()
        email_repo = get_email_repository()

        # Fetch unread emails
        messages = client.fetch_unread_emails(max_results=max_results)

        if not messages:
            logger.info("No new unread emails found")
            return {
                'status': 'success',
                'fetched_count': 0,
                'new_count': 0,
                'message_ids': [],
            }

        # Fetch full content and parse
        fetched_emails = []
        new_emails = []
        errors = []

        for msg_metadata in messages:
            gmail_id = msg_metadata['id']
            try:
                # Check if already in database
                if email_repo.gmail_id_exists(gmail_id):
                    logger.debug(f"Email {gmail_id} already exists, skipping")
                    continue

                # Get full email content
                full_message = client.get_email(gmail_id)
                parsed = parser.parse(full_message)

                # Prepare raw_headers with gmail_id
                raw_headers = parsed.raw_headers or {}
                raw_headers['gmail_id'] = parsed.gmail_id
                raw_headers['thread_id'] = parsed.thread_id
                raw_headers['labels'] = parsed.labels

                # Store in database
                email_id, created = email_repo.create_if_not_exists(
                    gmail_id=parsed.gmail_id,
                    message_id=parsed.message_id,
                    from_address=parsed.from_address,
                    subject=parsed.subject,
                    body=parsed.body,
                    received_at=parsed.received_at,
                    raw_headers=raw_headers
                )

                fetched_emails.append({
                    'gmail_id': parsed.gmail_id,
                    'email_id': email_id,
                    'message_id': parsed.message_id,
                    'from_address': parsed.from_address,
                    'subject': parsed.subject,
                    'created': created,
                })

                if created:
                    new_emails.append(email_id)
                    logger.info(f"Stored new email: {parsed.subject[:50]}... (id={email_id})")

                    # Mark as read in Gmail
                    client.mark_as_read(gmail_id)

            except Exception as e:
                logger.error(f"Failed to fetch/parse email {gmail_id}: {e}")
                errors.append({'gmail_id': gmail_id, 'error': str(e)})

        logger.info(
            f"Email fetch complete: {len(fetched_emails)} processed, "
            f"{len(new_emails)} new, {len(errors)} errors"
        )

        return {
            'status': 'success',
            'fetched_count': len(fetched_emails),
            'new_count': len(new_emails),
            'new_email_ids': new_emails,
            'message_ids': [e['gmail_id'] for e in fetched_emails],
            'errors': errors,
        }

    except SoftTimeLimitExceeded:
        logger.warning("Fetch task hit soft time limit")
        raise

    except Exception as e:
        logger.error(f"Email fetch task failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='services.tasks.email_tasks.process_pending_emails_task',
    max_retries=3,
    default_retry_delay=30,
)
def process_pending_emails_task(self, batch_size: int = 10) -> Dict[str, Any]:
    """
    Process emails that are pending classification.

    This task:
    1. Queries database for pending emails
    2. Sends each to Claude for classification & entity extraction
    3. Generates response draft
    4. Updates database with results

    Args:
        batch_size: Number of emails to process per run

    Returns:
        Dict with processing results
    """
    logger.info(f"Starting pending emails processing (batch_size={batch_size})")

    try:
        repos = get_repositories()
        email_repo = repos['email']
        entity_repo = repos['entity']
        response_repo = repos['response']

        # Get pending emails from database
        pending_emails = email_repo.get_pending_emails(limit=batch_size)

        if not pending_emails:
            logger.info("No pending emails to process")
            return {
                'status': 'success',
                'processed_count': 0,
                'results': [],
            }

        logger.info(f"Found {len(pending_emails)} pending emails to process")

        results = []
        for email_record in pending_emails:
            email_id = email_record['id']
            try:
                # Process with Claude
                result = _process_email_with_claude(
                    email_record, email_repo, entity_repo, response_repo
                )
                results.append({
                    'email_id': email_id,
                    'status': 'success',
                    **result,
                })

            except Exception as e:
                logger.error(f"Failed to process email {email_id}: {e}")
                email_repo.mark_failed(email_id)
                results.append({
                    'email_id': email_id,
                    'status': 'error',
                    'error': str(e),
                })

        processed = [r for r in results if r.get('status') == 'success']
        logger.info(f"Processed {len(processed)}/{len(results)} emails")

        return {
            'status': 'success',
            'processed_count': len(processed),
            'failed_count': len(results) - len(processed),
            'results': results,
        }

    except Exception as e:
        logger.error(f"Pending emails task failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='services.tasks.email_tasks.process_single_email_task',
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_single_email_task(self, email_id: int) -> Dict[str, Any]:
    """
    Process a single email through the full Claude pipeline.

    This task:
    1. Fetches the email from the database
    2. Classifies with Claude
    3. Extracts entities
    4. Generates response draft
    5. Stores all results in database

    Args:
        email_id: Database ID of the email to process

    Returns:
        Dict with processing result
    """
    logger.info(f"Processing email id={email_id}")

    try:
        repos = get_repositories()
        email_repo = repos['email']
        entity_repo = repos['entity']
        response_repo = repos['response']

        # Get email from database
        email_record = email_repo.get_email_by_id(email_id)
        if not email_record:
            logger.error(f"Email {email_id} not found in database")
            return {
                'status': 'error',
                'email_id': email_id,
                'error': 'Email not found',
            }

        logger.info(
            f"Processing: {email_record.get('from_address')} | "
            f"Subject: {email_record.get('subject', '')[:50]}"
        )

        # Process with Claude
        result = _process_email_with_claude(
            email_record, email_repo, entity_repo, response_repo
        )

        return {
            'status': 'success',
            'email_id': email_id,
            'message_id': email_record.get('message_id'),
            **result,
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"Processing task hit soft time limit for email {email_id}")
        raise

    except Exception as e:
        logger.error(f"Failed to process email {email_id}: {e}")
        raise


def _process_email_with_claude(
    email_record: Dict[str, Any],
    email_repo,
    entity_repo,
    response_repo
) -> Dict[str, Any]:
    """
    Process an email through the full Claude pipeline.

    Args:
        email_record: Email record from database
        email_repo: EmailRepository instance
        entity_repo: EntityRepository instance
        response_repo: ResponseRepository instance

    Returns:
        Dict with classification, entities, quote, and response info
    """
    from services.claude import process_email_with_claude

    email_id = email_record['id']
    body = email_record.get('body', '')
    from_address = email_record.get('from_address', '')
    subject = email_record.get('subject', '')

    logger.info(f"Processing email {email_id} with Claude...")

    # Run the full Claude pipeline
    claude_result = process_email_with_claude(
        body=body,
        from_address=from_address,
        subject=subject,
        generate_response_flag=True
    )

    # Extract results
    classification = claude_result.get('classification', {})
    entities = claude_result.get('entities', [])
    quote = claude_result.get('quote')
    response_text = claude_result.get('response', '')

    intent = classification.get('intent', 'general_inquiry')
    confidence = classification.get('confidence', 0.0)

    # Update email with classification
    email_repo.update_intent(email_id, intent)
    logger.info(f"Email {email_id} classified as '{intent}' (confidence: {confidence:.2f})")

    # Store extracted entities
    entity_ids = []
    if entities:
        entity_ids = entity_repo.create_entities_batch(email_id, entities)
        logger.info(f"Stored {len(entity_ids)} entities for email {email_id}")

    # Store generated response
    response_id = None
    if response_text:
        response_id = response_repo.create_response(
            email_id=email_id,
            draft_content=response_text,
            status='draft'
        )
        logger.info(f"Stored response draft (id={response_id}) for email {email_id}")

        # Send Telegram notification for new draft
        try:
            from services.telegram.notifications import notify_new_draft
            notify_new_draft(response_id)
        except Exception as e:
            logger.warning(f"Failed to send Telegram notification for draft {response_id}: {e}")

    return {
        'classification': {
            'intent': intent,
            'confidence': confidence,
            'reasoning': classification.get('reasoning', ''),
        },
        'entities_count': len(entities),
        'entity_ids': entity_ids,
        'quote': quote,
        'response_id': response_id,
        'has_response': bool(response_text),
    }


# =============================================================================
# Email Sending Tasks
# =============================================================================

@shared_task(
    bind=True,
    name='services.tasks.email_tasks.send_approved_responses_task',
    max_retries=3,
    default_retry_delay=60,
)
def send_approved_responses_task(
    self,
    batch_size: int = 10,
    max_attempts: int = 3
) -> Dict[str, Any]:
    """
    Send all approved responses that haven't been sent yet.

    This task:
    1. Queries database for approved, unsent responses
    2. Sends each via Gmail API
    3. Updates database with send status

    Args:
        batch_size: Maximum number of responses to send per run
        max_attempts: Maximum send attempts before marking as failed

    Returns:
        Dict with send results (sent_count, failed_count, details)
    """
    from services.email_sender import EmailSender, ErrorType

    logger.info(
        f"Starting send approved responses task "
        f"(batch_size={batch_size}, max_attempts={max_attempts})"
    )

    try:
        repos = get_repositories()
        response_repo = repos['response']
        email_repo = repos['email']

        # Get approved responses ready for sending
        responses = response_repo.get_approved_for_sending(
            max_attempts=max_attempts,
            limit=batch_size
        )

        if not responses:
            logger.info("No approved responses to send")
            return {
                'status': 'success',
                'sent_count': 0,
                'failed_count': 0,
                'results': [],
            }

        logger.info(f"Found {len(responses)} approved responses to send")

        sender = EmailSender()
        results = []
        sent_count = 0
        failed_count = 0

        for resp in responses:
            response_id = resp['id']
            try:
                result = _send_single_response(
                    resp, sender, response_repo, email_repo, max_attempts
                )
                results.append(result)

                if result['status'] == 'sent':
                    sent_count += 1
                elif result['status'] == 'failed':
                    failed_count += 1

            except Exception as e:
                logger.error(f"Error sending response {response_id}: {e}")
                response_repo.record_send_error(response_id, str(e))
                results.append({
                    'response_id': response_id,
                    'status': 'error',
                    'error': str(e),
                })
                failed_count += 1

        logger.info(
            f"Send task complete: {sent_count} sent, "
            f"{failed_count} failed, {len(results)} total"
        )

        return {
            'status': 'success',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'results': results,
        }

    except Exception as e:
        logger.error(f"Send approved responses task failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='services.tasks.email_tasks.send_single_response_task',
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_single_response_task(
    self,
    response_id: int,
    max_attempts: int = 3
) -> Dict[str, Any]:
    """
    Send a single response immediately.

    Args:
        response_id: Database ID of the response to send
        max_attempts: Maximum send attempts before marking as failed

    Returns:
        Dict with send result
    """
    from services.email_sender import EmailSender

    logger.info(f"Sending single response id={response_id}")

    try:
        repos = get_repositories()
        response_repo = repos['response']
        email_repo = repos['email']

        # Get response with email data
        resp = response_repo.get_response_with_email(response_id)
        if not resp:
            logger.error(f"Response {response_id} not found")
            return {
                'status': 'error',
                'response_id': response_id,
                'error': 'Response not found',
            }

        # Check if response is approved
        if resp['status'] != 'approved':
            logger.warning(
                f"Response {response_id} is not approved (status={resp['status']})"
            )
            return {
                'status': 'error',
                'response_id': response_id,
                'error': f"Response not approved (status={resp['status']})",
            }

        sender = EmailSender()
        result = _send_single_response(
            resp, sender, response_repo, email_repo, max_attempts
        )

        return result

    except SoftTimeLimitExceeded:
        logger.warning(f"Send task hit soft time limit for response {response_id}")
        raise

    except Exception as e:
        logger.error(f"Failed to send response {response_id}: {e}")
        raise


def _send_single_response(
    resp: Dict[str, Any],
    sender,
    response_repo,
    email_repo,
    max_attempts: int
) -> Dict[str, Any]:
    """
    Send a single response and update database.

    Args:
        resp: Response data with email information
        sender: EmailSender instance
        response_repo: ResponseRepository instance
        email_repo: EmailRepository instance
        max_attempts: Maximum send attempts

    Returns:
        Dict with send result
    """
    from services.email_sender import ErrorType

    response_id = resp['id']
    email_id = resp['email_id']
    to_address = resp['from_address']
    subject = resp.get('subject', 'Response from EcoClean')
    body = resp['draft_content']

    # Extract threading information
    raw_headers = resp.get('raw_headers') or {}
    thread_id = raw_headers.get('thread_id')
    message_id = raw_headers.get('Message-ID') or resp.get('message_id')

    logger.info(
        f"Sending response {response_id} to {to_address} | "
        f"Thread: {thread_id or 'new'}"
    )

    # Send the email
    if thread_id and message_id:
        send_result = sender.send_reply(
            to=to_address,
            subject=subject,
            body=body,
            thread_id=thread_id,
            in_reply_to=message_id
        )
    else:
        send_result = sender.send_new_email(
            to=to_address,
            subject=subject,
            body=body
        )

    if send_result.success:
        # Mark response as sent
        response_repo.mark_sent_with_message_id(
            response_id,
            send_result.message_id
        )
        # Mark original email as responded
        email_repo.mark_responded(email_id)

        # Send Telegram notification for successful send
        try:
            from services.telegram.notifications import notify_send_success
            notify_send_success(response_id)
        except Exception as e:
            logger.warning(f"Failed to send Telegram success notification: {e}")

        # Queue calendar event creation
        try:
            from config.settings import settings as app_settings
            if app_settings.calendar.is_configured():
                from services.celery_app import app as celery_app
                celery_app.send_task(
                    'services.tasks.calendar_tasks.create_calendar_event_task',
                    args=[response_id],
                )
                logger.info(
                    f"Queued calendar event creation for response {response_id}"
                )
        except Exception as e:
            logger.warning(
                f"Failed to queue calendar event task for "
                f"response {response_id}: {e}"
            )

        return {
            'response_id': response_id,
            'status': 'sent',
            'message_id': send_result.message_id,
            'thread_id': send_result.thread_id,
        }

    else:
        # Handle error
        current_attempts = resp.get('send_attempts', 0) + 1

        if send_result.is_retryable and current_attempts < max_attempts:
            # Retryable error - record and leave for next batch
            response_repo.record_send_error(response_id, send_result.error)
            return {
                'response_id': response_id,
                'status': 'retry',
                'error': send_result.error,
                'attempts': current_attempts,
            }
        else:
            # Permanent failure or max attempts reached
            response_repo.mark_failed(response_id, send_result.error)

            # Send Telegram notification for failure
            try:
                from services.telegram.notifications import notify_send_failure
                notify_send_failure(response_id, send_result.error)
            except Exception as e:
                logger.warning(f"Failed to send Telegram failure notification: {e}")

            return {
                'response_id': response_id,
                'status': 'failed',
                'error': send_result.error,
                'attempts': current_attempts,
            }
