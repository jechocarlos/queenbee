"""Unit tests for worker manager contribution logic."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from queenbee.workers.manager import SpecialistWorker


class TestContributionLogic:
    """Tests for _should_agent_contribute logic."""

    @pytest.fixture
    def worker(self, mock_config):
        """Create a SpecialistWorker instance."""
        session_id = uuid4()
        with patch('queenbee.workers.manager.DatabaseManager'):
            with patch('queenbee.workers.manager.TaskRepository'):
                worker = SpecialistWorker(mock_config, session_id)
                return worker

    @pytest.fixture
    def mock_config(self, temp_config_file):
        """Create a mock config."""
        from queenbee.config.loader import load_config
        return load_config(str(temp_config_file))

    def test_first_contribution_always_try(self, worker):
        """Test that agents always try to contribute first time."""
        result = worker._should_agent_contribute(
            agent_name="Divergent",
            discussion=[],
            user_input="Test question",
            contribution_count=0
        )
        assert result == True

    def test_dont_contribute_twice_in_row(self, worker):
        """Test that agents don't contribute twice in a row."""
        discussion = [
            {
                "agent": "Divergent",
                "content": "First contribution",
                "timestamp": 1699632000.0,
                "contribution_num": 1
            }
        ]
        
        result = worker._should_agent_contribute(
            agent_name="Divergent",
            discussion=discussion,
            user_input="Test question",
            contribution_count=1
        )
        assert result == False

    def test_can_contribute_after_another_agent(self, worker):
        """Test that agent can contribute after another agent."""
        discussion = [
            {
                "agent": "Divergent",
                "content": "First",
                "timestamp": 1699632000.0,
                "contribution_num": 1
            },
            {
                "agent": "Convergent",
                "content": "Second",
                "timestamp": 1699632002.0,
                "contribution_num": 1
            }
        ]
        
        result = worker._should_agent_contribute(
            agent_name="Divergent",
            discussion=discussion,
            user_input="Test question",
            contribution_count=1
        )
        assert result == True

    def test_max_three_contributions_per_agent(self, worker):
        """Test that agents are limited to 3 contributions."""
        discussion = []
        
        result = worker._should_agent_contribute(
            agent_name="Divergent",
            discussion=discussion,
            user_input="Test question",
            contribution_count=3
        )
        assert result == False

    def test_can_contribute_up_to_three_times(self, worker):
        """Test that agents can contribute up to 3 times."""
        discussion = [
            {
                "agent": "Convergent",
                "content": "Other agent",
                "timestamp": 1699632000.0,
                "contribution_num": 1
            }
        ]
        
        # Should be able to contribute 2nd and 3rd time
        for count in [1, 2]:
            result = worker._should_agent_contribute(
                agent_name="Divergent",
                discussion=discussion,
                user_input="Test question",
                contribution_count=count
            )
            assert result == True, f"Failed for contribution count {count}"

    def test_selective_contribution_long_discussion(self, worker):
        """Test that agents are more selective with long discussions."""
        # Create a discussion with 6+ contributions
        discussion = [
            {"agent": f"Agent{i}", "content": f"Content {i}", "timestamp": 1699632000.0 + i, "contribution_num": 1}
            for i in range(7)
        ]
        
        # Agent with 2+ contributions should not contribute again
        result = worker._should_agent_contribute(
            agent_name="Divergent",
            discussion=discussion,
            user_input="Test question",
            contribution_count=2
        )
        assert result == False

    def test_selective_contribution_allows_up_to_two(self, worker):
        """Test that selective mode allows up to 2 contributions."""
        discussion = [
            {"agent": f"Agent{i}", "content": f"Content {i}", "timestamp": 1699632000.0 + i, "contribution_num": 1}
            for i in range(7)
        ]
        
        # Agent with 1 contribution should still be able to contribute
        result = worker._should_agent_contribute(
            agent_name="Divergent",
            discussion=discussion,
            user_input="Test question",
            contribution_count=1
        )
        assert result == True


class TestDiscussionFormatting:
    """Tests for discussion formatting."""

    @pytest.fixture
    def worker(self, mock_config):
        """Create a SpecialistWorker instance."""
        session_id = uuid4()
        with patch('queenbee.workers.manager.DatabaseManager'):
            with patch('queenbee.workers.manager.TaskRepository'):
                worker = SpecialistWorker(mock_config, session_id)
                return worker

    @pytest.fixture
    def mock_config(self, temp_config_file):
        """Create a mock config."""
        from queenbee.config.loader import load_config
        return load_config(str(temp_config_file))

    def test_format_empty_discussion(self, worker):
        """Test formatting empty discussion."""
        result = worker._format_discussion_for_analysis([])
        assert result == ""

    def test_format_single_contribution(self, worker):
        """Test formatting single contribution."""
        discussion = [
            {
                "agent": "Divergent",
                "content": "Test content",
                "contribution_num": 1
            }
        ]
        
        result = worker._format_discussion_for_analysis(discussion)
        
        assert "--- Contribution 1 ---" in result
        assert "Agent: Divergent (contribution #1)" in result
        assert "Content: Test content" in result

    def test_format_multiple_contributions(self, worker):
        """Test formatting multiple contributions."""
        discussion = [
            {
                "agent": "Divergent",
                "content": "First",
                "contribution_num": 1
            },
            {
                "agent": "Convergent",
                "content": "Second",
                "contribution_num": 1
            },
            {
                "agent": "Critical",
                "content": "Third",
                "contribution_num": 1
            }
        ]
        
        result = worker._format_discussion_for_analysis(discussion)
        
        assert "--- Contribution 1 ---" in result
        assert "--- Contribution 2 ---" in result
        assert "--- Contribution 3 ---" in result
        assert "Agent: Divergent" in result
        assert "Agent: Convergent" in result
        assert "Agent: Critical" in result
        assert "Content: First" in result
        assert "Content: Second" in result
        assert "Content: Third" in result

    def test_format_preserves_order(self, worker):
        """Test that formatting preserves contribution order."""
        discussion = [
            {"agent": "A", "content": "First", "contribution_num": 1},
            {"agent": "B", "content": "Second", "contribution_num": 1},
            {"agent": "C", "content": "Third", "contribution_num": 1}
        ]
        
        result = worker._format_discussion_for_analysis(discussion)
        
        # Check that order is preserved
        first_pos = result.find("Content: First")
        second_pos = result.find("Content: Second")
        third_pos = result.find("Content: Third")
        
        assert first_pos < second_pos < third_pos
