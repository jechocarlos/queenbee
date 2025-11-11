"""Tests for database models and repositories to increase coverage."""

import json
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from queenbee.db.connection import DatabaseManager
from queenbee.db.models import (AgentRepository, AgentStatus, AgentType,
                                ChatRepository, MessageRole, SessionRepository,
                                SessionStatus, TaskRepository, TaskStatus)


@pytest.fixture
def db_manager():
    """Create a mock database manager."""
    db = MagicMock(spec=DatabaseManager)
    return db


@pytest.fixture
def session_repo(db_manager):
    """Create a session repository."""
    return SessionRepository(db_manager)


@pytest.fixture
def agent_repo(db_manager):
    """Create an agent repository."""
    return AgentRepository(db_manager)


@pytest.fixture
def chat_repo(db_manager):
    """Create a chat repository."""
    return ChatRepository(db_manager)


@pytest.fixture
def task_repo(db_manager):
    """Create a task repository."""
    return TaskRepository(db_manager)


class TestSessionRepository:
    """Test session repository operations."""

    def test_create_session(self, session_repo):
        """Test creating a new session."""
        mock_cursor = MagicMock()
        session_id = uuid4()
        mock_cursor.fetchone.return_value = {"id": session_id}
        session_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = session_repo.create_session()
        
        assert result == session_id
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO sessions" in call_args[0]
        assert call_args[1] == (SessionStatus.ACTIVE.value,)

    def test_terminate_session(self, session_repo):
        """Test terminating a session."""
        mock_cursor = MagicMock()
        session_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        session_id = uuid4()
        
        session_repo.terminate_session(session_id)
        
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "UPDATE sessions" in call_args[0]
        assert SessionStatus.TERMINATED.value in call_args[1]
        assert session_id in call_args[1]

    def test_terminate_all_active_sessions(self, session_repo):
        """Test terminating all active sessions."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 3
        session_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        count = session_repo.terminate_all_active_sessions()
        
        assert count == 3
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "UPDATE sessions" in call_args[0]
        assert call_args[1] == (SessionStatus.TERMINATED.value, SessionStatus.ACTIVE.value)


class TestAgentRepository:
    """Test agent repository operations."""

    def test_create_agent_basic(self, agent_repo):
        """Test creating an agent without configuration."""
        mock_cursor = MagicMock()
        agent_id = uuid4()
        mock_cursor.fetchone.return_value = {"id": agent_id}
        agent_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        result = agent_repo.create_agent(
            agent_type=AgentType.DIVERGENT,
            session_id=session_id,
            system_prompt="Test prompt",
        )
        
        # Should return the agent_id that was generated (not from cursor)
        assert result is not None
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO agents" in call_args[0]
        # Verify None was passed for configuration
        assert call_args[1][4] is None

    def test_create_agent_with_configuration(self, agent_repo):
        """Test creating an agent with configuration."""
        mock_cursor = MagicMock()
        agent_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        config = {"temperature": 0.7, "max_tokens": 1000}
        result = agent_repo.create_agent(
            agent_type=AgentType.CONVERGENT,
            session_id=session_id,
            system_prompt="Test prompt",
            configuration=config,
        )
        
        assert result is not None
        call_args = mock_cursor.execute.call_args[0]
        # Verify configuration was JSON encoded
        config_arg = call_args[1][4]
        assert json.loads(config_arg) == config

    def test_update_agent_status(self, agent_repo):
        """Test updating agent status."""
        mock_cursor = MagicMock()
        agent_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        agent_id = uuid4()
        agent_repo.update_agent_status(agent_id, AgentStatus.IDLE)
        
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "UPDATE agents" in call_args[0]
        assert "status" in call_args[0]
        assert call_args[1] == (AgentStatus.IDLE.value, agent_id)

    def test_update_agent_activity(self, agent_repo):
        """Test updating agent activity timestamp."""
        mock_cursor = MagicMock()
        agent_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        agent_id = uuid4()
        agent_repo.update_agent_activity(agent_id)
        
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "UPDATE agents" in call_args[0]
        assert "last_activity_at" in call_args[0]
        assert call_args[1] == (agent_id,)

    def test_get_idle_agents(self, agent_repo):
        """Test getting idle agents."""
        mock_cursor = MagicMock()
        agent_id = uuid4()
        mock_cursor.fetchall.return_value = [{"id": agent_id, "status": "active"}]
        agent_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        idle_agents = agent_repo.get_idle_agents(idle_minutes=5)
        
        assert len(idle_agents) == 1
        assert idle_agents[0]["id"] == agent_id
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "SELECT * FROM agents" in call_args[0]
        assert call_args[1] == (AgentStatus.TERMINATED.value, 5)


class TestChatRepository:
    """Test chat repository operations."""

    def test_add_message_basic(self, chat_repo):
        """Test adding a basic message."""
        mock_cursor = MagicMock()
        message_id = 42
        mock_cursor.fetchone.return_value = {"id": message_id}
        chat_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        result = chat_repo.add_message(
            session_id=session_id,
            role=MessageRole.USER,
            content="Hello, world!",
        )
        
        assert result == message_id
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO chat_history" in call_args[0]
        assert call_args[1][0] == session_id
        assert call_args[1][2] == MessageRole.USER.value
        assert call_args[1][3] == "Hello, world!"

    def test_add_message_with_agent(self, chat_repo):
        """Test adding a message with agent ID."""
        mock_cursor = MagicMock()
        message_id = 43
        mock_cursor.fetchone.return_value = {"id": message_id}
        chat_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        agent_id = uuid4()
        result = chat_repo.add_message(
            session_id=session_id,
            role=MessageRole.QUEEN,
            content="Agent message",
            agent_id=agent_id,
        )
        
        assert result == message_id
        call_args = mock_cursor.execute.call_args[0]
        assert call_args[1][1] == agent_id

    def test_add_message_with_metadata(self, chat_repo):
        """Test adding a message with metadata."""
        mock_cursor = MagicMock()
        message_id = 44
        mock_cursor.fetchone.return_value = {"id": message_id}
        chat_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        metadata = {"tokens": 150, "model": "gpt-4"}
        result = chat_repo.add_message(
            session_id=session_id,
            role=MessageRole.SPECIALIST,
            content="Specialist response",
            metadata=metadata,
        )
        
        assert result == message_id
        call_args = mock_cursor.execute.call_args[0]
        metadata_arg = call_args[1][4]
        assert json.loads(metadata_arg) == metadata

    def test_get_session_history(self, chat_repo):
        """Test retrieving session history."""
        mock_cursor = MagicMock()
        messages = [
            {"id": 1, "content": "Message 1"},
            {"id": 2, "content": "Message 2"},
            {"id": 3, "content": "Message 3"},
        ]
        mock_cursor.fetchall.return_value = messages
        chat_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        history = chat_repo.get_session_history(session_id)
        
        assert len(history) == 3
        assert history[0]["content"] == "Message 1"
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "SELECT * FROM chat_history" in call_args[0]
        assert "LIMIT" not in call_args[0]

    def test_get_session_history_with_limit(self, chat_repo):
        """Test retrieving session history with limit."""
        mock_cursor = MagicMock()
        messages = [
            {"id": 1, "content": "Message 1"},
            {"id": 2, "content": "Message 2"},
            {"id": 3, "content": "Message 3"},
        ]
        mock_cursor.fetchall.return_value = messages
        chat_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        history = chat_repo.get_session_history(session_id, limit=3)
        
        assert len(history) == 3
        call_args = mock_cursor.execute.call_args[0]
        assert "LIMIT 3" in call_args[0]

    def test_get_session_history_empty(self, chat_repo):
        """Test retrieving history for session with no messages."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        chat_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        history = chat_repo.get_session_history(session_id)
        
        assert len(history) == 0


class TestTaskRepository:
    """Test task repository operations."""

    def test_create_task(self, task_repo):
        """Test creating a task."""
        mock_cursor = MagicMock()
        task_id = uuid4()
        mock_cursor.fetchone.return_value = {"id": task_id}
        task_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        queen_id = uuid4()
        agent_id = uuid4()
        
        result = task_repo.create_task(
            session_id=session_id,
            assigned_by=queen_id,
            assigned_to=[agent_id],
            description="Test task",
        )
        
        assert result == task_id
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO tasks" in call_args[0]
        assert call_args[1] == (session_id, queen_id, [agent_id], "Test task", TaskStatus.PENDING.value)

    def test_get_task(self, task_repo):
        """Test retrieving a task by ID."""
        mock_cursor = MagicMock()
        task_id = uuid4()
        mock_cursor.fetchone.return_value = {
            "id": task_id,
            "description": "Test task",
            "status": TaskStatus.PENDING.value
        }
        task_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        task = task_repo.get_task(task_id)
        
        assert task is not None
        assert task["id"] == task_id
        assert task["description"] == "Test task"
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "SELECT * FROM tasks WHERE id = %s" in call_args[0]

    def test_get_task_not_found(self, task_repo):
        """Test getting a non-existent task."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        task_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        fake_id = uuid4()
        task = task_repo.get_task(fake_id)
        
        assert task is None

    def test_get_pending_tasks(self, task_repo):
        """Test getting pending tasks without session filter."""
        mock_cursor = MagicMock()
        task_id1 = uuid4()
        task_id2 = uuid4()
        mock_cursor.fetchall.return_value = [
            {"id": task_id1, "description": "Task 1"},
            {"id": task_id2, "description": "Task 2"},
        ]
        task_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        pending = task_repo.get_pending_tasks()
        
        assert len(pending) == 2
        call_args = mock_cursor.execute.call_args[0]
        assert "WHERE status = %s ORDER BY created_at" in call_args[0]
        assert call_args[1] == (TaskStatus.PENDING.value,)

    def test_get_pending_tasks_with_session_filter(self, task_repo):
        """Test getting pending tasks filtered by session."""
        mock_cursor = MagicMock()
        task_id1 = uuid4()
        mock_cursor.fetchall.return_value = [{"id": task_id1}]
        task_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        pending = task_repo.get_pending_tasks(session_id=session_id)
        
        assert len(pending) == 1
        call_args = mock_cursor.execute.call_args[0]
        assert "WHERE status = %s AND session_id = %s" in call_args[0]
        assert call_args[1] == (TaskStatus.PENDING.value, session_id)

    def test_update_task_status_to_completed(self, task_repo):
        """Test updating task status to completed."""
        mock_cursor = MagicMock()
        task_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        task_id = uuid4()
        task_repo.update_task_status(task_id, TaskStatus.COMPLETED)
        
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "completed_at = NOW()" in call_args[0]
        assert call_args[1] == (TaskStatus.COMPLETED.value, task_id)

    def test_update_task_status_to_in_progress(self, task_repo):
        """Test updating task status to in progress."""
        mock_cursor = MagicMock()
        task_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        task_id = uuid4()
        task_repo.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "completed_at" not in call_args[0]
        assert call_args[1] == (TaskStatus.IN_PROGRESS.value, task_id)

    def test_set_task_result(self, task_repo):
        """Test setting task result."""
        mock_cursor = MagicMock()
        task_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        task_id = uuid4()
        result_data = json.dumps({"answer": "42", "confidence": 0.95})
        task_repo.set_task_result(task_id, result_data)
        
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "UPDATE tasks SET result = %s WHERE id = %s" in call_args[0]
        assert call_args[1] == (result_data, task_id)

    def test_get_session_tasks(self, task_repo):
        """Test getting all tasks for a session."""
        mock_cursor = MagicMock()
        task_id1 = uuid4()
        task_id2 = uuid4()
        task_id3 = uuid4()
        mock_cursor.fetchall.return_value = [
            {"id": task_id3, "description": "Third"},
            {"id": task_id2, "description": "Second"},
            {"id": task_id1, "description": "First"},
        ]
        task_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        tasks = task_repo.get_session_tasks(session_id)
        
        assert len(tasks) == 3
        call_args = mock_cursor.execute.call_args[0]
        assert "WHERE session_id = %s ORDER BY created_at DESC" in call_args[0]
        assert call_args[1] == (session_id,)

    def test_get_session_tasks_ordered_by_created_at(self, task_repo):
        """Test that session tasks are ordered by created_at DESC."""
        mock_cursor = MagicMock()
        task_id1 = uuid4()
        task_id2 = uuid4()
        task_id3 = uuid4()
        mock_cursor.fetchall.return_value = [
            {"id": task_id3, "description": "Third"},  # Most recent
            {"id": task_id2, "description": "Second"},
            {"id": task_id1, "description": "First"},  # Oldest
        ]
        task_repo.db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        session_id = uuid4()
        tasks = task_repo.get_session_tasks(session_id)
        
        # Verify order - most recent first
        assert tasks[0]["id"] == task_id3
        assert tasks[1]["id"] == task_id2
        assert tasks[2]["id"] == task_id1
