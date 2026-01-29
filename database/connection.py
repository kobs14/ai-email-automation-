"""
Database connection management using psycopg2.

Provides thread-safe connection pooling and context managers for
database operations. All queries should use parameterized statements
to prevent SQL injection.
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union

import psycopg2
from psycopg2 import pool, extras, OperationalError
from psycopg2 import DatabaseError as PsycopgDatabaseError

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


class Database:
    """
    Manages PostgreSQL connection pool using psycopg2.

    Usage:
        db = Database(connection_string)

        # Using context manager (recommended)
        with db.get_cursor(commit=True) as cur:
            cur.execute("INSERT INTO table VALUES (%s)", (value,))

        # Using execute_query helper
        result = db.execute_query(
            "SELECT * FROM table WHERE id = %s",
            params=(1,),
            fetch='one'
        )

        # Cleanup
        db.close_all_connections()
    """

    def __init__(
        self,
        connection_string: str,
        min_conn: int = 2,
        max_conn: int = 10
    ):
        """
        Initialize the connection pool.

        Args:
            connection_string: PostgreSQL connection string or DSN
            min_conn: Minimum number of connections to maintain
            max_conn: Maximum number of connections allowed
        """
        self._connection_string = connection_string
        self._min_conn = min_conn
        self._max_conn = max_conn
        self._pool: Optional[pool.ThreadedConnectionPool] = None
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Create the connection pool."""
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=self._min_conn,
                maxconn=self._max_conn,
                dsn=self._connection_string
            )
            logger.info(
                f"Connection pool initialized (min={self._min_conn}, max={self._max_conn})"
            )
        except OperationalError as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise DatabaseError(f"Could not connect to database: {e}")

    def get_connection(self) -> psycopg2.extensions.connection:
        """
        Get a connection from the pool.

        Returns:
            A psycopg2 connection object

        Raises:
            DatabaseError: If pool is not initialized or connection fails
        """
        if self._pool is None:
            raise DatabaseError("Connection pool is not initialized")

        try:
            conn = self._pool.getconn()
            # Validate connection is still alive
            conn.isolation_level
            return conn
        except (OperationalError, PsycopgDatabaseError) as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise DatabaseError(f"Could not get database connection: {e}")

    def return_connection(self, conn: psycopg2.extensions.connection) -> None:
        """
        Return a connection to the pool.

        Args:
            conn: The connection to return
        """
        if self._pool is not None and conn is not None:
            self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, commit: bool = False):
        """
        Context manager for database operations.

        Automatically handles connection acquisition, cursor creation,
        commit/rollback, and connection return to pool.

        Args:
            commit: If True, commit transaction on successful completion

        Yields:
            A RealDictCursor for dictionary-style row access

        Usage:
            with db.get_cursor(commit=True) as cur:
                cur.execute("INSERT INTO emails (...) VALUES (%s, %s)", (val1, val2))
                cur.execute("SELECT * FROM emails WHERE id = %s", (id,))
                result = cur.fetchone()
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            yield cursor

            if commit:
                conn.commit()
                logger.debug("Transaction committed")
        except Exception as e:
            if conn is not None:
                conn.rollback()
                logger.warning(f"Transaction rolled back due to: {e}")
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                self.return_connection(conn)

    def execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch: Optional[str] = None
    ) -> Optional[Union[Dict, List[Dict]]]:
        """
        Execute a query and optionally return results.

        Args:
            query: SQL query string with %s placeholders
            params: Query parameters (tuple) - ALWAYS use this for user input
            fetch: 'one' for single row, 'all' for all rows, None for no results

        Returns:
            - If fetch='one': Single row as dict or None
            - If fetch='all': List of rows as dicts (may be empty)
            - If fetch=None: None (for INSERT/UPDATE/DELETE without RETURNING)

        Example:
            # Insert with RETURNING
            result = db.execute_query(
                "INSERT INTO emails (message_id, body) VALUES (%s, %s) RETURNING id",
                params=("msg123", "Hello"),
                fetch='one'
            )
            email_id = result['id']

            # Select multiple rows
            emails = db.execute_query(
                "SELECT * FROM emails WHERE status = %s LIMIT %s",
                params=("pending", 10),
                fetch='all'
            )
        """
        # Determine if this is a write operation
        is_write = query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))

        with self.get_cursor(commit=is_write) as cur:
            cur.execute(query, params)

            if fetch == 'one':
                return cur.fetchone()
            elif fetch == 'all':
                return cur.fetchall()
            return None

    def execute_many(
        self,
        query: str,
        params_list: List[tuple]
    ) -> int:
        """
        Execute a query multiple times with different parameters.

        Args:
            query: SQL query string with %s placeholders
            params_list: List of parameter tuples

        Returns:
            Number of rows affected

        Example:
            db.execute_many(
                "INSERT INTO entities (email_id, type, value) VALUES (%s, %s, %s)",
                [(1, "property_type", "house"), (1, "bedrooms", "3")]
            )
        """
        with self.get_cursor(commit=True) as cur:
            cur.executemany(query, params_list)
            return cur.rowcount

    def execute_values(
        self,
        query: str,
        values: List[tuple],
        template: Optional[str] = None,
        fetch: bool = False
    ) -> Optional[List[Dict]]:
        """
        Efficiently insert multiple rows using execute_values.

        This is faster than executemany for bulk inserts.

        Args:
            query: Base query (e.g., "INSERT INTO table (col1, col2) VALUES %s")
            values: List of value tuples
            template: Optional template for values (e.g., "(%s, %s, %s)")
            fetch: If True, return inserted rows (requires RETURNING clause)

        Returns:
            List of inserted rows if fetch=True, else None

        Example:
            rows = db.execute_values(
                "INSERT INTO entities (email_id, type, value) VALUES %s RETURNING id",
                [(1, "type1", "val1"), (1, "type2", "val2")],
                fetch=True
            )
        """
        with self.get_cursor(commit=True) as cur:
            if fetch:
                return extras.execute_values(
                    cur, query, values, template=template, fetch=True
                )
            else:
                extras.execute_values(cur, query, values, template=template)
                return None

    def close_all_connections(self) -> None:
        """
        Close all connections in the pool.

        Should be called during application shutdown.
        """
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None
            logger.info("All database connections closed")

    def is_connected(self) -> bool:
        """
        Check if database is accessible.

        Returns:
            True if a connection can be established
        """
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    def __enter__(self):
        """Support using Database as context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close all connections when exiting context."""
        self.close_all_connections()


# Singleton database instance (initialized on first use)
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """
    Get or create the singleton database instance.

    Uses settings from config/settings.py.

    Returns:
        Database: The configured database instance
    """
    global _db_instance

    if _db_instance is None:
        from config.settings import settings

        _db_instance = Database(
            connection_string=settings.database.dsn,
            min_conn=settings.database.min_connections,
            max_conn=settings.database.max_connections
        )

    return _db_instance


def close_database() -> None:
    """Close the singleton database instance."""
    global _db_instance

    if _db_instance is not None:
        _db_instance.close_all_connections()
        _db_instance = None
