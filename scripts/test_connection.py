#!/usr/bin/env python3
"""
Connection test script.

Verifies connectivity to PostgreSQL and Redis services.
Run this after starting Docker containers to ensure everything is working.

Usage:
    python scripts/test_connection.py
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_postgres_connection() -> bool:
    """Test PostgreSQL database connection."""
    from config.settings import settings
    import psycopg2

    print("\n--- PostgreSQL Connection Test ---")
    print(f"Host: {settings.database.host}")
    print(f"Port: {settings.database.port}")
    print(f"Database: {settings.database.database}")
    print(f"User: {settings.database.user}")

    try:
        conn = psycopg2.connect(settings.database.dsn)
        with conn.cursor() as cur:
            # Test basic query
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"Version: {version}")

            # Test if tables exist
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cur.fetchall()]

            if tables:
                print(f"Tables: {', '.join(tables)}")
            else:
                print("Tables: None (run migrations first)")

            # Test connection pool functionality
            cur.execute("SELECT 1 + 1 AS result;")
            result = cur.fetchone()[0]
            assert result == 2, "Basic query failed"

        conn.close()
        print("Status: ✓ Connected successfully")
        return True

    except psycopg2.OperationalError as e:
        print(f"Status: ✗ Connection failed")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"Status: ✗ Unexpected error")
        print(f"Error: {e}")
        return False


def test_redis_connection() -> bool:
    """Test Redis connection."""
    from config.settings import settings
    import redis

    print("\n--- Redis Connection Test ---")
    print(f"Host: {settings.redis.host}")
    print(f"Port: {settings.redis.port}")
    print(f"Database: {settings.redis.db}")

    try:
        r = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            password=settings.redis.password,
            decode_responses=True
        )

        # Test connection
        pong = r.ping()
        assert pong is True, "Ping failed"

        # Get server info
        info = r.info('server')
        print(f"Version: {info.get('redis_version', 'unknown')}")

        # Test basic operations
        test_key = '__connection_test__'
        r.set(test_key, 'hello')
        value = r.get(test_key)
        r.delete(test_key)

        assert value == 'hello', "Get/Set test failed"

        print("Status: ✓ Connected successfully")
        return True

    except redis.ConnectionError as e:
        print(f"Status: ✗ Connection failed")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"Status: ✗ Unexpected error")
        print(f"Error: {e}")
        return False


def test_database_pool() -> bool:
    """Test the database connection pool."""
    from config.settings import settings
    from database.connection import Database

    print("\n--- Connection Pool Test ---")

    try:
        db = Database(
            connection_string=settings.database.dsn,
            min_conn=2,
            max_conn=5
        )

        # Test using context manager
        with db.get_cursor() as cur:
            cur.execute("SELECT current_database(), current_user;")
            result = cur.fetchone()
            print(f"Database: {result['current_database']}")
            print(f"User: {result['current_user']}")

        # Test execute_query
        result = db.execute_query(
            "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = 'public';",
            fetch='one'
        )
        print(f"Public tables: {result['count']}")

        # Test is_connected
        assert db.is_connected(), "is_connected() returned False"

        db.close_all_connections()
        print("Status: ✓ Pool working correctly")
        return True

    except Exception as e:
        print(f"Status: ✗ Pool test failed")
        print(f"Error: {e}")
        return False


def test_repositories() -> bool:
    """Test the repository layer."""
    from config.settings import settings
    from database.connection import Database
    from database.schema import ConfigRepository

    print("\n--- Repository Layer Test ---")

    try:
        db = Database(settings.database.dsn)
        config_repo = ConfigRepository(db)

        # Test config retrieval (should work even without seed data)
        pricing = config_repo.get_pricing_rules()

        if pricing:
            print("Pricing rules: ✓ Found")
            print(f"  Property types: {list(pricing.keys())}")
        else:
            print("Pricing rules: Not found (run seed_db.py)")

        business_info = config_repo.get_business_info()
        if business_info:
            print(f"Business: {business_info.get('name', 'N/A')}")
        else:
            print("Business info: Not found (run seed_db.py)")

        db.close_all_connections()
        print("Status: ✓ Repositories working correctly")
        return True

    except Exception as e:
        print(f"Status: ✗ Repository test failed")
        print(f"Error: {e}")
        return False


def test_settings() -> bool:
    """Test settings loading."""
    from config.settings import settings

    print("\n--- Settings Test ---")

    try:
        print(f"Environment: {settings.app.env}")
        print(f"Debug mode: {settings.app.debug}")
        print(f"Log level: {settings.app.log_level}")

        # Check if Claude API key is configured
        if settings.claude.api_key and settings.claude.api_key != 'your_anthropic_api_key_here':
            print(f"Claude API: ✓ Configured (model: {settings.claude.model})")
        else:
            print("Claude API: ✗ Not configured (set ANTHROPIC_API_KEY in .env)")

        print("Status: ✓ Settings loaded correctly")
        return True

    except Exception as e:
        print(f"Status: ✗ Settings test failed")
        print(f"Error: {e}")
        return False


def main():
    """Run all connection tests."""
    print("\n" + "=" * 50)
    print("  Cleaning Email Automation - Connection Tests")
    print("=" * 50)

    results = {
        'settings': test_settings(),
        'postgres': test_postgres_connection(),
        'redis': test_redis_connection(),
        'pool': test_database_pool(),
        'repositories': test_repositories(),
    }

    # Summary
    print("\n" + "=" * 50)
    print("  Test Summary")
    print("=" * 50)

    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name.ljust(15)} {status}")
        if not passed:
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("\n✓ All tests passed!")
        print("\nNext steps:")
        print("  1. If tables are missing: python scripts/init_db.py")
        print("  2. Run proof of concept: python proof_of_concept/claude_test.py")
    else:
        print("\n✗ Some tests failed!")
        print("\nTroubleshooting:")
        print("  1. Make sure Docker is running: docker-compose up -d")
        print("  2. Check .env file configuration")
        print("  3. Wait a few seconds for containers to start")

    print()
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
