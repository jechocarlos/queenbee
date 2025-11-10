"""Unit tests for session management."""

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from queenbee.session.manager import SessionManager


class TestSessionManager:
    """Test session manager functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager."""
        return MagicMock()

    @pytest.fixture
    def mock_session_repo(self):
        """Create a mock session repository."""
        repo = MagicMock()
        repo.create_session.return_value = uuid4()
        repo.terminate_all_active_sessions.return_value = 0
        repo.terminate_session.return_value = None
        return repo

    @pytest.fixture
    def session_manager(self, mock_db, mock_session_repo):
        """Create a SessionManager instance with mocked dependencies."""
        with patch('queenbee.session.manager.SessionRepository', return_value=mock_session_repo):
            manager = SessionManager(mock_db)
            return manager

    def test_init_creates_session_repo(self, mock_db):
        """Test that initialization creates session repository."""
        with patch('queenbee.session.manager.SessionRepository') as mock_repo_class:
            manager = SessionManager(mock_db)
            
            mock_repo_class.assert_called_once_with(mock_db)
            assert manager.db == mock_db
            assert manager._current_session_id is None

    def test_start_session_creates_new_session(self, session_manager, mock_session_repo):
        """Test that start_session creates a new session."""
        session_id = session_manager.start_session()
        
        # Should terminate orphaned sessions first
        mock_session_repo.terminate_all_active_sessions.assert_called_once()
        
        # Should create new session
        mock_session_repo.create_session.assert_called_once()
        
        # Should return session ID
        assert isinstance(session_id, UUID)
        assert session_manager._current_session_id == session_id

    def test_start_session_cleans_up_orphaned_sessions(self, session_manager, mock_session_repo):
        """Test that start_session cleans up orphaned sessions."""
        mock_session_repo.terminate_all_active_sessions.return_value = 3
        
        session_manager.start_session()
        
        mock_session_repo.terminate_all_active_sessions.assert_called_once()

    def test_end_session_terminates_current_session(self, session_manager, mock_session_repo):
        """Test that end_session terminates the current session."""
        # Start a session first
        session_id = session_manager.start_session()
        
        # End the session
        session_manager.end_session()
        
        # Should terminate the session
        mock_session_repo.terminate_session.assert_called_once_with(session_id)
        
        # Should clear current session ID
        assert session_manager._current_session_id is None

    def test_end_session_without_active_session(self, session_manager, mock_session_repo):
        """Test that end_session does nothing when no session is active."""
        # Don't start a session
        session_manager.end_session()
        
        # Should not call terminate_session
        mock_session_repo.terminate_session.assert_not_called()

    def test_current_session_id_property(self, session_manager):
        """Test current_session_id property."""
        # Initially None
        assert session_manager.current_session_id is None
        
        # After starting session
        session_id = session_manager.start_session()
        assert session_manager.current_session_id == session_id
        
        # After ending session
        session_manager.end_session()
        assert session_manager.current_session_id is None

    def test_context_manager_starts_session(self, session_manager, mock_session_repo):
        """Test that entering context manager starts a session."""
        with session_manager as manager:
            assert manager._current_session_id is not None
            mock_session_repo.create_session.assert_called_once()

    def test_context_manager_ends_session(self, session_manager, mock_session_repo):
        """Test that exiting context manager ends the session."""
        with session_manager as manager:
            session_id = manager._current_session_id
        
        # After exiting context
        mock_session_repo.terminate_session.assert_called_once_with(session_id)
        assert session_manager._current_session_id is None

    def test_context_manager_ends_session_on_exception(self, session_manager, mock_session_repo):
        """Test that context manager ends session even on exception."""
        session_id = None
        try:
            with session_manager as manager:
                session_id = manager._current_session_id
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still terminate session
        assert session_id is not None
        mock_session_repo.terminate_session.assert_called_once_with(session_id)
        assert session_manager._current_session_id is None
