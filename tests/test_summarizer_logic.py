"""Unit tests for SummarizerAgent rolling summary and synthesis logic."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from queenbee.agents.summarizer import SummarizerAgent
from queenbee.config.loader import Config
from queenbee.db.models import AgentType


class TestSummarizerEdgeCases:
    """Test edge cases for Summarizer agent."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=Config)
        config.ollama = MagicMock()
        config.ollama.model = "llama2"
        config.ollama.host = "http://localhost:11434"
        config.ollama.timeout = 30
        config.agents = MagicMock()
        config.agents.summarizer = MagicMock()
        config.agents.summarizer.system_prompt_file = "prompts/summarizer.md"
        config.agents.summarizer.max_iterations = 5
        return config

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MagicMock()
        return db

    @pytest.fixture
    def summarizer(self, mock_config, mock_db):
        """Create Summarizer agent instance."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: "System prompt")))):
                    session_id = uuid4()
                    return SummarizerAgent(session_id, mock_config, mock_db)

    def test_rolling_summary_with_empty_contributions(self, summarizer):
        """Test rolling summary returns message for empty contributions."""
        result = summarizer.generate_rolling_summary("Test question", [])
        
        assert result == "No contributions yet."
        assert isinstance(result, str)

    def test_rolling_summary_with_single_contribution(self, summarizer):
        """Test rolling summary with one contribution."""
        contributions = [
            {"agent": "Divergent", "content": "First idea"}
        ]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Summary of one contribution"):
            result = summarizer.generate_rolling_summary("What is X?", contributions)
            
            assert result == "Summary of one contribution"
            summarizer.ollama.generate.assert_called_once()

    def test_rolling_summary_with_multiple_contributions(self, summarizer):
        """Test rolling summary with multiple contributions."""
        contributions = [
            {"agent": "Divergent", "content": "Idea 1"},
            {"agent": "Convergent", "content": "Synthesis 1"},
            {"agent": "Critical", "content": "Analysis 1"}
        ]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Comprehensive summary"):
            result = summarizer.generate_rolling_summary("Complex query", contributions)
            
            assert result == "Comprehensive summary"
            # Check that prompt includes all contributions
            call_args = summarizer.ollama.generate.call_args
            prompt = call_args[1]['prompt']
            assert "Idea 1" in prompt
            assert "Synthesis 1" in prompt
            assert "Analysis 1" in prompt

    def test_rolling_summary_uses_lower_temperature(self, summarizer):
        """Test that rolling summary uses temperature 0.3 for consistency."""
        contributions = [{"agent": "Divergent", "content": "Test"}]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Summary"):
            summarizer.generate_rolling_summary("Question", contributions)
            
            call_kwargs = summarizer.ollama.generate.call_args[1]
            assert call_kwargs['temperature'] == 0.3

    def test_rolling_summary_streaming_support(self, summarizer):
        """Test that rolling summary supports streaming."""
        contributions = [{"agent": "Divergent", "content": "Test"}]
        
        def mock_stream():
            yield "Part 1"
            yield "Part 2"
        
        with patch.object(summarizer.ollama, 'generate', return_value=mock_stream()):
            result = summarizer.generate_rolling_summary("Question", contributions, stream=True)
            
            # Result should be an iterator
            chunks = list(result)
            assert len(chunks) == 2
            assert chunks[0] == "Part 1"
            assert chunks[1] == "Part 2"

    def test_final_synthesis_with_empty_contributions(self, summarizer):
        """Test final synthesis with no contributions."""
        result = summarizer.generate_final_synthesis("Question", [])
        
        assert result == "No discussion occurred."

    def test_final_synthesis_with_single_contribution(self, summarizer):
        """Test final synthesis with one contribution."""
        contributions = [{"agent": "Divergent", "content": "Only idea"}]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Final synthesis"):
            result = summarizer.generate_final_synthesis("Question", contributions)
            
            assert result == "Final synthesis"

    def test_final_synthesis_with_all_agent_types(self, summarizer):
        """Test final synthesis includes all specialist perspectives."""
        contributions = [
            {"agent": "Divergent", "content": "Multiple perspectives"},
            {"agent": "Convergent", "content": "Synthesized recommendations"},
            {"agent": "Critical", "content": "Validation and risks"}
        ]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Complete synthesis"):
            result = summarizer.generate_final_synthesis("Complex problem", contributions)
            
            assert result == "Complete synthesis"
            # Verify all perspectives are in prompt
            call_args = summarizer.ollama.generate.call_args
            prompt = call_args[1]['prompt']
            assert "Multiple perspectives" in prompt
            assert "Synthesized recommendations" in prompt
            assert "Validation and risks" in prompt

    def test_final_synthesis_uses_temperature_0_4(self, summarizer):
        """Test that final synthesis uses temperature 0.4."""
        contributions = [{"agent": "Divergent", "content": "Test"}]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Synthesis"):
            summarizer.generate_final_synthesis("Question", contributions)
            
            call_kwargs = summarizer.ollama.generate.call_args[1]
            assert call_kwargs['temperature'] == 0.4

    def test_final_synthesis_streaming_support(self, summarizer):
        """Test that final synthesis supports streaming."""
        contributions = [{"agent": "Divergent", "content": "Test"}]
        
        def mock_stream():
            yield "Synthesis "
            yield "parts"
        
        with patch.object(summarizer.ollama, 'generate', return_value=mock_stream()):
            result = summarizer.generate_final_synthesis("Question", contributions, stream=True)
            
            # Result should be an iterator
            chunks = list(result)
            assert "Synthesis " in chunks
            assert "parts" in chunks

    def test_rolling_summary_formats_discussion_correctly(self, summarizer):
        """Test that discussion is formatted properly in rolling summary."""
        contributions = [
            {"agent": "Divergent", "content": "First point\nSecond line"},
            {"agent": "Convergent", "content": "Synthesis point"}
        ]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Summary") as mock_gen:
            summarizer.generate_rolling_summary("Question?", contributions)
            
            prompt = mock_gen.call_args[1]['prompt']
            # Check formatting
            assert "Divergent:" in prompt
            assert "Convergent:" in prompt
            assert "First point" in prompt
            assert "Question?" in prompt

    def test_final_synthesis_formats_discussion_correctly(self, summarizer):
        """Test that discussion is formatted properly in final synthesis."""
        contributions = [
            {"agent": "Divergent", "content": "Idea"},
            {"agent": "Critical", "content": "Analysis"}
        ]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Synthesis") as mock_gen:
            summarizer.generate_final_synthesis("Original query", contributions)
            
            prompt = mock_gen.call_args[1]['prompt']
            # Check formatting
            assert "Divergent:" in prompt
            assert "Critical:" in prompt
            assert "Original query" in prompt

    def test_rolling_summary_with_very_long_contributions(self, summarizer):
        """Test rolling summary handles very long contributions."""
        long_content = "A" * 5000  # Very long contribution
        contributions = [
            {"agent": "Divergent", "content": long_content}
        ]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Concise summary"):
            result = summarizer.generate_rolling_summary("Question", contributions)
            
            assert result == "Concise summary"
            # Verify the long content was passed to LLM
            prompt = summarizer.ollama.generate.call_args[1]['prompt']
            assert long_content in prompt

    def test_final_synthesis_with_duplicate_agents(self, summarizer):
        """Test final synthesis when same agent contributes multiple times."""
        contributions = [
            {"agent": "Divergent", "content": "First idea"},
            {"agent": "Divergent", "content": "Second idea"},
            {"agent": "Convergent", "content": "Synthesis"}
        ]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Final result"):
            result = summarizer.generate_final_synthesis("Question", contributions)
            
            assert result == "Final result"
            # All contributions should be included
            prompt = summarizer.ollama.generate.call_args[1]['prompt']
            assert "First idea" in prompt
            assert "Second idea" in prompt

    def test_rolling_summary_preserves_user_input(self, summarizer):
        """Test that user input is preserved in rolling summary."""
        user_input = "What are the tradeoffs between approach A and B?"
        contributions = [{"agent": "Divergent", "content": "Analysis"}]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Summary") as mock_gen:
            summarizer.generate_rolling_summary(user_input, contributions)
            
            prompt = mock_gen.call_args[1]['prompt']
            assert user_input in prompt

    def test_final_synthesis_preserves_user_input(self, summarizer):
        """Test that user input is preserved in final synthesis."""
        user_input = "Explain quantum computing to a beginner"
        contributions = [{"agent": "Divergent", "content": "Explanation"}]
        
        with patch.object(summarizer.ollama, 'generate', return_value="Synthesis") as mock_gen:
            summarizer.generate_final_synthesis(user_input, contributions)
            
            prompt = mock_gen.call_args[1]['prompt']
            assert user_input in prompt
