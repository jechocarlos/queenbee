"""Unit tests for BaseAgent class."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch
from uuid import UUID, uuid4

import pytest

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.models import AgentType


class TestBaseAgent:
    """Test BaseAgent functionality."""

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
        config.agents.queen.system_prompt_file = "./prompts/queen.md"
        config.agents.queen.max_iterations = 5
        config.agents.divergent = MagicMock()
        config.agents.divergent.system_prompt_file = "./prompts/divergent.md"
        config.agents.divergent.max_iterations = 10
        config.agents.convergent = MagicMock()
        config.agents.convergent.system_prompt_file = "./prompts/convergent.md"
        config.agents.convergent.max_iterations = 10
        config.agents.critical = MagicMock()
        config.agents.critical.system_prompt_file = "./prompts/critical.md"
        config.agents.critical.max_iterations = 10
        config.agents.summarizer = MagicMock()
        config.agents.summarizer.system_prompt_file = "./prompts/summarizer.md"
        config.agents.summarizer.max_iterations = 5
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

    def test_base_agent_initialization_queen(self, mock_config, mock_db):
        """Test BaseAgent initializes correctly for Queen agent."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                with patch('builtins.open', mock_open(read_data="Queen system prompt")):
                    session_id = uuid4()
                    agent = BaseAgent(AgentType.QUEEN, session_id, mock_config, mock_db)
                    
                    assert agent.agent_type == AgentType.QUEEN
                    assert agent.session_id == session_id
                    assert agent.config == mock_config
                    assert agent.db == mock_db
                    assert agent.system_prompt == "Queen system prompt"

    def test_base_agent_initialization_divergent(self, mock_config, mock_db):
        """Test BaseAgent initializes correctly for Divergent agent."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                with patch('builtins.open', mock_open(read_data="Divergent system prompt")):
                    session_id = uuid4()
                    agent = BaseAgent(AgentType.DIVERGENT, session_id, mock_config, mock_db)
                    
                    assert agent.agent_type == AgentType.DIVERGENT
                    assert agent.system_prompt == "Divergent system prompt"

    def test_base_agent_initialization_convergent(self, mock_config, mock_db):
        """Test BaseAgent initializes correctly for Convergent agent."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                with patch('builtins.open', mock_open(read_data="Convergent system prompt")):
                    session_id = uuid4()
                    agent = BaseAgent(AgentType.CONVERGENT, session_id, mock_config, mock_db)
                    
                    assert agent.agent_type == AgentType.CONVERGENT
                    assert agent.system_prompt == "Convergent system prompt"

    def test_base_agent_initialization_critical(self, mock_config, mock_db):
        """Test BaseAgent initializes correctly for Critical agent."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                with patch('builtins.open', mock_open(read_data="Critical system prompt")):
                    session_id = uuid4()
                    agent = BaseAgent(AgentType.CRITICAL, session_id, mock_config, mock_db)
                    
                    assert agent.agent_type == AgentType.CRITICAL
                    assert agent.system_prompt == "Critical system prompt"

    def test_base_agent_initialization_summarizer(self, mock_config, mock_db):
        """Test BaseAgent initializes correctly for Summarizer agent."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                with patch('builtins.open', mock_open(read_data="Summarizer system prompt")):
                    session_id = uuid4()
                    agent = BaseAgent(AgentType.SUMMARIZER, session_id, mock_config, mock_db)
                    
                    assert agent.agent_type == AgentType.SUMMARIZER
                    assert agent.system_prompt == "Summarizer system prompt"

    def test_load_system_prompt_file_not_found(self, mock_config, mock_db):
        """Test that FileNotFoundError is raised when prompt file doesn't exist."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = False
                mock_path.return_value = mock_path_instance
                
                session_id = uuid4()
                with pytest.raises(FileNotFoundError):
                    BaseAgent(AgentType.QUEEN, session_id, mock_config, mock_db)

    def test_agent_creates_database_record(self, mock_config, mock_db):
        """Test that agent creates a database record on initialization."""
        with patch('queenbee.agents.base.AgentRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_agent_id = uuid4()
            mock_repo.create_agent.return_value = mock_agent_id
            mock_repo_class.return_value = mock_repo
            
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                with patch('builtins.open', mock_open(read_data="Test prompt")):
                    session_id = uuid4()
                    agent = BaseAgent(AgentType.QUEEN, session_id, mock_config, mock_db)
                    
                    # Verify agent_id was set
                    assert agent.agent_id == mock_agent_id
                    
                    # Verify create_agent was called
                    mock_repo.create_agent.assert_called_once()
                    call_args = mock_repo.create_agent.call_args
                    assert call_args[1]['agent_type'] == AgentType.QUEEN
                    assert call_args[1]['session_id'] == session_id

    def test_agent_config_for_each_type(self, mock_config, mock_db):
        """Test _get_agent_config returns correct config for each agent type."""
        agent_types = [
            AgentType.QUEEN,
            AgentType.DIVERGENT,
            AgentType.CONVERGENT,
            AgentType.CRITICAL,
            AgentType.SUMMARIZER
        ]
        
        for agent_type in agent_types:
            with patch('queenbee.agents.base.AgentRepository'):
                with patch('queenbee.agents.base.Path') as mock_path:
                    mock_path_instance = MagicMock()
                    mock_path_instance.exists.return_value = True
                    mock_path.return_value = mock_path_instance
                    
                    with patch('builtins.open', mock_open(read_data="Test prompt")):
                        session_id = uuid4()
                        agent = BaseAgent(agent_type, session_id, mock_config, mock_db)
                        
                        config = agent._get_agent_config()
                        assert isinstance(config, dict)
                        # Queen has complexity_threshold, others have max_iterations
                        if agent_type == AgentType.QUEEN:
                            assert "complexity_threshold" in config
                        else:
                            assert "max_iterations" in config

    def test_ollama_client_initialization(self, mock_config, mock_db):
        """Test that OllamaClient is initialized correctly."""
        with patch('queenbee.agents.base.AgentRepository'):
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                with patch('builtins.open', mock_open(read_data="Test prompt")):
                    with patch('queenbee.agents.base.OllamaClient') as mock_ollama_class:
                        mock_ollama = MagicMock()
                        mock_ollama_class.return_value = mock_ollama
                        
                        session_id = uuid4()
                        agent = BaseAgent(AgentType.QUEEN, session_id, mock_config, mock_db)
                        
                        # Verify OllamaClient was initialized
                        mock_ollama_class.assert_called_once_with(mock_config.ollama)
                        assert agent.ollama == mock_ollama

    def test_agent_repository_initialization(self, mock_config, mock_db):
        """Test that AgentRepository is initialized correctly."""
        with patch('queenbee.agents.base.AgentRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                with patch('builtins.open', mock_open(read_data="Test prompt")):
                    session_id = uuid4()
                    agent = BaseAgent(AgentType.QUEEN, session_id, mock_config, mock_db)
                    
                    # Verify AgentRepository was initialized with database
                    mock_repo_class.assert_called_once_with(mock_db)
                    assert agent.agent_repo == mock_repo

    def test_logging_on_initialization(self, mock_config, mock_db, caplog):
        """Test that initialization logs appropriate messages."""
        with caplog.at_level(logging.INFO):
            with patch('queenbee.agents.base.AgentRepository'):
                with patch('queenbee.agents.base.Path') as mock_path:
                    mock_path_instance = MagicMock()
                    mock_path_instance.exists.return_value = True
                    mock_path.return_value = mock_path_instance
                    
                    with patch('builtins.open', mock_open(read_data="Test prompt")):
                        session_id = uuid4()
                        agent = BaseAgent(AgentType.QUEEN, session_id, mock_config, mock_db)
                        
                        # Check for initialization log message
                        assert any("initialized queen agent" in record.message.lower() 
                                  for record in caplog.records)

    def test_terminate_agent(self, mock_config, mock_db):
        """Test agent termination."""
        with patch('queenbee.agents.base.AgentRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            with patch('queenbee.agents.base.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                with patch('builtins.open', mock_open(read_data="Test prompt")):
                    session_id = uuid4()
                    agent = BaseAgent(AgentType.QUEEN, session_id, mock_config, mock_db)
                    agent.terminate()
                    
                    # Verify update_agent_status was called with TERMINATED
                    from queenbee.db.models import AgentStatus
                    mock_repo.update_agent_status.assert_called_once_with(
                        agent.agent_id, 
                        AgentStatus.TERMINATED
                    )
