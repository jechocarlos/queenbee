"""Unit tests for database connection management."""

from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from queenbee.config.loader import DatabaseConfig
from queenbee.db.connection import DatabaseManager


class TestDatabaseManager:
    """Test database manager functionality."""

    @pytest.fixture
    def db_config(self):
        """Create test database configuration."""
        return DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass",
            ssl_mode="prefer"
        )

    @pytest.fixture
    def db_manager(self, db_config):
        """Create DatabaseManager instance."""
        return DatabaseManager(db_config)

    def test_init_stores_config(self, db_config):
        """Test that initialization stores configuration."""
        manager = DatabaseManager(db_config)
        
        assert manager.config == db_config
        assert manager._connection is None

    @patch('queenbee.db.connection.psycopg.connect')
    def test_connect_creates_connection(self, mock_connect, db_manager):
        """Test that connect establishes database connection."""
        mock_connection = MagicMock()
        mock_connection.closed = False
        mock_connect.return_value = mock_connection
        
        result = db_manager.connect()
        
        assert result == mock_connection
        assert db_manager._connection == mock_connection
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        assert db_manager.config.connection_string in str(call_args)

    @patch('queenbee.db.connection.psycopg.connect')
    def test_connect_reuses_existing_connection(self, mock_connect, db_manager):
        """Test that connect reuses existing open connection."""
        mock_connection = MagicMock()
        mock_connection.closed = False
        mock_connect.return_value = mock_connection
        
        # First connect
        first = db_manager.connect()
        # Second connect
        second = db_manager.connect()
        
        assert first == second
        # Should only connect once
        mock_connect.assert_called_once()

    @patch('queenbee.db.connection.psycopg.connect')
    def test_connect_reconnects_if_closed(self, mock_connect, db_manager):
        """Test that connect reconnects if connection is closed."""
        mock_connection = MagicMock()
        mock_connection.closed = True
        mock_connect.return_value = mock_connection
        
        db_manager._connection = mock_connection
        
        # This should reconnect since connection is closed
        db_manager.connect()
        
        mock_connect.assert_called_once()

    @patch('queenbee.db.connection.psycopg.connect')
    def test_disconnect_closes_connection(self, mock_connect, db_manager):
        """Test that disconnect closes the connection."""
        mock_connection = MagicMock()
        mock_connection.closed = False
        mock_connect.return_value = mock_connection
        
        db_manager.connect()
        db_manager.disconnect()
        
        mock_connection.close.assert_called_once()
        assert db_manager._connection is None

    def test_disconnect_when_no_connection(self, db_manager):
        """Test that disconnect does nothing when no connection exists."""
        # Should not raise an error
        db_manager.disconnect()
        
        assert db_manager._connection is None

    @patch('queenbee.db.connection.psycopg.connect')
    def test_disconnect_when_already_closed(self, mock_connect, db_manager):
        """Test that disconnect handles already closed connection."""
        mock_connection = MagicMock()
        mock_connection.closed = True
        mock_connect.return_value = mock_connection
        
        db_manager._connection = mock_connection
        db_manager.disconnect()
        
        # Should not call close since already closed
        mock_connection.close.assert_not_called()

    @patch('queenbee.db.connection.psycopg.connect')
    def test_get_cursor_commits_on_success(self, mock_connect, db_manager):
        """Test that get_cursor commits transaction on success."""
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.closed = False
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_connect.return_value = mock_connection
        
        with db_manager.get_cursor() as cursor:
            assert cursor == mock_cursor
            cursor.execute("SELECT 1")
        
        mock_connection.commit.assert_called_once()
        mock_connection.rollback.assert_not_called()

    @patch('queenbee.db.connection.psycopg.connect')
    def test_get_cursor_rollback_on_error(self, mock_connect, db_manager):
        """Test that get_cursor rolls back transaction on error."""
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.closed = False
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_connect.return_value = mock_connection
        
        with pytest.raises(ValueError):
            with db_manager.get_cursor() as cursor:
                raise ValueError("Test error")
        
        mock_connection.rollback.assert_called_once()
        mock_connection.commit.assert_not_called()

    @patch('queenbee.db.connection.psycopg.connect')
    def test_execute_script_reads_and_executes_file(self, mock_connect, db_manager):
        """Test that execute_script reads and executes SQL file."""
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.closed = False
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_connect.return_value = mock_connection
        
        sql_content = "CREATE TABLE test (id INT);"
        
        with patch('builtins.open', mock_open(read_data=sql_content)):
            db_manager.execute_script("/path/to/script.sql")
        
        mock_cursor.execute.assert_called_once_with(sql_content)
        mock_connection.commit.assert_called_once()

    @patch('queenbee.db.connection.psycopg.connect')
    def test_context_manager_connects_and_disconnects(self, mock_connect, db_manager):
        """Test that context manager connects and disconnects properly."""
        mock_connection = MagicMock()
        mock_connection.closed = False
        mock_connect.return_value = mock_connection
        
        with db_manager as manager:
            assert manager == db_manager
            assert manager._connection == mock_connection
        
        mock_connection.close.assert_called_once()
        assert db_manager._connection is None

    @patch('queenbee.db.connection.psycopg.connect')
    def test_context_manager_disconnects_on_exception(self, mock_connect, db_manager):
        """Test that context manager disconnects even on exception."""
        mock_connection = MagicMock()
        mock_connection.closed = False
        mock_connect.return_value = mock_connection
        
        with pytest.raises(RuntimeError):
            with db_manager as manager:
                raise RuntimeError("Test error")
        
        mock_connection.close.assert_called_once()
        assert db_manager._connection is None
