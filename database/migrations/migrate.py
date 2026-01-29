"""
Simple database migration runner.

Executes SQL migration files in order from the migrations directory.
Tracks applied migrations in a migrations_history table.

Usage:
    # Run all pending migrations
    python -m database.migrations.migrate

    # Run a specific migration
    python -m database.migrations.migrate --file 001_initial_schema.sql

    # Check migration status
    python -m database.migrations.migrate --status
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

import psycopg2
from psycopg2 import sql

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# SQL to create migrations tracking table
CREATE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS migrations_history (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# SQL to check if a migration has been applied
CHECK_MIGRATION = """
SELECT EXISTS(
    SELECT 1 FROM migrations_history WHERE filename = %s
) AS applied;
"""

# SQL to record a migration
RECORD_MIGRATION = """
INSERT INTO migrations_history (filename) VALUES (%s);
"""

# SQL to get all applied migrations
GET_APPLIED_MIGRATIONS = """
SELECT filename, applied_at FROM migrations_history ORDER BY applied_at;
"""


class MigrationRunner:
    """
    Runs SQL migration files against the database.

    Migrations are executed in alphabetical order by filename.
    Each migration is run in a transaction and recorded in the
    migrations_history table.
    """

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize the migration runner.

        Args:
            connection_string: PostgreSQL DSN. If not provided, uses settings.
        """
        self.connection_string = connection_string or settings.database.dsn
        self.migrations_dir = Path(__file__).parent

    def _get_connection(self):
        """Create a new database connection."""
        return psycopg2.connect(self.connection_string)

    def _ensure_migrations_table(self, conn) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        with conn.cursor() as cur:
            cur.execute(CREATE_MIGRATIONS_TABLE)
        conn.commit()
        logger.debug("Migrations history table ready")

    def _is_migration_applied(self, conn, filename: str) -> bool:
        """Check if a migration has already been applied."""
        with conn.cursor() as cur:
            cur.execute(CHECK_MIGRATION, (filename,))
            result = cur.fetchone()
            return result[0] if result else False

    def _record_migration(self, conn, filename: str) -> None:
        """Record that a migration has been applied."""
        with conn.cursor() as cur:
            cur.execute(RECORD_MIGRATION, (filename,))
        conn.commit()

    def get_migration_files(self) -> List[Path]:
        """
        Get sorted list of SQL migration files.

        Returns:
            List of paths to .sql files, sorted alphabetically
        """
        files = sorted(self.migrations_dir.glob('*.sql'))
        # Exclude any rollback files
        return [f for f in files if 'rollback' not in f.name.lower()]

    def get_applied_migrations(self) -> List[dict]:
        """
        Get list of applied migrations.

        Returns:
            List of dicts with filename and applied_at
        """
        conn = self._get_connection()
        try:
            self._ensure_migrations_table(conn)
            with conn.cursor() as cur:
                cur.execute(GET_APPLIED_MIGRATIONS)
                results = cur.fetchall()
                return [
                    {'filename': r[0], 'applied_at': r[1]}
                    for r in results
                ]
        finally:
            conn.close()

    def get_pending_migrations(self) -> List[Path]:
        """
        Get list of migrations that haven't been applied yet.

        Returns:
            List of paths to pending migration files
        """
        conn = self._get_connection()
        try:
            self._ensure_migrations_table(conn)
            all_files = self.get_migration_files()
            pending = []

            for file_path in all_files:
                if not self._is_migration_applied(conn, file_path.name):
                    pending.append(file_path)

            return pending
        finally:
            conn.close()

    def run_migration(self, file_path: Path) -> bool:
        """
        Execute a single migration file.

        Args:
            file_path: Path to the SQL migration file

        Returns:
            True if migration succeeded, False otherwise
        """
        logger.info(f"Running migration: {file_path.name}")

        with open(file_path, 'r') as f:
            sql_content = f.read()

        conn = self._get_connection()
        try:
            self._ensure_migrations_table(conn)

            # Check if already applied
            if self._is_migration_applied(conn, file_path.name):
                logger.info(f"Migration already applied: {file_path.name}")
                return True

            # Execute the migration
            with conn.cursor() as cur:
                cur.execute(sql_content)
            conn.commit()

            # Record the migration
            self._record_migration(conn, file_path.name)

            logger.info(f"Successfully applied: {file_path.name}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to run migration {file_path.name}: {e}")
            return False

        finally:
            conn.close()

    def run_all(self) -> bool:
        """
        Run all pending migrations.

        Returns:
            True if all migrations succeeded, False otherwise
        """
        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return True

        logger.info(f"Found {len(pending)} pending migration(s)")

        for file_path in pending:
            if not self.run_migration(file_path):
                logger.error(f"Migration failed at: {file_path.name}")
                return False

        logger.info(f"Successfully applied {len(pending)} migration(s)")
        return True

    def run_specific(self, filename: str) -> bool:
        """
        Run a specific migration file by name.

        Args:
            filename: Name of the migration file (e.g., '001_initial_schema.sql')

        Returns:
            True if migration succeeded, False otherwise
        """
        file_path = self.migrations_dir / filename

        if not file_path.exists():
            logger.error(f"Migration file not found: {filename}")
            return False

        return self.run_migration(file_path)

    def status(self) -> None:
        """Print the current migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        print("\n=== Migration Status ===\n")

        if applied:
            print("Applied migrations:")
            for m in applied:
                print(f"  ✓ {m['filename']} (applied at {m['applied_at']})")
        else:
            print("No migrations have been applied yet.")

        print()

        if pending:
            print("Pending migrations:")
            for p in pending:
                print(f"  ○ {p.name}")
        else:
            print("All migrations are up to date.")

        print()


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description='Database migration runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m database.migrations.migrate           # Run all pending migrations
  python -m database.migrations.migrate --status  # Show migration status
  python -m database.migrations.migrate --file 001_initial_schema.sql
        """
    )

    parser.add_argument(
        '--file', '-f',
        help='Run a specific migration file'
    )
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help='Show migration status'
    )
    parser.add_argument(
        '--dsn',
        help='Database connection string (overrides settings)'
    )

    args = parser.parse_args()

    runner = MigrationRunner(connection_string=args.dsn)

    if args.status:
        runner.status()
        return 0

    if args.file:
        success = runner.run_specific(args.file)
    else:
        success = runner.run_all()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
