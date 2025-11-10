"""Unit tests for specialist agents (Divergent, Convergent, Critical)."""

from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from queenbee.agents.convergent import ConvergentAgent
from queenbee.agents.critical import CriticalAgent
from queenbee.agents.divergent import DivergentAgent
from queenbee.config.loader import Config
from queenbee.db.models import AgentType


class TestDivergentAgent:
    """Test Divergent agent functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=Config)
        config.ollama = MagicMock()
        config.ollama.model = "llama2"
        config.ollama.host = "http://localhost:11434"
        config.ollama.timeout = 30
        config.agents = MagicMock()
        config.agents.divergent = MagicMock()
        config.agents.divergent.system_prompt_file = "prompts/divergent.md"
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
    def agent(self, mock_config, mock_db):
        """Create Divergent agent instance."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: "System prompt")))):
                    session_id = uuid4()
                    agent = DivergentAgent(session_id, mock_config, mock_db)
                    return agent

    def test_init_creates_divergent_agent(self, mock_config, mock_db):
        """Test that initialization creates agent with correct type."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: "System prompt")))):
                    session_id = uuid4()
                    agent = DivergentAgent(session_id, mock_config, mock_db)
                    
                    assert agent.agent_type == AgentType.DIVERGENT
                    assert agent.session_id == session_id

    def test_explore_generates_perspectives(self, agent):
        """Test that explore method generates perspectives."""
        with patch.object(agent, 'generate_response', return_value="1. First perspective\n2. Second perspective\n3. Third perspective"):
            perspectives = agent.explore("Test task")
            
            assert isinstance(perspectives, list)
            assert len(perspectives) > 0
            agent.generate_response.assert_called_once()

    def test_explore_passes_context(self, agent):
        """Test that explore passes context to prompt."""
        with patch.object(agent, 'generate_response', return_value="Perspective") as mock_gen:
            agent.explore("Test task", context="Previous discussion")
            
            call_args = mock_gen.call_args[0][0]
            assert "Test task" in call_args
            assert "Previous discussion" in call_args

    def test_explore_uses_high_temperature(self, agent):
        """Test that explore uses high temperature for creativity."""
        with patch.object(agent, 'generate_response', return_value="Perspective") as mock_gen:
            agent.explore("Test task")
            
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["temperature"] == 0.9

    def test_parse_perspectives_numbered_list(self, agent):
        """Test parsing numbered list of perspectives."""
        response = """1. First perspective is here
2. Second perspective follows
3. Third perspective concludes"""
        
        perspectives = agent._parse_perspectives(response)
        
        assert len(perspectives) == 3
        assert "First perspective" in perspectives[0]
        assert "Second perspective" in perspectives[1]
        assert "Third perspective" in perspectives[2]

    def test_parse_perspectives_bullet_list(self, agent):
        """Test parsing bullet list of perspectives."""
        response = """* First perspective with bullets
* Second perspective also bulleted
* Third perspective here"""
        
        perspectives = agent._parse_perspectives(response)
        
        assert len(perspectives) == 3

    def test_parse_perspectives_mixed_format(self, agent):
        """Test parsing mixed format."""
        response = """- First with dash
• Second with bullet
* Third with asterisk"""
        
        perspectives = agent._parse_perspectives(response)
        
        assert len(perspectives) == 3

    def test_parse_perspectives_multiline(self, agent):
        """Test parsing perspectives spanning multiple lines."""
        response = """1. First perspective
   continues on next line
   and another line
2. Second perspective is here"""
        
        perspectives = agent._parse_perspectives(response)
        
        assert len(perspectives) == 2
        assert "continues on next line" in perspectives[0]

    def test_parse_perspectives_fallback(self, agent):
        """Test fallback when parsing fails."""
        response = "Just a plain paragraph without any structure"
        
        perspectives = agent._parse_perspectives(response)
        
        assert len(perspectives) == 1
        assert perspectives[0] == response


class TestConvergentAgent:
    """Test Convergent agent functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=Config)
        config.ollama = MagicMock()
        config.ollama.model = "llama2"
        config.ollama.host = "http://localhost:11434"
        config.ollama.timeout = 30
        config.agents = MagicMock()
        config.agents.convergent = MagicMock()
        config.agents.convergent.system_prompt_file = "prompts/convergent.md"
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
    def agent(self, mock_config, mock_db):
        """Create Convergent agent instance."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: "System prompt")))):
                    session_id = uuid4()
                    agent = ConvergentAgent(session_id, mock_config, mock_db)
                    return agent

    def test_init_creates_convergent_agent(self, mock_config, mock_db):
        """Test that initialization creates agent with correct type."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: "System prompt")))):
                    session_id = uuid4()
                    agent = ConvergentAgent(session_id, mock_config, mock_db)
                    
                    assert agent.agent_type == AgentType.CONVERGENT
                    assert agent.session_id == session_id

    def test_synthesize_generates_recommendations(self, agent):
        """Test that synthesize generates recommendations."""
        with patch.object(agent, 'generate_response', return_value="Recommendation text"):
            options = ["Option 1", "Option 2", "Option 3"]
            result = agent.synthesize("Test task", options)
            
            assert isinstance(result, dict)
            assert "synthesis" in result
            assert result["synthesis"] == "Recommendation text"
            assert result["perspectives_evaluated"] == 3
            agent.generate_response.assert_called_once()

    def test_synthesize_includes_options_in_prompt(self, agent):
        """Test that synthesize includes options in prompt."""
        with patch.object(agent, 'generate_response', return_value="Recommendation") as mock_gen:
            options = ["First option", "Second option"]
            agent.synthesize("Test task", options)
            
            call_args = mock_gen.call_args[0][0]
            assert "First option" in call_args
            assert "Second option" in call_args

    def test_synthesize_uses_lower_temperature(self, agent):
        """Test that synthesize uses lower temperature for focused output."""
        with patch.object(agent, 'generate_response', return_value="Recommendation") as mock_gen:
            agent.synthesize("Test task", ["Option 1"])
            
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["temperature"] == 0.5


class TestCriticalAgent:
    """Test Critical agent functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=Config)
        config.ollama = MagicMock()
        config.ollama.model = "llama2"
        config.ollama.host = "http://localhost:11434"
        config.ollama.timeout = 30
        config.agents = MagicMock()
        config.agents.critical = MagicMock()
        config.agents.critical.system_prompt_file = "prompts/critical.md"
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
    def agent(self, mock_config, mock_db):
        """Create Critical agent instance."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: "System prompt")))):
                    session_id = uuid4()
                    agent = CriticalAgent(session_id, mock_config, mock_db)
                    return agent

    def test_init_creates_critical_agent(self, mock_config, mock_db):
        """Test that initialization creates agent with correct type."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: "System prompt")))):
                    session_id = uuid4()
                    agent = CriticalAgent(session_id, mock_config, mock_db)
                    
                    assert agent.agent_type == AgentType.CRITICAL
                    assert agent.session_id == session_id

    def test_validate_analyzes_synthesis(self, agent):
        """Test that validate analyzes a synthesis."""
        with patch.object(agent, 'generate_response', return_value="Critical analysis"):
            result = agent.validate("Test task", "Proposed synthesis")
            
            assert isinstance(result, dict)
            assert "validation" in result
            agent.generate_response.assert_called_once()

    def test_validate_includes_synthesis_in_prompt(self, agent):
        """Test that validate includes synthesis in prompt."""
        with patch.object(agent, 'generate_response', return_value="Analysis") as mock_gen:
            agent.validate("Test task", "My proposed synthesis")
            
            call_args = mock_gen.call_args[0][0]
            assert "My proposed synthesis" in call_args
            assert "Test task" in call_args

    def test_validate_uses_balanced_temperature(self, agent):
        """Test that validate uses lower temperature for precision."""
        with patch.object(agent, 'generate_response', return_value="Analysis") as mock_gen:
            agent.validate("Test task", "Synthesis")
            
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["temperature"] == 0.3  # Lower temp for analytical precision
