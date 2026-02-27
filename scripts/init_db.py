#!/usr/bin/env python3
"""
Database initialization script.

Creates the database schema by running all migrations.
Should be run once after setting up Docker containers.

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --status  # Check migration status only
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from database.migrations.migrate import MigrationRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_database_connection() -> bool:
    """Verify database is accessible."""
    import psycopg2

    logger.info(f"Connecting to database at {settings.database.host}:{settings.database.port}")

    try:
        conn = psycopg2.connect(settings.database.dsn)
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            logger.info(f"Connected to: {version}")
        conn.close()
        return True
    except psycopg2.OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error("Make sure Docker containers are running: docker-compose up -d")
        return False


def initialize_database(status_only: bool = False) -> bool:
    """
    Run all database migrations.

    Args:
        status_only: If True, only show status without running migrations

    Returns:
        True if initialization succeeded
    """
    runner = MigrationRunner()

    if status_only:
        runner.status()
        return True

    logger.info("Starting database initialization...")

    # Run all migrations
    if not runner.run_all():
        logger.error("Database initialization failed!")
        return False

    logger.info("Database initialization complete!")
    runner.status()
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Initialize the database schema")
    parser.add_argument("--status", "-s", action="store_true", help="Show migration status only")

    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("  Cleaning Email Automation - Database Setup")
    print("=" * 50 + "\n")

    # Check connection first
    if not check_database_connection():
        return 1

    # Run migrations
    if not initialize_database(status_only=args.status):
        return 1

    print("\n✓ Database is ready!")
    print("\nNext steps:")
    print("  1. Run: python scripts/test_connection.py")
    print("  2. Run: python proof_of_concept/claude_test.py")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
