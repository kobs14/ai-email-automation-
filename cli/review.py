#!/usr/bin/env python3
"""
CLI tool for reviewing and managing email response drafts.

Usage:
    python -m cli.review list              # List pending drafts
    python -m cli.review show <id>         # View draft details
    python -m cli.review approve <id>      # Approve for sending
    python -m cli.review reject <id>       # Reject draft
    python -m cli.review edit <id>         # Edit then approve
    python -m cli.review failed            # List failed sends
    python -m cli.review retry <id>        # Retry failed send
"""

import argparse
import sys
import os
import tempfile
import subprocess
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_database
from database.schema import ResponseRepository, EmailRepository


def get_repos():
    """Get repository instances."""
    db = get_database()
    return {
        'response': ResponseRepository(db),
        'email': EmailRepository(db),
    }


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if dt is None:
        return 'N/A'
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ''
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'


def print_separator(char: str = '-', width: int = 80):
    """Print a separator line."""
    print(char * width)


def cmd_list(args):
    """List pending response drafts."""
    repos = get_repos()
    response_repo = repos['response']

    drafts = response_repo.get_pending_drafts()

    if not drafts:
        print("No pending drafts found.")
        return

    print(f"\n{'ID':>5} | {'From':^30} | {'Subject':^30} | {'Generated'}")
    print_separator()

    for draft in drafts:
        print(
            f"{draft['id']:>5} | "
            f"{truncate(draft['from_address'], 30):^30} | "
            f"{truncate(draft.get('subject', ''), 30):^30} | "
            f"{format_datetime(draft.get('generated_at'))}"
        )

    print_separator()
    print(f"Total: {len(drafts)} pending draft(s)")
    print("\nUse 'python -m cli.review show <id>' to view details")


def cmd_show(args):
    """Show details of a specific response draft."""
    repos = get_repos()
    response_repo = repos['response']

    response = response_repo.get_response_with_email(args.id)

    if not response:
        print(f"Error: Response with ID {args.id} not found.")
        sys.exit(1)

    print_separator('=')
    print(f"RESPONSE DRAFT #{response['id']}")
    print_separator('=')

    print(f"\nStatus: {response['status'].upper()}")
    print(f"Generated: {format_datetime(response.get('generated_at'))}")

    if response.get('approved_by'):
        print(f"Approved by: {response['approved_by']}")

    if response.get('sent_at'):
        print(f"Sent at: {format_datetime(response['sent_at'])}")

    if response.get('send_attempts', 0) > 0:
        print(f"Send attempts: {response['send_attempts']}")

    if response.get('send_error'):
        print(f"Last error: {response['send_error']}")

    print_separator()
    print("ORIGINAL EMAIL")
    print_separator()
    print(f"From: {response['from_address']}")
    print(f"Subject: {response.get('subject', '(No subject)')}")
    print(f"Intent: {response.get('intent', 'Unknown')}")
    print(f"\n{response.get('original_body', '')[:500]}")
    if len(response.get('original_body', '')) > 500:
        print("\n... (truncated)")

    print_separator()
    print("DRAFT RESPONSE")
    print_separator()
    print(response['draft_content'])

    print_separator()
    print("\nActions:")
    print(f"  Approve: python -m cli.review approve {args.id}")
    print(f"  Reject:  python -m cli.review reject {args.id}")
    print(f"  Edit:    python -m cli.review edit {args.id}")


def cmd_approve(args):
    """Approve a response draft for sending."""
    repos = get_repos()
    response_repo = repos['response']

    response = response_repo.get_response_by_id(args.id)

    if not response:
        print(f"Error: Response with ID {args.id} not found.")
        sys.exit(1)

    if response['status'] != 'draft':
        print(f"Error: Response is not in 'draft' status (current: {response['status']})")
        sys.exit(1)

    # Get approver name
    approver = args.approver or os.environ.get('USER', 'cli_user')

    success = response_repo.approve_response(args.id, approver)

    if success:
        print(f"Response #{args.id} approved by {approver}")
        print("It will be sent in the next scheduled send batch.")
        print("\nTo send immediately:")
        print(f"  from services.tasks.email_tasks import send_single_response_task")
        print(f"  send_single_response_task.delay({args.id})")
    else:
        print(f"Error: Failed to approve response #{args.id}")
        sys.exit(1)


def cmd_reject(args):
    """Reject a response draft."""
    repos = get_repos()
    response_repo = repos['response']

    response = response_repo.get_response_by_id(args.id)

    if not response:
        print(f"Error: Response with ID {args.id} not found.")
        sys.exit(1)

    if response['status'] not in ('draft', 'approved'):
        print(f"Error: Cannot reject response with status '{response['status']}'")
        sys.exit(1)

    success = response_repo.reject_response(args.id)

    if success:
        print(f"Response #{args.id} rejected")
    else:
        print(f"Error: Failed to reject response #{args.id}")
        sys.exit(1)


def cmd_edit(args):
    """Edit a response draft and optionally approve."""
    repos = get_repos()
    response_repo = repos['response']

    response = response_repo.get_response_with_email(args.id)

    if not response:
        print(f"Error: Response with ID {args.id} not found.")
        sys.exit(1)

    if response['status'] not in ('draft', 'approved', 'failed'):
        print(f"Error: Cannot edit response with status '{response['status']}'")
        sys.exit(1)

    # Get editor from environment or use default
    editor = os.environ.get('EDITOR', 'nano')

    # Create temporary file with response content
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.txt',
        delete=False
    ) as f:
        f.write(f"# Response Draft #{response['id']}\n")
        f.write(f"# To: {response['from_address']}\n")
        f.write(f"# Subject: {response.get('subject', '')}\n")
        f.write(f"# Lines starting with # will be ignored\n")
        f.write(f"# Save and close to continue\n")
        f.write("#\n")
        f.write(response['draft_content'])
        temp_path = f.name

    try:
        # Open editor
        subprocess.call([editor, temp_path])

        # Read edited content
        with open(temp_path, 'r') as f:
            lines = f.readlines()

        # Filter out comment lines
        edited_content = ''.join(
            line for line in lines
            if not line.startswith('#')
        ).strip()

        if not edited_content:
            print("Error: Content cannot be empty")
            sys.exit(1)

        # Check if content changed
        if edited_content == response['draft_content']:
            print("No changes made.")
        else:
            # Update content
            success = response_repo.update_content(args.id, edited_content)
            if success:
                print(f"Response #{args.id} updated")
            else:
                print(f"Error: Failed to update response #{args.id}")
                sys.exit(1)

        # Ask to approve
        if not args.no_approve:
            approve = input("\nApprove this response for sending? [y/N]: ")
            if approve.lower() in ('y', 'yes'):
                approver = args.approver or os.environ.get('USER', 'cli_user')
                # Reset to draft first if it was failed
                if response['status'] == 'failed':
                    response_repo.reset_for_retry(args.id)
                response_repo.approve_response(args.id, approver)
                print(f"Response #{args.id} approved by {approver}")

    finally:
        # Clean up temp file
        os.unlink(temp_path)


def cmd_failed(args):
    """List failed response sends."""
    repos = get_repos()
    response_repo = repos['response']

    failed = response_repo.get_failed_responses(limit=args.limit)

    if not failed:
        print("No failed responses found.")
        return

    print(f"\n{'ID':>5} | {'From':^25} | {'Attempts':^8} | {'Error'}")
    print_separator()

    for resp in failed:
        error = truncate(resp.get('send_error', ''), 30)
        print(
            f"{resp['id']:>5} | "
            f"{truncate(resp['from_address'], 25):^25} | "
            f"{resp.get('send_attempts', 0):^8} | "
            f"{error}"
        )

    print_separator()
    print(f"Total: {len(failed)} failed response(s)")
    print("\nUse 'python -m cli.review retry <id>' to retry sending")


def cmd_retry(args):
    """Retry sending a failed response."""
    repos = get_repos()
    response_repo = repos['response']

    response = response_repo.get_response_by_id(args.id)

    if not response:
        print(f"Error: Response with ID {args.id} not found.")
        sys.exit(1)

    if response['status'] != 'failed':
        print(f"Error: Response is not in 'failed' status (current: {response['status']})")
        sys.exit(1)

    success = response_repo.reset_for_retry(args.id)

    if success:
        print(f"Response #{args.id} reset for retry")
        print("It will be sent in the next scheduled send batch.")

        if args.immediate:
            print("\nSending immediately...")
            from services.tasks.email_tasks import send_single_response_task
            result = send_single_response_task(args.id)
            print(f"Result: {result}")
    else:
        print(f"Error: Failed to reset response #{args.id}")
        sys.exit(1)


def cmd_stats(args):
    """Show response statistics."""
    repos = get_repos()
    response_repo = repos['response']

    drafts = response_repo.count_pending_drafts()
    approved = len(response_repo.get_approved_unsent())
    failed = len(response_repo.get_failed_responses(limit=1000))

    print("\nResponse Statistics")
    print_separator()
    print(f"  Pending drafts:     {drafts}")
    print(f"  Approved (unsent):  {approved}")
    print(f"  Failed:             {failed}")
    print_separator()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Review and manage email response drafts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m cli.review list              # List pending drafts
    python -m cli.review show 5            # View draft #5
    python -m cli.review approve 5         # Approve draft #5
    python -m cli.review reject 5          # Reject draft #5
    python -m cli.review edit 5            # Edit draft #5
    python -m cli.review failed            # List failed sends
    python -m cli.review retry 5           # Retry sending #5
    python -m cli.review stats             # Show statistics
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # list command
    list_parser = subparsers.add_parser('list', help='List pending drafts')
    list_parser.set_defaults(func=cmd_list)

    # show command
    show_parser = subparsers.add_parser('show', help='Show draft details')
    show_parser.add_argument('id', type=int, help='Response ID')
    show_parser.set_defaults(func=cmd_show)

    # approve command
    approve_parser = subparsers.add_parser('approve', help='Approve draft for sending')
    approve_parser.add_argument('id', type=int, help='Response ID')
    approve_parser.add_argument(
        '--approver', '-a',
        help='Approver name (default: current user)'
    )
    approve_parser.set_defaults(func=cmd_approve)

    # reject command
    reject_parser = subparsers.add_parser('reject', help='Reject draft')
    reject_parser.add_argument('id', type=int, help='Response ID')
    reject_parser.set_defaults(func=cmd_reject)

    # edit command
    edit_parser = subparsers.add_parser('edit', help='Edit draft')
    edit_parser.add_argument('id', type=int, help='Response ID')
    edit_parser.add_argument(
        '--approver', '-a',
        help='Approver name (default: current user)'
    )
    edit_parser.add_argument(
        '--no-approve',
        action='store_true',
        help='Do not prompt to approve after editing'
    )
    edit_parser.set_defaults(func=cmd_edit)

    # failed command
    failed_parser = subparsers.add_parser('failed', help='List failed sends')
    failed_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=50,
        help='Maximum number of results'
    )
    failed_parser.set_defaults(func=cmd_failed)

    # retry command
    retry_parser = subparsers.add_parser('retry', help='Retry failed send')
    retry_parser.add_argument('id', type=int, help='Response ID')
    retry_parser.add_argument(
        '--immediate', '-i',
        action='store_true',
        help='Send immediately instead of waiting for batch'
    )
    retry_parser.set_defaults(func=cmd_retry)

    # stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize logging
    import logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(levelname)s: %(message)s'
    )

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
