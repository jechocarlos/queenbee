"""Unit tests for worker manager."""

import json
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from queenbee.config.loader import Config
from queenbee.db.models import TaskStatus
from queenbee.workers.manager import SpecialistWorker


class TestSpecialistWorker:
    """Test specialist worker functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=Config)
        config.database = MagicMock()
        config.database.host = "localhost"
        config.database.port = 5432
        config.database.name = "test_db"
        config.database.user = "test_user"
        config.database.password = "test_pass"
        config.ollama = MagicMock()
        config.ollama.model = "llama2"
        config.agents = MagicMock()
        config.consensus = MagicMock()
        config.consensus.discussion_rounds = 3
        return config

    @pytest.fixture
    def session_id(self):
        """Create test session ID."""
        return uuid4()

    @pytest.fixture
    def worker(self, mock_config, session_id):
        """Create SpecialistWorker instance."""
        with patch('queenbee.workers.manager.DatabaseManager'):
            with patch('queenbee.workers.manager.TaskRepository'):
                worker = SpecialistWorker(mock_config, session_id)
                return worker

    def test_init_creates_worker_with_config(self, mock_config, session_id):
        """Test that initialization creates worker with proper configuration."""
        with patch('queenbee.workers.manager.DatabaseManager') as mock_db_class:
            with patch('queenbee.workers.manager.TaskRepository') as mock_task_class:
                worker = SpecialistWorker(mock_config, session_id)
                
                assert worker.config == mock_config
                assert worker.session_id == session_id
                mock_db_class.assert_called_once_with(mock_config.database)
                mock_task_class.assert_called_once()

    def test_process_task_updates_status_to_in_progress(self, worker):
        """Test that process_task updates status to IN_PROGRESS."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "description": json.dumps({
                "input": "Test question",
                "context": "",
                "max_rounds": 2
            }),
            "assigned_to": [uuid4(), uuid4(), uuid4()]
        }
        
        mock_task_repo = MagicMock()
        worker.task_repo = mock_task_repo
        
        with patch.object(worker, '_run_collaborative_discussion', return_value={"status": "completed"}):
            worker.process_task(task)
        
        # Should update to IN_PROGRESS first
        mock_task_repo.update_task_status.assert_any_call(task_id, TaskStatus.IN_PROGRESS)

    def test_process_task_updates_status_to_completed_on_success(self, worker):
        """Test that process_task updates status to COMPLETED on success."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "description": json.dumps({"input": "Test", "max_rounds": 1}),
            "assigned_to": [uuid4()]
        }
        
        mock_task_repo = MagicMock()
        worker.task_repo = mock_task_repo
        
        with patch.object(worker, '_run_collaborative_discussion', return_value={"status": "completed", "rounds": []}):
            worker.process_task(task)
        
        # Should update to COMPLETED at the end
        mock_task_repo.update_task_status.assert_any_call(task_id, TaskStatus.COMPLETED)

    def test_process_task_stores_result(self, worker):
        """Test that process_task stores the result."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "description": json.dumps({"input": "Test"}),
            "assigned_to": []
        }
        
        mock_task_repo = MagicMock()
        worker.task_repo = mock_task_repo
        
        result_data = {"status": "completed", "summary": "Done"}
        with patch.object(worker, '_run_collaborative_discussion', return_value=result_data):
            worker.process_task(task)
        
        # Should store result
        mock_task_repo.set_task_result.assert_called_once()
        call_args = mock_task_repo.set_task_result.call_args[0]
        assert call_args[0] == task_id
        stored_result = json.loads(call_args[1])
        assert stored_result["status"] == "completed"

    def test_process_task_handles_json_decode_error(self, worker):
        """Test that process_task handles non-JSON descriptions."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "description": "Plain text description",
            "assigned_to": []
        }
        
        mock_task_repo = MagicMock()
        worker.task_repo = mock_task_repo
        
        with patch.object(worker, '_run_collaborative_discussion', return_value={"status": "completed", "rounds": []}):
            worker.process_task(task)
        
        # Should still complete the task
        mock_task_repo.update_task_status.assert_any_call(task_id, TaskStatus.COMPLETED)

    def test_process_task_handles_exception(self, worker):
        """Test that process_task handles exceptions gracefully."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "description": json.dumps({"input": "Test"}),
            "assigned_to": []
        }
        
        mock_task_repo = MagicMock()
        worker.task_repo = mock_task_repo
        
        # Simulate an exception during discussion
        with patch.object(worker, '_run_collaborative_discussion', side_effect=RuntimeError("Test error")):
            worker.process_task(task)
        
        # Should update status to FAILED
        mock_task_repo.update_task_status.assert_any_call(task_id, TaskStatus.FAILED)
        
        # Should store error result
        mock_task_repo.set_task_result.assert_called_once()
        call_args = mock_task_repo.set_task_result.call_args[0]
        result = json.loads(call_args[1])
        assert "error" in result

    def test_process_task_parses_max_rounds_from_description(self, worker):
        """Test that process_task parses max_rounds from task description."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "description": json.dumps({
                "input": "Test",
                "max_rounds": 5
            }),
            "assigned_to": []
        }
        
        mock_task_repo = MagicMock()
        worker.task_repo = mock_task_repo
        
        with patch.object(worker, '_run_collaborative_discussion', return_value={"status": "completed", "rounds": []}) as mock_discuss:
            worker.process_task(task)
        
        # Should pass max_rounds to discussion
        call_args = mock_discuss.call_args[0]
        assert call_args[3] == 5  # max_rounds is 4th argument

    def test_process_task_uses_default_max_rounds(self, worker):
        """Test that process_task uses default max_rounds when not specified."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "description": json.dumps({"input": "Test"}),
            "assigned_to": []
        }
        
        mock_task_repo = MagicMock()
        worker.task_repo = mock_task_repo
        
        with patch.object(worker, '_run_collaborative_discussion', return_value={"status": "completed", "rounds": []}) as mock_discuss:
            worker.process_task(task)
        
        # Should use default max_rounds of 3
        call_args = mock_discuss.call_args[0]
        assert call_args[3] == 3
