"""Additional tests for specialist agents to increase coverage."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from queenbee.agents.convergent import ConvergentAgent
from queenbee.agents.critical import CriticalAgent
from queenbee.config.loader import AgentsConfig, Config, ConsensusConfig, DatabaseConfig, OllamaConfig


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock(spec=Config)
    config.ollama = OllamaConfig()
    config.consensus = ConsensusConfig()
    config.agents = MagicMock(spec=AgentsConfig)
    config.agents.convergent = MagicMock()
    config.agents.convergent.system_prompt_file = "./prompts/convergent.md"
    config.agents.convergent.max_iterations = 10
    config.agents.critical = MagicMock()
    config.agents.critical.system_prompt_file = "./prompts/critical.md"
    config.agents.critical.max_iterations = 10
    return config


@pytest.fixture
def mock_db():
    """Create mock database."""
    return MagicMock()


class TestConvergentAgentCoverage:
    """Test additional ConvergentAgent methods."""

    @pytest.fixture
    def convergent_agent(self, mock_config, mock_db):
        """Create a ConvergentAgent instance."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: "System prompt")))):
                    session_id = uuid4()
                    agent = ConvergentAgent(session_id, mock_config, mock_db)
                    return agent

    def test_evaluate_tradeoffs(self, convergent_agent):
        """Test trade-off evaluation between options."""
        with patch.object(convergent_agent, 'generate_response', return_value="Option 1 is better for speed, Option 2 is better for reliability") as mock_gen:
            options = [
                "Fast but less reliable approach",
                "Slower but more reliable approach"
            ]
            criteria = ["Speed", "Reliability", "Maintainability"]
            
            result = convergent_agent.evaluate_trade_offs(options, criteria)
            
            assert "trade_off_analysis" in result
            assert result["options_count"] == 2
            assert result["criteria_count"] == 3
            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["temperature"] == 0.5


class TestCriticalAgentCoverage:
    """Test additional CriticalAgent methods."""

    @pytest.fixture
    def critical_agent(self, mock_config, mock_db):
        """Create a CriticalAgent instance."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: "System prompt")))):
                    session_id = uuid4()
                    agent = CriticalAgent(session_id, mock_config, mock_db)
                    return agent

    def test_identify_risks_no_domain(self, critical_agent):
        """Test risk identification without domain context."""
        with patch.object(critical_agent, 'generate_response', return_value="Risk 1: High technical complexity. Risk 2: Performance concerns") as mock_gen:
            proposal = "Deploy new microservice architecture"
            
            result = critical_agent.identify_risks(proposal)
            
            assert "risk_analysis" in result
            assert result["domain"] == "general"
            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["temperature"] == 0.3

    def test_identify_risks_with_domain(self, critical_agent):
        """Test risk identification with specific domain context."""
        with patch.object(critical_agent, 'generate_response', return_value="Security risk: Insufficient authentication") as mock_gen:
            proposal = "Deploy new API endpoint"
            domain = "security"
            
            result = critical_agent.identify_risks(proposal, domain=domain)
            
            assert "risk_analysis" in result
            assert result["domain"] == "security"
            mock_gen.assert_called_once()
            # Verify domain was included in prompt
            prompt = mock_gen.call_args[0][0]
            assert "security" in prompt.lower()

    def test_verify_consistency(self, critical_agent):
        """Test consistency verification across statements."""
        with patch.object(critical_agent, 'generate_response', return_value="Statements are logically consistent") as mock_gen:
            statements = [
                "All users must authenticate",
                "Unauthenticated users have limited access",
                "Admin users have full access"
            ]
            
            result = critical_agent.verify_consistency(statements)
            
            assert "consistency_check" in result
            assert result["statements_analyzed"] == 3
            mock_gen.assert_called_once()
            # Verify all statements were included in prompt
            prompt = mock_gen.call_args[0][0]
            assert "1." in prompt
            assert "2." in prompt
            assert "3." in prompt

