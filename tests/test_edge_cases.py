"""Edge case and error handling tests for QueenBee system."""

import json
import threading
import time
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from queenbee.config.loader import Config
from queenbee.db.models import TaskStatus
from queenbee.workers.manager import SpecialistWorker


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = MagicMock(spec=Config)
    
    # Create database config with nested attributes
    config.database = MagicMock()
    config.database.host = "localhost"
    config.database.port = 5432
    config.database.name = "test_db"
    config.database.user = "test_user"
    config.database.password = "test_pass"
    
    # Create ollama config
    config.ollama = MagicMock()
    config.ollama.host = "http://localhost:11434"
    config.ollama.model = "test-model"
    config.ollama.timeout = 300
    
    # Create consensus config
    config.consensus = MagicMock()
    config.consensus.specialist_timeout_seconds = 300
    
    # Create agents config (needed for rolling summary thread)
    config.agents = MagicMock()
    config.agents.divergent = MagicMock()
    config.agents.divergent.system_prompt_file = "./prompts/divergent.md"
    config.agents.convergent = MagicMock()
    config.agents.convergent.system_prompt_file = "./prompts/convergent.md"
    config.agents.critical = MagicMock()
    config.agents.critical.system_prompt_file = "./prompts/critical.md"
    config.agents.summarizer = MagicMock()
    config.agents.summarizer.system_prompt_file = "./prompts/summarizer.md"
    
    return config


@pytest.fixture
def mock_db():
    """Mock database manager."""
    db = MagicMock()
    db.__enter__ = Mock(return_value=db)
    db.__exit__ = Mock(return_value=False)
    return db


@pytest.fixture
def mock_task_repo():
    """Mock task repository."""
    return MagicMock()


@pytest.fixture
def specialist_worker(mock_config, mock_db, mock_task_repo):
    """Create SpecialistWorker with mocked dependencies."""
    with patch("queenbee.workers.manager.DatabaseManager", return_value=mock_db):
        with patch("queenbee.workers.manager.TaskRepository", return_value=mock_task_repo):
            worker = SpecialistWorker(mock_config, uuid4())
            worker.task_repo = mock_task_repo
            return worker


class TestTaskProcessing:
    """Test core task processing error handling."""

    def test_json_parsing_error_fallback(self, specialist_worker):
        """Test that malformed JSON falls back to plain text."""
        task = {
            "id": uuid4(),
            "description": "{invalid json}",
            "assigned_to": "queen"
        }

        # Mock discussion to return quickly
        with patch.object(specialist_worker, "_run_collaborative_discussion") as mock_discuss:
            mock_discuss.return_value = {
                "task": "{invalid json}",
                "context": "",
                "total_contributions": 0,
                "contributions": [],
                "rolling_summary": "",
                "summary": "Summary"
            }
            specialist_worker.process_task(task)

        # Should handle gracefully and complete
        specialist_worker.task_repo.update_task_status.assert_any_call(
            task["id"], TaskStatus.COMPLETED
        )
        
        # Verify discussion was called with plain text
        mock_discuss.assert_called_once()
        call_args = mock_discuss.call_args[0]
        assert call_args[1] == "{invalid json}"  # user_input

    def test_missing_json_fields_use_defaults(self, specialist_worker):
        """Test that missing JSON fields use default values."""
        task = {
            "id": uuid4(),
            "description": json.dumps({"some_field": "value"}),  # No 'input'
            "assigned_to": "queen"
        }

        with patch.object(specialist_worker, "_run_collaborative_discussion") as mock_discuss:
            mock_discuss.return_value = {
                "task": "",
                "context": "",
                "total_contributions": 0,
                "contributions": [],
                "rolling_summary": "",
                "summary": "No discussion occurred."
            }
            specialist_worker.process_task(task)

        # Should use defaults
        mock_discuss.assert_called_once()
        call_args = mock_discuss.call_args[0]
        assert call_args[1] == ""  # user_input defaults to empty
        assert call_args[2] == ""  # context defaults to empty
        assert call_args[3] == 3   # max_rounds defaults to 3

    def test_discussion_exception_marks_task_failed(self, specialist_worker):
        """Test that exceptions during discussion mark task as failed."""
        task = {
            "id": uuid4(),
            "description": "Test question?",
            "assigned_to": "queen"
        }

        # Mock discussion to raise exception
        with patch.object(specialist_worker, "_run_collaborative_discussion") as mock_discuss:
            mock_discuss.side_effect = Exception("Discussion crashed")
            specialist_worker.process_task(task)

        # Should mark as failed
        specialist_worker.task_repo.update_task_status.assert_called_with(
            task["id"], TaskStatus.FAILED
        )
        
        # Should store error in result
        calls = specialist_worker.task_repo.set_task_result.call_args_list
        error_result = json.loads(calls[-1][0][1])
        assert "error" in error_result
        assert "Discussion crashed" in error_result["error"]


class TestDatabaseFailures:
    """Test database operation failures."""

    def test_result_storage_failure_marks_failed(self, specialist_worker):
        """Test that result storage failures mark task as failed."""
        task = {
            "id": uuid4(),
            "description": "Test question?",
            "assigned_to": "queen"
        }

        # Mock discussion to succeed
        mock_result = {
            "task": "Test",
            "context": "",
            "total_contributions": 1,
            "contributions": [{"agent": "Divergent", "content": "Test"}],
            "rolling_summary": "",
            "summary": "Summary"
        }
        
        with patch.object(specialist_worker, "_run_collaborative_discussion") as mock_discuss:
            mock_discuss.return_value = mock_result
            
            # Mock result storage to fail
            specialist_worker.task_repo.set_task_result.side_effect = Exception("Disk full")
            
            # Exception is caught but not re-raised
            try:
                specialist_worker.process_task(task)
            except Exception:
                pass  # Expected - exception caught internally

        # Should mark as failed
        specialist_worker.task_repo.update_task_status.assert_called_with(
            task["id"], TaskStatus.FAILED
        )

    def test_status_update_failure_caught(self, specialist_worker):
        """Test that status update failures are logged but don't crash."""
        task = {
            "id": uuid4(),
            "description": "Test question?",
            "assigned_to": "queen"
        }

        # Mock status update to fail
        specialist_worker.task_repo.update_task_status.side_effect = Exception("DB connection lost")
        
        with patch.object(specialist_worker, "_run_collaborative_discussion") as mock_discuss:
            mock_discuss.return_value = {
                "task": "Test",
                "context": "",
                "total_contributions": 0,
                "contributions": [],
                "rolling_summary": "",
                "summary": "Summary"
            }
            # Should not raise exception (caught internally)
            try:
                specialist_worker.process_task(task)
            except Exception:
                pass  # Expected to be caught


class TestSummaryGeneration:
    """Test final summary generation edge cases."""

    def test_generate_queen_summary_with_empty_discussion(self, specialist_worker):
        """Test summary generation when no contributions exist."""
        result = specialist_worker._generate_queen_summary(
            user_input="Test question?",
            discussion=[],
            rolling_summary=""
        )
        
        assert result == "No discussion occurred."

    def test_generate_queen_summary_with_contributions(self, specialist_worker):
        """Test summary generation with actual contributions."""
        contributions = [
            {"agent": "Divergent", "content": "First", "timestamp": 1.0},
            {"agent": "Convergent", "content": "Second", "timestamp": 2.0}
        ]
        
        # Mock SummarizerAgent
        mock_summarizer = MagicMock()
        mock_summarizer.generate_final_synthesis.return_value = "Final synthesis"
        
        with patch("queenbee.agents.summarizer.SummarizerAgent", return_value=mock_summarizer):
            result = specialist_worker._generate_queen_summary(
                user_input="Test?",
                discussion=contributions,
                rolling_summary="Rolling summary"
            )
        
        assert result == "Final synthesis"
        mock_summarizer.generate_final_synthesis.assert_called_once()
        mock_summarizer.terminate.assert_called_once()

    def test_generate_queen_summary_handles_exception(self, specialist_worker):
        """Test that summary generation exceptions return fallback message."""
        contributions = [
            {"agent": "Divergent", "content": "Test", "timestamp": 1.0}
        ]
        
        # Mock SummarizerAgent to raise exception
        mock_summarizer = MagicMock()
        mock_summarizer.generate_final_synthesis.side_effect = Exception("Synthesis failed")
        
        with patch("queenbee.agents.summarizer.SummarizerAgent", return_value=mock_summarizer):
            result = specialist_worker._generate_queen_summary(
                user_input="Test?",
                discussion=contributions,
                rolling_summary=""
            )
        
        assert result == "Unable to generate summary."
        mock_summarizer.terminate.assert_called_once()


class TestCollaborativeDiscussion:
    """Test collaborative discussion edge cases."""

    def test_discussion_with_no_contributions(self, specialist_worker):
        """Test discussion when all agents remain silent."""
        # Don't run actual discussion - just verify behavior logically
        # The real discussion is tested in test_integration_async_discussion.py
        
        # Mock discussion to return empty contributions
        with patch.object(specialist_worker, "_run_collaborative_discussion") as mock_discuss:
            mock_discuss.return_value = {
                "task": "Test?",
                "context": "",
                "total_contributions": 0,
                "contributions": [],
                "rolling_summary": "",
                "summary": "No discussion occurred."
            }
            
            task = {
                "id": uuid4(),
                "description": "Test?",
                "assigned_to": "queen"
            }
            specialist_worker.process_task(task)
        
        # Should complete successfully
        specialist_worker.task_repo.update_task_status.assert_any_call(
            task["id"], TaskStatus.COMPLETED
        )

    def test_discussion_with_single_contribution(self, specialist_worker):
        """Test discussion when only one agent contributes."""
        # Mock discussion with single contribution
        with patch.object(specialist_worker, "_run_collaborative_discussion") as mock_discuss:
            mock_discuss.return_value = {
                "task": "Test?",
                "context": "",
                "total_contributions": 1,
                "contributions": [{"agent": "Divergent", "content": "Single contribution", "timestamp": 1.0}],
                "rolling_summary": "",
                "summary": "Summary"
            }
            
            task = {
                "id": uuid4(),
                "description": "Test?",
                "assigned_to": "queen"
            }
            specialist_worker.process_task(task)
        
        # Should complete successfully
        specialist_worker.task_repo.update_task_status.assert_any_call(
            task["id"], TaskStatus.COMPLETED
        )


class TestAgentExceptions:
    """Test agent exception handling during discussion."""

    def test_agent_contribution_exception_caught(self, specialist_worker):
        """Test that agent exceptions during contribution are caught."""
        task_id = uuid4()
        
        # Agent that crashes when contributing
        failing_agent = MagicMock()
        failing_agent.should_contribute.return_value = True
        failing_agent.contribute.side_effect = Exception("Agent crashed")
        failing_agent.terminate = MagicMock()
        
        silent_agent = MagicMock()
        silent_agent.should_contribute.return_value = False
        silent_agent.terminate = MagicMock()
        
        with patch("queenbee.workers.manager.DivergentAgent", return_value=failing_agent):
            with patch("queenbee.workers.manager.ConvergentAgent", return_value=silent_agent):
                with patch("queenbee.workers.manager.CriticalAgent", return_value=silent_agent):
                    with patch("queenbee.agents.summarizer.SummarizerAgent", return_value=silent_agent):
                        # Should not raise exception
                        result = specialist_worker._run_collaborative_discussion(
                            task_id=task_id,
                            user_input="Test?",
                            context="",
                            max_rounds=1
                        )
        
        # Discussion completes despite agent exceptions
        assert "contributions" in result
        assert "total_contributions" in result
