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
        assert client.model == "llama2"
        assert client.timeout == 30

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base URL."""
        config = OllamaConfig(host="http://localhost:11434/", model="llama2")
        client = OllamaClient(config)
        
        assert client.base_url == "http://localhost:11434"

    @patch('queenbee.llm.httpx.Client')
    def test_generate_sync_without_system(self, mock_client_class, client):
        """Test synchronous generation without system prompt."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Generated text"}
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = client.generate("Test prompt", stream=False)
        
        assert result == "Generated text"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        assert call_args[1]["json"]["prompt"] == "Test prompt"
        assert call_args[1]["json"]["stream"] is False
        assert "system" not in call_args[1]["json"]

    @patch('queenbee.llm.httpx.Client')
    def test_generate_sync_with_system(self, mock_client_class, client):
        """Test synchronous generation with system prompt."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Generated text"}
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = client.generate("Test prompt", system="System prompt", stream=False)
        
        assert result == "Generated text"
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["system"] == "System prompt"

    @patch('queenbee.llm.httpx.Client')
    def test_generate_sync_with_temperature(self, mock_client_class, client):
        """Test that temperature is passed correctly."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Generated text"}
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = client.generate("Test prompt", temperature=0.9, stream=False)
        
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["options"]["temperature"] == 0.9

    @patch('queenbee.llm.httpx.Client')
    def test_generate_stream(self, mock_client_class, client):
        """Test streaming generation."""
        # Mock streaming response
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            '{"response": "Hello"}',
            '{"response": " world"}',
            '{"response": "!"}',
        ]
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_stream_context = MagicMock()
        mock_stream_context.__enter__.return_value = mock_response
        mock_client.stream.return_value = mock_stream_context
        mock_client_class.return_value = mock_client
        
        result = client.generate("Test prompt", stream=True)
        chunks = list(result)
        
        assert chunks == ["Hello", " world", "!"]
        mock_client.stream.assert_called_once()

    @patch('queenbee.llm.httpx.Client')
    def test_generate_stream_handles_invalid_json(self, mock_client_class, client):
        """Test that streaming handles invalid JSON gracefully."""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            '{"response": "Valid"}',
            'invalid json',
            '{"response": "Also valid"}',
        ]
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_stream_context = MagicMock()
        mock_stream_context.__enter__.return_value = mock_response
        mock_client.stream.return_value = mock_stream_context
        mock_client_class.return_value = mock_client
        
        result = client.generate("Test prompt", stream=True)
        chunks = list(result)
        
        # Should skip invalid JSON
        assert chunks == ["Valid", "Also valid"]

    @patch('queenbee.llm.httpx.Client')
    def test_chat_sync(self, mock_client_class, client):
        """Test synchronous chat."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {"content": "Chat response"}
        }
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        result = client.chat(messages, stream=False)
        
        assert result == "Chat response"
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/chat"
        assert call_args[1]["json"]["messages"] == messages

    @patch('queenbee.llm.httpx.Client')
    def test_chat_stream(self, mock_client_class, client):
        """Test streaming chat."""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            '{"message": {"content": "Hello"}}',
            '{"message": {"content": " world"}}',
        ]
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_stream_context = MagicMock()
        mock_stream_context.__enter__.return_value = mock_response
        mock_client.stream.return_value = mock_stream_context
        mock_client_class.return_value = mock_client
        
        messages = [{"role": "user", "content": "Test"}]
        result = client.chat(messages, stream=True)
        chunks = list(result)
        
        assert chunks == ["Hello", " world"]

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
