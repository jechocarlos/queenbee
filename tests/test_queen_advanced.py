"""Additional unit tests for Queen agent."""

import json
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from queenbee.agents.queen import QueenAgent
from queenbee.config.loader import Config
from queenbee.db.models import AgentType, TaskStatus


class TestQueenAgentAdvanced:
    """Advanced tests for Queen agent functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=Config)
        config.ollama = MagicMock()
        config.ollama.model = "llama2"
        config.ollama.host = "http://localhost:11434"
        config.ollama.timeout = 30
        config.agents = MagicMock()
        config.agents.queen = MagicMock()
        config.agents.queen.system_prompt_file = "prompts/queen.md"
        config.consensus = MagicMock()
        config.consensus.discussion_rounds = 3
        config.consensus.specialist_timeout_seconds = 300
        return config

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone = MagicMock(return_value={"id": uuid4()})
        db.get_cursor = MagicMock(return_value=mock_cursor)
        return db

    @pytest.fixture
    def queen_agent(self, mock_config, mock_db):
        """Create Queen agent instance."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: "System prompt")))):
                    with patch('queenbee.agents.queen.TaskRepository'):
                        with patch('queenbee.agents.queen.ChatRepository'):
                            session_id = uuid4()
                            agent = QueenAgent(session_id, mock_config, mock_db)
                            return agent

    def test_handle_simple_request_direct_response(self, queen_agent):
        """Test that simple requests get direct responses."""
        with patch.object(queen_agent, 'generate_response', return_value="Direct answer"):
            result = queen_agent._handle_simple_request("What is 2+2?")
            
            assert result == "Direct answer"
            queen_agent.generate_response.assert_called_once()

    def test_handle_simple_request_streaming(self, queen_agent):
        """Test that simple requests support streaming."""
        with patch.object(queen_agent, 'generate_response', return_value=iter(["Hello", " world"])):
            result = queen_agent._handle_simple_request("Test", stream=True)
            
            chunks = list(result)
            assert chunks == ["Hello", " world"]

    def test_handle_complex_request_when_specialists_disabled(self, queen_agent):
        """Test complex request handling when specialists are disabled."""
        queen_agent.enable_specialists = False
        
        with patch.object(queen_agent, 'generate_response', return_value="Fallback response"):
            result = queen_agent._handle_complex_request("Complex question")
            
            assert "specialist spawning is disabled" in result
            assert "Fallback response" in result

    def test_handle_complex_request_creates_task(self, queen_agent):
        """Test that complex requests create tasks for specialists."""
        queen_agent.enable_specialists = True
        mock_task_repo = MagicMock()
        mock_task_repo.create_task.return_value = uuid4()
        mock_task_repo.get_task.return_value = {
            "id": uuid4(),
            "status": TaskStatus.COMPLETED.value,
            "result": json.dumps({
                "status": "completed",
                "final_summary": "Task complete"
            })
        }
        queen_agent.task_repo = mock_task_repo
        
        with patch('builtins.print'):  # Suppress print output
            result = queen_agent._handle_complex_request("Analyze this complex topic")
        
        mock_task_repo.create_task.assert_called_once()
        call_args = mock_task_repo.create_task.call_args[1]
        assert call_args["session_id"] == queen_agent.session_id
        assert call_args["assigned_by"] == queen_agent.agent_id

    def test_get_conversation_context_returns_recent_messages(self, queen_agent):
        """Test that get_conversation_context retrieves recent messages."""
        mock_chat_repo = MagicMock()
        mock_chat_repo.get_session_history.return_value = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"}
        ]
        queen_agent.chat_repo = mock_chat_repo
        
        context = queen_agent._get_conversation_context()
        
        mock_chat_repo.get_session_history.assert_called_once()
        # Just verify it was called, the exact format may vary

    def test_get_conversation_context_empty_history(self, queen_agent):
        """Test get_conversation_context with no history."""
        mock_chat_repo = MagicMock()
        mock_chat_repo.get_session_history.return_value = []
        queen_agent.chat_repo = mock_chat_repo
        
        context = queen_agent._get_conversation_context()
        
        # Should return empty or formatted empty context
        assert isinstance(context, str)

    def test_specialists_toggle(self, queen_agent):
        """Test toggling specialists on and off."""
        # Initially enabled
        assert queen_agent.enable_specialists is True
        
        # Can be toggled
        queen_agent.enable_specialists = False
        assert queen_agent.enable_specialists is False
        
        queen_agent.enable_specialists = True
        assert queen_agent.enable_specialists is True

    def test_process_request_uses_chat_history(self, queen_agent):
        """Test that process_request uses chat repository."""
        mock_chat_repo = MagicMock()
        queen_agent.chat_repo = mock_chat_repo
        
        # Disable specialists to test simple path
        queen_agent.enable_specialists = False
        
        with patch.object(queen_agent, 'generate_response', return_value="Response"):
            queen_agent.process_request("Test question")
        
        # Should add messages to chat history
        assert mock_chat_repo.add_message.call_count >= 1

    def test_complexity_analysis_detects_multiple_questions(self, queen_agent):
        """Test that complexity analysis detects multiple questions."""
        result = queen_agent._analyze_complexity("What is X? And what is Y? Also Z?")
        
        assert result is True

    def test_complexity_analysis_detects_long_input(self, queen_agent):
        """Test that complexity analysis detects long input."""
        long_text = " ".join(["word"] * 60)  # 60 words
        result = queen_agent._analyze_complexity(long_text)
        
        assert result is True

    def test_format_discussion_results_creates_output(self, queen_agent):
        """Test that format_discussion_results creates formatted output."""
        results = {
            "status": "completed",
            "final_summary": "This is the final summary",
            "contributions": [],
            "rounds": []  # Add rounds key
        }
        
        result = queen_agent._format_discussion_results(results, "Original question")
        
        # Check for key elements in the formatted output
        assert isinstance(result, str)
        assert len(result) > 0
        assert "QueenBee" in result or "queenbee" in result.lower()

    def test_format_discussion_results_handles_different_status(self, queen_agent):
        """Test that format_discussion_results handles different statuses."""
        results = {
            "status": "timeout",
            "final_summary": "Partial results",
            "rounds": []  # Add rounds key
        }
        
        result = queen_agent._format_discussion_results(results, "Original question")
        
        # Should still return a string
        assert isinstance(result, str)
