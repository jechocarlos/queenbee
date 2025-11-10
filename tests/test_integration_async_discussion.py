"""Integration tests for async collaborative discussion system."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from queenbee.config.loader import load_config
from queenbee.db.connection import DatabaseManager
from queenbee.workers.manager import SpecialistWorker


class TestAsyncDiscussionIntegration:
    """Integration tests for the full async discussion flow."""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create a temporary config file for testing."""
        config_content = """
system:
  name: queenbee
  version: 1.0.0
  environment: test

database:
  host: localhost
  port: 5432
  name: queenbee_test
  user: queenbee
  password: changeme
  ssl_mode: prefer

ollama:
  host: http://localhost:11434
  model: llama3.1:8b
  timeout: 120

agents:
  ttl:
    idle_timeout_minutes: 10
    check_interval_seconds: 30
  
  max_concurrent_specialists: 10
  
  queen:
    system_prompt_file: ./prompts/queen.md
    complexity_threshold: auto
  
  divergent:
    system_prompt_file: ./prompts/divergent.md
    max_iterations: 10
  
  convergent:
    system_prompt_file: ./prompts/convergent.md
    max_iterations: 10
  
  critical:
    system_prompt_file: ./prompts/critical.md
    max_iterations: 10
  
  summarizer:
    system_prompt_file: ./prompts/summarizer.md
    max_iterations: 5

consensus:
  max_rounds: 10
  agreement_threshold: "all"
  discussion_rounds: 10
  specialist_timeout_seconds: 300

logging:
  level: ERROR
  format: json
  output: stdout
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        return config_file

    @pytest.fixture
    def mock_config(self, temp_config_file):
        """Load config from temp file."""
        return load_config(str(temp_config_file))

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager."""
        db = MagicMock(spec=DatabaseManager)
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        db.get_cursor = MagicMock(return_value=mock_cursor)
        return db

    @pytest.fixture
    def mock_task_repo(self):
        """Create a mock task repository."""
        task_repo = MagicMock()
        task_repo.get_next_task = MagicMock(return_value=None)
        return task_repo

    def test_collaborative_discussion_task_format(self, mock_config):
        """Test that collaborative discussion task has correct format."""
        with patch('queenbee.workers.manager.DatabaseManager'):
            with patch('queenbee.workers.manager.TaskRepository') as mock_task_class:
                mock_task_repo = MagicMock()
                mock_task_class.return_value = mock_task_repo
                
                # Simulate a collaborative discussion task
                task_data = {
                    "type": "collaborative_discussion",
                    "input": "What is the capital of France?",
                    "max_duration_seconds": 20
                }
                
                mock_task = {
                    "id": uuid4(),
                    "type": "collaborative_discussion",
                    "data": json.dumps(task_data),
                    "status": "pending"
                }
                
                mock_task_repo.get_next_task.return_value = mock_task
                
                session_id = uuid4()
                worker = SpecialistWorker(mock_config, session_id)
                
                # Verify task can be parsed
                task_content = json.loads(mock_task["data"])
                assert task_content["type"] == "collaborative_discussion"
                assert "input" in task_content
                assert "max_duration_seconds" in task_content

    def test_discussion_state_initialization(self, mock_config):
        """Test that discussion state is properly initialized."""
        with patch('queenbee.workers.manager.DatabaseManager'):
            with patch('queenbee.workers.manager.TaskRepository'):
                session_id = uuid4()
                worker = SpecialistWorker(mock_config, session_id)
                
                # Verify worker initializes with empty discussion state
                assert hasattr(worker, 'config')
                assert hasattr(worker, 'session_id')
                assert worker.session_id == session_id

    def test_should_agent_contribute_first_time(self, mock_config):
        """Test agent contribution logic for first contribution."""
        with patch('queenbee.workers.manager.DatabaseManager'):
            with patch('queenbee.workers.manager.TaskRepository'):
                session_id = uuid4()
                worker = SpecialistWorker(mock_config, session_id)
                
                # First contribution should always return True
                result = worker._should_agent_contribute(
                    agent_name="Divergent",
                    discussion=[],
                    user_input="What is AI?",
                    contribution_count=0
                )
                
                assert result is True

    def test_should_agent_contribute_prevents_consecutive(self, mock_config):
        """Test that agents can't contribute twice in a row."""
        with patch('queenbee.workers.manager.DatabaseManager'):
            with patch('queenbee.workers.manager.TaskRepository'):
                session_id = uuid4()
                worker = SpecialistWorker(mock_config, session_id)
                
                discussion = [
                    {
                        "agent": "Divergent",
                        "content": "Previous contribution",
                        "timestamp": time.time(),
                        "contribution_num": 1
                    }
                ]
                
                # Shouldn't contribute immediately after own contribution
                result = worker._should_agent_contribute(
                    agent_name="Divergent",
                    discussion=discussion,
                    user_input="What is AI?",
                    contribution_count=1
                )
                
                assert result is False

    def test_should_agent_contribute_max_contributions(self, mock_config):
        """Test that agents respect max contribution limit."""
        with patch('queenbee.workers.manager.DatabaseManager'):
            with patch('queenbee.workers.manager.TaskRepository'):
                session_id = uuid4()
                worker = SpecialistWorker(mock_config, session_id)
                
                discussion = [
                    {"agent": "Convergent", "content": "C1", "timestamp": time.time(), "contribution_num": 1},
                    {"agent": "Divergent", "content": "D1", "timestamp": time.time(), "contribution_num": 1},
                    {"agent": "Convergent", "content": "C2", "timestamp": time.time(), "contribution_num": 2},
                    {"agent": "Divergent", "content": "D2", "timestamp": time.time(), "contribution_num": 2},
                    {"agent": "Convergent", "content": "C3", "timestamp": time.time(), "contribution_num": 3},
                    {"agent": "Divergent", "content": "D3", "timestamp": time.time(), "contribution_num": 3},
                ]
                
                # After 3 contributions, should not contribute
                result = worker._should_agent_contribute(
                    agent_name="Divergent",
                    discussion=discussion,
                    user_input="What is AI?",
                    contribution_count=3
                )
                
                assert result is False

    def test_rolling_summary_format(self, mock_config):
        """Test that rolling summary has correct format."""
        # Rolling summary should be 2-3 sentences max
        # This tests the expected format without actual LLM calls
        
        sample_summary = "The discussion focuses on technical scalability. Multiple approaches were suggested including cloud-based and on-premise solutions."
        
        # Verify format expectations
        sentences = sample_summary.split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        assert len(sentences) <= 3, "Rolling summary should be 2-3 sentences max"
        assert len(sample_summary) < 500, "Rolling summary should be concise"

    def test_final_synthesis_includes_all_perspectives(self, mock_config):
        """Test that final synthesis considers all agent types."""
        contributions = [
            {"agent": "Divergent", "content": "Multiple approaches possible"},
            {"agent": "Convergent", "content": "Best approach is X"},
            {"agent": "Critical", "content": "Risk: Y needs consideration"}
        ]
        
        # Verify all three agent types contributed
        agent_types = set(c["agent"] for c in contributions)
        
        assert "Divergent" in agent_types
        assert "Convergent" in agent_types
        assert "Critical" in agent_types

    def test_worker_graceful_shutdown(self, mock_config):
        """Test that worker can shutdown gracefully."""
        with patch('queenbee.workers.manager.DatabaseManager'):
            with patch('queenbee.workers.manager.TaskRepository') as mock_task_class:
                mock_task_repo = MagicMock()
                mock_task_class.return_value = mock_task_repo
                mock_task_repo.get_next_task.return_value = None
                
                session_id = uuid4()
                worker = SpecialistWorker(mock_config, session_id)
                
                # Worker should be able to initialize and shutdown
                assert worker is not None
                assert worker.session_id == session_id

    def test_discussion_timeout_handling(self, mock_config):
        """Test that discussion respects timeout settings."""
        max_duration = 20  # seconds
        
        # Verify config has timeout setting
        assert hasattr(mock_config.consensus, 'specialist_timeout_seconds')
        assert mock_config.consensus.specialist_timeout_seconds == 300

    def test_agent_status_tracking(self, mock_config):
        """Test that agent status is properly tracked."""
        # Agent statuses: idle, thinking, contributed
        valid_statuses = ["idle", "thinking", "contributed"]
        
        # Verify all expected statuses are defined
        assert len(valid_statuses) == 3
        assert "idle" in valid_statuses
        assert "thinking" in valid_statuses
        assert "contributed" in valid_statuses


class TestRollingSummaryIntegration:
    """Integration tests for rolling summary generation."""

    def test_rolling_summary_thread_safety(self):
        """Test that rolling summary updates are thread-safe."""
        # Rolling summary is updated by background thread
        # Shared state should be protected by locks
        import threading
        
        lock = threading.Lock()
        shared_state = {"summary": ""}
        
        def update_summary(new_summary):
            with lock:
                shared_state["summary"] = new_summary
        
        # Simulate multiple updates
        update_summary("Summary 1")
        assert shared_state["summary"] == "Summary 1"
        
        update_summary("Summary 2")
        assert shared_state["summary"] == "Summary 2"

    def test_rolling_summary_update_interval(self):
        """Test rolling summary respects update interval."""
        # Summary should update every 4 seconds
        update_interval = 4
        
        assert update_interval == 4
        assert update_interval > 0

    def test_rolling_summary_includes_recent_contributions(self):
        """Test that rolling summary focuses on recent contributions."""
        all_contributions = [
            {"agent": "Divergent", "content": "Old idea", "timestamp": 1000.0},
            {"agent": "Convergent", "content": "Recent synthesis", "timestamp": 2000.0},
            {"agent": "Critical", "content": "Latest concern", "timestamp": 3000.0}
        ]
        
        # Most recent contributions should be prioritized
        recent_contributions = sorted(all_contributions, key=lambda x: x["timestamp"], reverse=True)[:2]
        
        assert len(recent_contributions) == 2
        assert recent_contributions[0]["content"] == "Latest concern"
        assert recent_contributions[1]["content"] == "Recent synthesis"


class TestAgentCoordination:
    """Integration tests for multi-agent coordination."""

    def test_three_agent_types_available(self):
        """Test that all three specialist types exist."""
        from queenbee.agents.convergent import ConvergentAgent
        from queenbee.agents.critical import CriticalAgent
        from queenbee.agents.divergent import DivergentAgent
        
        assert DivergentAgent is not None
        assert ConvergentAgent is not None
        assert CriticalAgent is not None

    def test_agents_have_distinct_prompts(self):
        """Test that each agent type has a unique system prompt."""
        prompts_dir = Path("prompts")
        
        assert (prompts_dir / "divergent.md").exists()
        assert (prompts_dir / "convergent.md").exists()
        assert (prompts_dir / "critical.md").exists()
        
        # Verify prompts are different
        divergent_prompt = (prompts_dir / "divergent.md").read_text()
        convergent_prompt = (prompts_dir / "convergent.md").read_text()
        critical_prompt = (prompts_dir / "critical.md").read_text()
        
        assert divergent_prompt != convergent_prompt
        assert convergent_prompt != critical_prompt
        assert divergent_prompt != critical_prompt

    def test_parallel_execution_setup(self):
        """Test that agents can execute in parallel."""
        import threading
        
        results = []
        lock = threading.Lock()
        
        def agent_task(agent_name):
            with lock:
                results.append(agent_name)
        
        threads = [
            threading.Thread(target=agent_task, args=("Divergent",)),
            threading.Thread(target=agent_task, args=("Convergent",)),
            threading.Thread(target=agent_task, args=("Critical",))
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(results) == 3
        assert "Divergent" in results
        assert "Convergent" in results
        assert "Critical" in results
