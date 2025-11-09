"""Database connection management."""

import logging
from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from queenbee.config.loader import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, config: DatabaseConfig):
        """Initialize database manager.

        Args:
            config: Database configuration.
        """
        self.config = config
        self._connection: Connection | None = None

    def connect(self) -> Connection:
        """Establish database connection.

        Returns:
            Database connection.
        """
        if self._connection is None or self._connection.closed:
            logger.info(f"Connecting to database: {self.config.host}:{self.config.port}/{self.config.name}")
            self._connection = psycopg.connect(
                self.config.connection_string,
                row_factory=dict_row,
                autocommit=False,
            )
        return self._connection

    def disconnect(self) -> None:
        """Close database connection."""
        if self._connection and not self._connection.closed:
            logger.info("Closing database connection")
            self._connection.close()
            self._connection = None

    @contextmanager
    def get_cursor(self) -> Generator:
        """Get a database cursor within a context manager.

        Yields:
            Database cursor.
        """
        conn = self.connect()
        with conn.cursor() as cursor:
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise

    def execute_script(self, script_path: str) -> None:
        """Execute SQL script file.

        Args:
            script_path: Path to SQL script.
        """
        with open(script_path, "r") as f:
            script = f.read()

        with self.get_cursor() as cursor:
            cursor.execute(script)
            logger.info(f"Executed script: {script_path}")

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()
