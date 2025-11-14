"""Unit tests for Ollama LLM client."""

import json
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from queenbee.config.loader import OllamaConfig
from queenbee.llm import OllamaClient


class TestOllamaClient:
    """Test Ollama client functionality."""

    @pytest.fixture
    def ollama_config(self):
        """Create test Ollama configuration."""
        return OllamaConfig(
            host="http://localhost:11434",
            model="llama2",
            timeout=30
        )

    @pytest.fixture
    def client(self, ollama_config):
        """Create OllamaClient instance."""
        return OllamaClient(ollama_config)

    def test_init_sets_config(self, ollama_config):
        """Test that initialization sets configuration."""
        client = OllamaClient(ollama_config)
        
        assert client.config == ollama_config
        assert client.base_url == "http://localhost:11434"
        assert client.model == "llama2"  # Now this is a string for compatibility
        assert client.model_id == "llama2"
        assert client.timeout == 30
        assert client._agno_model is not None  # Check Agno model exists

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base URL."""
        config = OllamaConfig(host="http://localhost:11434/", model="llama2")
        client = OllamaClient(config)
        
        assert client.base_url == "http://localhost:11434"

    @patch('queenbee.llm.Agent')
    def test_generate_sync_without_system(self, mock_agent_class, client):
        """Test synchronous generation without system prompt."""
        # Mock Agno Agent response
        mock_response = Mock()
        mock_response.content = "Generated text"
        
        mock_agent = Mock()
        mock_agent.run.return_value = mock_response
        mock_agent_class.return_value = mock_agent
        
        result = client.generate("Test prompt", stream=False)
        
        assert result == "Generated text"
        mock_agent_class.assert_called_once()  # Agent created
        mock_agent.run.assert_called_once_with("Test prompt", stream=False)

    @patch('queenbee.llm.Agent')
    def test_generate_sync_with_system(self, mock_agent_class, client):
        """Test synchronous generation with system prompt."""
        # Mock Agno Agent response
        mock_response = Mock()
        mock_response.content = "Generated text"
        
        mock_agent = Mock()
        mock_agent.run.return_value = mock_response
        mock_agent_class.return_value = mock_agent
        
        result = client.generate("Test prompt", system="System prompt", stream=False)
        
        assert result == "Generated text"
        mock_agent.run.assert_called_once_with("Test prompt", stream=False)

    @patch('queenbee.llm.Agent')
    def test_generate_sync_with_temperature(self, mock_agent_class, client):
        """Test that temperature is passed correctly."""
        # Mock Agno Agent response
        mock_response = Mock()
        mock_response.content = "Generated text"
        
        mock_agent = Mock()
        mock_agent.run.return_value = mock_response
        mock_agent_class.return_value = mock_agent
        
        result = client.generate("Test prompt", temperature=0.9, stream=False)
        
        assert result == "Generated text"
        # Verify Agent was called with correct model config
        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        model_arg = call_args[1]['model']
        # Check that options were set (temperature should be in model.options)
        assert model_arg.options['temperature'] == 0.9

    @patch('queenbee.llm.Agent')
    def test_generate_stream(self, mock_agent_class, client):
        """Test streaming generation."""
        # Mock Agno streaming response
        mock_event1 = Mock()
        mock_event1.content = "Hello"
        mock_event2 = Mock()
        mock_event2.content = " world"
        mock_event3 = Mock()
        mock_event3.content = "!"
        
        mock_agent = Mock()
        mock_agent.run.return_value = iter([mock_event1, mock_event2, mock_event3])
        mock_agent_class.return_value = mock_agent
        
        result = client.generate("Test prompt", stream=True)
        chunks = list(result)
        
        assert chunks == ["Hello", " world", "!"]
        mock_agent.run.assert_called_once_with("Test prompt", stream=True)

    @patch('queenbee.llm.Agent')
    def test_generate_stream_handles_invalid_json(self, mock_agent_class, client):
        """Test that streaming handles invalid JSON gracefully."""
        # Mock Agno streaming with some None/empty content (simulating errors)
        mock_event1 = Mock()
        mock_event1.content = "Valid"
        mock_event2 = Mock()
        mock_event2.content = None  # Simulates skipped content
        mock_event3 = Mock()
        mock_event3.content = "Also valid"
        
        mock_agent = Mock()
        mock_agent.run.return_value = iter([mock_event1, mock_event2, mock_event3])
        mock_agent_class.return_value = mock_agent
        
        result = client.generate("Test prompt", stream=True)
        chunks = list(result)
        
        # Should skip None/empty content
        assert chunks == ["Valid", "Also valid"]

    @patch('queenbee.llm.Agent')
    def test_chat_sync(self, mock_agent_class, client):
        """Test synchronous chat."""
        # Mock Agno Agent response
        mock_response = Mock()
        mock_response.content = "Chat response"
        
        mock_agent = Mock()
        mock_agent.run.return_value = mock_response
        mock_agent_class.return_value = mock_agent
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        result = client.chat(messages, stream=False)
        
        assert result == "Chat response"
        # Agent should be called with last message content
        mock_agent.run.assert_called_once_with("Hi there!", stream=False)

    @patch('queenbee.llm.Agent')
    def test_chat_stream(self, mock_agent_class, client):
        """Test streaming chat."""
        # Mock Agno streaming response
        mock_event1 = Mock()
        mock_event1.content = "Hello"
        mock_event2 = Mock()
        mock_event2.content = " world"
        
        mock_agent = Mock()
        mock_agent.run.return_value = iter([mock_event1, mock_event2])
        mock_agent_class.return_value = mock_agent
        
        messages = [{"role": "user", "content": "Test"}]
        result = client.chat(messages, stream=True)
        chunks = list(result)
        
        assert chunks == ["Hello", " world"]
        mock_agent.run.assert_called_once_with("Test", stream=True)

    @patch('queenbee.llm.httpx.Client')
    def test_list_models(self, mock_client_class, client):
        """Test listing available models."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama2"},
                {"name": "mistral"},
                {"name": "codellama"}
            ]
        }
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = client.list_models()
        
        assert result == ["llama2", "mistral", "codellama"]
        mock_client.get.assert_called_once_with("http://localhost:11434/api/tags")

    @patch('queenbee.llm.httpx.Client')
    def test_list_models_empty(self, mock_client_class, client):
        """Test listing models when none are available."""
        mock_response = Mock()
        mock_response.json.return_value = {"models": []}
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = client.list_models()
        
        assert result == []

    @patch('queenbee.llm.httpx.Client')
    def test_is_available_returns_true_when_server_up(self, mock_client_class, client):
        """Test is_available returns True when server is up."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = client.is_available()
        
        assert result is True

    @patch('queenbee.llm.httpx.Client')
    def test_is_available_returns_false_on_error(self, mock_client_class, client):
        """Test is_available returns False on connection error."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value = mock_client
        
        result = client.is_available()
        
        assert result is False

    @patch('queenbee.llm.httpx.Client')
    def test_is_available_returns_false_on_non_200_status(self, mock_client_class, client):
        """Test is_available returns False on non-200 status."""
        mock_response = Mock()
        mock_response.status_code = 500
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = client.is_available()
        
        assert result is False
