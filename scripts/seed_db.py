#!/usr/bin/env python3
"""
Database seeding script.

Runs the seed data migration (002_seed_data.sql) to populate
business configuration. Can be run multiple times safely due to
UPSERT operations.

Usage:
    python scripts/seed_db.py
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from database.connection import Database
from database.migrations.migrate import MigrationRunner
from database.schema import ConfigRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def seed_database() -> bool:
    """
    Run the seed data migration.

    Returns:
        True if seeding succeeded
    """
    runner = MigrationRunner()

    logger.info("Running seed data migration...")

    # Run specifically the seed data migration
    # The UPSERT queries make this safe to run multiple times
    seed_file = Path(__file__).parent.parent / "database" / "migrations" / "002_seed_data.sql"

    if not seed_file.exists():
        logger.error(f"Seed file not found: {seed_file}")
        return False

    if not runner.run_migration(seed_file):
        logger.error("Seeding failed!")
        return False

    logger.info("Seed data applied successfully!")
    return True


def verify_seed_data() -> None:
    """Verify that seed data was loaded correctly."""
    logger.info("Verifying seed data...")

    db = Database(settings.database.dsn)
    config_repo = ConfigRepository(db)

    try:
        # Check each config key
        configs = [
            "pricing_rules",
            "service_multipliers",
            "addon_services",
            "business_info",
            "brand_voice",
            "response_templates",
            "entity_extraction_rules",
        ]

        print("\nConfiguration status:")
        print("-" * 40)

        for key in configs:
            value = config_repo.get_config(key)
            if value:
                print(f"  ✓ {key}")
            else:
                print(f"  ✗ {key} (missing)")

        print("-" * 40)

        # Show some sample data
        pricing = config_repo.get_pricing_rules()
        if pricing:
            print("\nSample pricing (house):")
            house_pricing = pricing.get("house", {})
            print(f"  Base: ${house_pricing.get('base', 'N/A')}")
            print(f"  Per bedroom: ${house_pricing.get('per_bedroom', 'N/A')}")
            print(f"  Per bathroom: ${house_pricing.get('per_bathroom', 'N/A')}")

        business = config_repo.get_business_info()
        if business:
            print(f"\nBusiness name: {business.get('name', 'N/A')}")
            print(f"Email: {business.get('email', 'N/A')}")
            print(f"Phone: {business.get('phone', 'N/A')}")

    finally:
        db.close_all_connections()


def main():
    """Main entry point."""
    print("\n" + "=" * 50)
    print("  Cleaning Email Automation - Seed Database")
    print("=" * 50 + "\n")

    if not seed_database():
        return 1

    verify_seed_data()

    print("\n✓ Database seeding complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
