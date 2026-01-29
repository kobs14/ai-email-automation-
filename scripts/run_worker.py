#!/usr/bin/env python3
"""
Celery worker entry point script.

Usage:
    # Start worker only
    python scripts/run_worker.py

    # Start worker with beat scheduler
    python scripts/run_worker.py --beat

    # Start with specific queues
    python scripts/run_worker.py --queues email_fetch,email_process

    # Start with custom log level
    python scripts/run_worker.py --loglevel debug
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Run the Celery worker."""
    parser = argparse.ArgumentParser(description='Start Celery worker')
    parser.add_argument(
        '--beat',
        action='store_true',
        help='Enable beat scheduler for periodic tasks'
    )
    parser.add_argument(
        '--queues', '-Q',
        type=str,
        default='default,email_fetch,email_process',
        help='Comma-separated list of queues to consume from'
    )
    parser.add_argument(
        '--concurrency', '-c',
        type=int,
        default=2,
        help='Number of concurrent worker processes'
    )
    parser.add_argument(
        '--loglevel', '-l',
        type=str,
        default='info',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        help='Logging level'
    )
    parser.add_argument(
        '--pool', '-P',
        type=str,
        default='prefork',
        choices=['prefork', 'eventlet', 'gevent', 'solo'],
        help='Worker pool type'
    )

    args = parser.parse_args()

    # Import Celery app
    from services.celery_app import app

    # Build worker arguments
    worker_args = [
        'worker',
        f'--loglevel={args.loglevel}',
        f'--concurrency={args.concurrency}',
        f'--queues={args.queues}',
        f'--pool={args.pool}',
    ]

    if args.beat:
        worker_args.append('--beat')

    print(f"Starting Celery worker with args: {worker_args}")
    print(f"Queues: {args.queues}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Log level: {args.loglevel}")

    if args.beat:
        print("Beat scheduler: ENABLED")

    # Start the worker
    app.worker_main(argv=worker_args)


if __name__ == '__main__':
    main()
