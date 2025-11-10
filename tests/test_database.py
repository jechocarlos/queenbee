"""Unit tests for database models and repositories."""

from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from queenbee.db.models import (AgentType, ChatRepository, MessageRole,
                                TaskRepository, TaskStatus)


class TestTaskRepository:
    """Tests for TaskRepository."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager with context manager support."""
        db = MagicMock()
        # Mock get_cursor to return a context manager
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone = MagicMock(return_value={"id": uuid4()})
        mock_cursor.fetchall = MagicMock(return_value=[])
        db.get_cursor = MagicMock(return_value=mock_cursor)
        return db

    @pytest.fixture
    def task_repo(self, mock_db):
        """Create a TaskRepository instance."""
        return TaskRepository(mock_db)

    def test_create_task_returns_uuid(self, task_repo, mock_db, test_session_id):
        """Test that create_task returns a UUID."""
        # The cursor's fetchone returns the task id
        cursor = mock_db.get_cursor.return_value.__enter__.return_value
        test_id = uuid4()
        cursor.fetchone.return_value = {"id": test_id}
        
        task_id = task_repo.create_task(
            session_id=test_session_id,
            assigned_by=uuid4(),
            assigned_to=[uuid4()],
            description="Test task"
        )
        
        assert task_id is not None
        assert isinstance(task_id, UUID)
        assert task_id == test_id
        cursor.execute.assert_called_once()

    def test_get_pending_tasks_filters_by_session(self, task_repo, mock_db, test_session_id):
        """Test that get_pending_tasks filters by session."""
        cursor = mock_db.get_cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        
        task_repo.get_pending_tasks(test_session_id)
        
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args
        assert str(test_session_id) in str(call_args)

    def test_update_task_status_calls_execute(self, task_repo, mock_db):
        """Test that update_task_status executes query."""
        task_id = uuid4()
        cursor = mock_db.get_cursor.return_value.__enter__.return_value
        
        task_repo.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        
        cursor.execute.assert_called_once()

    def test_set_task_result_stores_result(self, task_repo, mock_db):
        """Test that set_task_result stores result."""
        task_id = uuid4()
        result = '{"status": "complete"}'
        cursor = mock_db.get_cursor.return_value.__enter__.return_value
        
        task_repo.set_task_result(task_id, result)
        
        cursor.execute.assert_called_once()


class TestChatRepository:
    """Test chat repository methods."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager with context manager support."""
        db = MagicMock()
        # Mock get_cursor to return a context manager
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone = MagicMock(return_value={"id": 123})  # Return proper message id
        mock_cursor.fetchall = MagicMock(return_value=[])
        db.get_cursor = MagicMock(return_value=mock_cursor)
        return db

    @pytest.fixture
    def chat_repo(self, mock_db):
        """Create a ChatRepository instance."""
        return ChatRepository(mock_db)

    def test_add_message_executes_insert(self, chat_repo, mock_db, test_session_id):
        """Test that add_message executes insert query."""
        cursor = mock_db.get_cursor.return_value.__enter__.return_value
        
        chat_repo.add_message(
            session_id=test_session_id,
            role=MessageRole.USER,
            content="Test message"
        )
        
        cursor.execute.assert_called_once()

    def test_add_message_with_agent_id(self, chat_repo, mock_db, test_session_id, test_agent_id):
        """Test adding message with agent_id."""
        cursor = mock_db.get_cursor.return_value.__enter__.return_value
        
        chat_repo.add_message(
            session_id=test_session_id,
            agent_id=test_agent_id,
            role=MessageRole.QUEEN,
            content="Test response"
        )
        
        cursor.execute.assert_called_once()

    def test_get_session_history_applies_limit(self, chat_repo, mock_db, test_session_id):
        """Test that get_session_history applies limit."""
        cursor = mock_db.get_cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        
        chat_repo.get_session_history(test_session_id, limit=5)
        
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args
        assert "5" in str(call_args) or "LIMIT" in str(call_args).upper()
        assert "5" in str(call_args) or "LIMIT" in str(call_args)


class TestEnums:
    """Tests for enum types."""

    def test_agent_type_values(self):
        """Test AgentType enum values."""
        assert AgentType.QUEEN.value == "queen"
        assert AgentType.DIVERGENT.value == "divergent"
        assert AgentType.CONVERGENT.value == "convergent"
        assert AgentType.CRITICAL.value == "critical"

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_message_role_values(self):
        """Test MessageRole enum values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.QUEEN.value == "queen"
        assert MessageRole.SPECIALIST.value == "specialist"
