"""Unit tests for Queen agent complexity analysis."""

from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from queenbee.agents.queen import QueenAgent
from queenbee.config.loader import Config, load_config


class TestComplexityAnalysis:
    """Tests for Queen's complexity analysis logic."""

    @pytest.fixture
    def mock_config(self, temp_config_file):
        """Create a mock config."""
        return load_config(str(temp_config_file))

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager with context manager support."""
        mock = MagicMock()
        # Mock get_cursor to return a context manager
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock.get_cursor = MagicMock(return_value=mock_cursor)
        return mock

    @pytest.fixture
    def queen_agent(self, mock_config, mock_db):
        """Create a Queen agent instance for testing."""
        session_id = uuid4()
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.queen.ChatRepository'):
                with patch('queenbee.agents.queen.TaskRepository'):
                    agent = QueenAgent(session_id, mock_config, mock_db)
                    return agent

    def test_simple_request_single_word(self, queen_agent):
        """Test that single-word queries are classified as simple."""
        assert queen_agent._analyze_complexity("Hello") == False
        assert queen_agent._analyze_complexity("Python") == False
        assert queen_agent._analyze_complexity("Help") == False

    def test_simple_request_short_question(self, queen_agent):
        """Test that short factual questions are simple."""
        assert queen_agent._analyze_complexity("What is Python?") == False
        assert queen_agent._analyze_complexity("Who are you?") == False
        assert queen_agent._analyze_complexity("What time is it?") == False

    def test_complex_keyword_analyze(self, queen_agent):
        """Test that 'analyze' keyword triggers complexity."""
        assert queen_agent._analyze_complexity("Analyze this problem") == True
        assert queen_agent._analyze_complexity("Can you analyze the situation?") == True

    def test_complex_keyword_compare(self, queen_agent):
        """Test that 'compare' keyword triggers complexity."""
        assert queen_agent._analyze_complexity("Compare Python and JavaScript") == True
        assert queen_agent._analyze_complexity("What are the comparisons?") == True

    def test_complex_keyword_design(self, queen_agent):
        """Test that 'design' keyword triggers complexity."""
        assert queen_agent._analyze_complexity("How to design a system?") == True
        assert queen_agent._analyze_complexity("Design a database schema") == True

    def test_complex_keyword_evaluate(self, queen_agent):
        """Test that 'evaluate' keyword triggers complexity."""
        assert queen_agent._analyze_complexity("Evaluate these options") == True
        assert queen_agent._analyze_complexity("Can you evaluate the approach?") == True

    def test_complex_keyword_how_to(self, queen_agent):
        """Test that 'how to' triggers complexity."""
        assert queen_agent._analyze_complexity("How to implement authentication?") == True
        assert queen_agent._analyze_complexity("How do I build a REST API?") == True

    def test_complex_keyword_explain(self, queen_agent):
        """Test that 'explain' triggers complexity."""
        assert queen_agent._analyze_complexity("Explain microservices architecture") == True
        assert queen_agent._analyze_complexity("Can you explain this concept?") == True

    def test_complex_keyword_tradeoffs(self, queen_agent):
        """Test that 'trade-offs' triggers complexity."""
        assert queen_agent._analyze_complexity("What are the trade-offs?") == True
        assert queen_agent._analyze_complexity("Discuss the tradeoffs") == True

    def test_complex_multiple_questions(self, queen_agent):
        """Test that multiple questions trigger complexity."""
        text = "What is Python? What is JavaScript?"
        assert queen_agent._analyze_complexity(text) == True

    def test_complex_long_input(self, queen_agent):
        """Test that long input (>50 words) triggers complexity."""
        long_text = " ".join(["word"] * 51)
        assert queen_agent._analyze_complexity(long_text) == True

    def test_simple_short_input(self, queen_agent):
        """Test that short input without keywords is simple."""
        short_text = " ".join(["word"] * 10)
        assert queen_agent._analyze_complexity(short_text) == False

    def test_edge_case_exactly_50_words(self, queen_agent):
        """Test edge case of exactly 50 words."""
        text = " ".join(["word"] * 50)
        assert queen_agent._analyze_complexity(text) == False

    def test_edge_case_51_words(self, queen_agent):
        """Test that 51 words triggers complexity."""
        text = " ".join(["word"] * 51)
        assert queen_agent._analyze_complexity(text) == True

    def test_case_insensitive_keywords(self, queen_agent):
        """Test that keyword detection is case-insensitive."""
        assert queen_agent._analyze_complexity("ANALYZE this") == True
        assert queen_agent._analyze_complexity("Compare THESE") == True
        assert queen_agent._analyze_complexity("how TO implement") == True

    def test_keyword_as_part_of_word(self, queen_agent):
        """Test that keywords must be whole words."""
        # "analyzer" contains "analyze" but shouldn't match due to word boundary
        assert queen_agent._analyze_complexity("I am an analyzer") == False  # Doesn't match \banalyze\b
        assert queen_agent._analyze_complexity("I need to analyze this") == True  # Does match \banalyze\b
        assert queen_agent._analyze_complexity("I like catalyze") == False  # Shouldn't match

    def test_real_world_complex_queries(self, queen_agent):
        """Test real-world complex queries."""
        queries = [
            "How to implement a multi-agent system with LangGraph?",
            "Compare microservices vs monolithic architecture",
            "Design a scalable database schema for e-commerce",
            "Evaluate the pros and cons of using TypeScript",
            "What are the trade-offs between SQL and NoSQL?",
            "Explain the benefits of event-driven architecture"
        ]
        for query in queries:
            assert queen_agent._analyze_complexity(query) == True, f"Failed for: {query}"

    def test_real_world_simple_queries(self, queen_agent):
        """Test real-world simple queries."""
        queries = [
            "What is Python?",
            "Hello",
            "Who are you?",
            "What's the weather?",
            "Thank you",
            "Help"
        ]
        for query in queries:
            assert queen_agent._analyze_complexity(query) == False, f"Failed for: {query}"
