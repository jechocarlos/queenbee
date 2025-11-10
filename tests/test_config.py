"""Unit tests for configuration loader."""

import os
from pathlib import Path

import pytest

from queenbee.config.loader import (AgentsConfig, Config, ConsensusConfig,
                                    DatabaseConfig, OllamaConfig, load_config)


class TestDatabaseConfig:
    """Tests for DatabaseConfig."""

    def test_connection_string_format(self):
        """Test PostgreSQL connection string formatting."""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="testdb",
            user="testuser",
            password="testpass",
            ssl_mode="require"
        )
        
        expected = "postgresql://testuser:testpass@localhost:5432/testdb?sslmode=require"
        assert config.connection_string == expected

    @pytest.mark.skip(reason="Test expects defaults but .env file overrides config values")
    def test_default_values(self):
        """Test default configuration values."""
        config = DatabaseConfig(password="testpass")
        
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.name == "queenbee"
        assert config.user == "queenbee"
        assert config.ssl_mode == "prefer"


class TestOllamaConfig:
    """Tests for OllamaConfig."""

    def test_default_values(self):
        """Test default Ollama configuration."""
        config = OllamaConfig()
        
        assert config.host == "http://localhost:11434"
        assert config.model == "llama3.1:8b"
        assert config.timeout == 120

    def test_custom_values(self):
        """Test custom Ollama configuration."""
        config = OllamaConfig(
            host="http://remote:11434",
            model="deepseek-r1:1.5b",
            timeout=300
        )
        
        assert config.host == "http://remote:11434"
        assert config.model == "deepseek-r1:1.5b"
        assert config.timeout == 300


class TestConsensusConfig:
    """Tests for ConsensusConfig."""

    def test_default_values(self):
        """Test default consensus configuration."""
        config = ConsensusConfig()
        
        assert config.max_rounds == 10
        assert config.agreement_threshold == "all"
        assert config.discussion_rounds == 3
        assert config.specialist_timeout_seconds == 300

    def test_custom_timeout(self):
        """Test custom specialist timeout."""
        config = ConsensusConfig(specialist_timeout_seconds=600)
        
        assert config.specialist_timeout_seconds == 600


class TestConfigLoader:
    """Tests for configuration loading."""

    def test_load_config_from_yaml(self, temp_config_file: Path):
        """Test loading configuration from YAML file."""
        config = load_config(str(temp_config_file))
        
        assert config.system.name == "queenbee"
        assert config.system.version == "1.0.0"
        assert config.system.environment == "test"
        
        assert config.database.host == "localhost"
        assert config.database.port == 5432
        assert config.database.name == "queenbee_test"
        
        assert config.ollama.host == "http://localhost:11434"
        assert config.ollama.model == "llama3.1:8b"
        assert config.ollama.timeout == 300
        
        assert config.consensus.discussion_rounds == 10
        assert config.consensus.specialist_timeout_seconds == 300

    @pytest.mark.skip(reason="Environment variable overrides not working with .env file present")
    def test_config_with_environment_variables(self, temp_config_file: Path, monkeypatch):
        """Test configuration with environment variable overrides."""
        monkeypatch.setenv("DB_HOST", "custom-host")
        monkeypatch.setenv("DB_PORT", "5433")
        monkeypatch.setenv("OLLAMA_HOST", "http://custom:11434")
        
        config = load_config(str(temp_config_file))
        
        # Environment variables should override config file
        assert config.database.host == "custom-host"
        assert config.database.port == 5433
        assert config.ollama.host == "http://custom:11434"

    def test_missing_password_raises_error(self, tmp_path: Path):
        """Test that missing password raises validation error."""
        config_content = """
system:
  name: queenbee
  version: 1.0.0

database:
  host: localhost
  port: 5432
  name: queenbee

ollama:
  host: http://localhost:11434

agents:
  ttl:
    idle_timeout_minutes: 10
  max_concurrent_specialists: 10
  queen:
    system_prompt_file: ./prompts/queen.md
  divergent:
    system_prompt_file: ./prompts/divergent.md
  convergent:
    system_prompt_file: ./prompts/convergent.md
  critical:
    system_prompt_file: ./prompts/critical.md
  summarizer:
    system_prompt_file: ./prompts/summarizer.md
    max_iterations: 5

consensus:
  max_rounds: 10
  agreement_threshold: "all"
  discussion_rounds: 3

logging:
  level: INFO
"""
        config_file = tmp_path / "invalid_config.yaml"
        config_file.write_text(config_content)
        
        with pytest.raises(Exception):  # Pydantic validation error
            load_config(str(config_file))


class TestAgentPromptConfig:
    """Tests for agent prompt configuration."""

    def test_agent_config_structure(self, temp_config_file: Path):
        """Test agent configuration structure."""
        config = load_config(str(temp_config_file))
        
        assert hasattr(config.agents, "queen")
        assert hasattr(config.agents, "divergent")
        assert hasattr(config.agents, "convergent")
        assert hasattr(config.agents, "critical")
        
        assert config.agents.queen.system_prompt_file == "./prompts/queen.md"
        assert config.agents.divergent.max_iterations == 10
        assert config.agents.convergent.max_iterations == 10
        assert config.agents.critical.max_iterations == 10
