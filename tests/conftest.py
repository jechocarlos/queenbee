"""Pytest configuration and shared fixtures."""

import os
from pathlib import Path
from typing import Generator
from uuid import uuid4

import pytest

# Set test environment
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "queenbee_test"
os.environ["DB_USER"] = "queenbee"
os.environ["DB_PASSWORD"] = "test_password"
os.environ["OLLAMA_HOST"] = "http://localhost:11434"


@pytest.fixture
def config_yaml_content() -> str:
    """Sample config.yaml content for testing."""
    return """
system:
  name: queenbee
  version: 1.0.0
  environment: test

database:
  host: localhost
  port: 5432
  name: queenbee_test
  user: queenbee
  password: test_password
  ssl_mode: prefer

ollama:
  host: http://localhost:11434
  model: llama3.1:8b
  timeout: 300

openrouter:
  api_key: test_api_key
  model: anthropic/claude-3.5-sonnet
  timeout: 300
  base_url: https://openrouter.ai/api/v1

agents:
  ttl:
    idle_timeout_minutes: 10
    check_interval_seconds: 30
  
  max_concurrent_specialists: 10
  
  queen:
    system_prompt_file: ./prompts/queen.md
    complexity_threshold: auto
  
  divergent:
    system_prompt_file: ./prompts/divergent.md
    max_iterations: 10
  
  convergent:
    system_prompt_file: ./prompts/convergent.md
    max_iterations: 10
  
  critical:
    system_prompt_file: ./prompts/critical.md
    max_iterations: 10
  
  summarizer:
    system_prompt_file: ./prompts/summarizer.md
    max_iterations: 5

consensus:
  max_rounds: 10
  agreement_threshold: "all"
  discussion_rounds: 10
  specialist_timeout_seconds: 300

logging:
  level: DEBUG
  format: json
  output: stdout
"""


@pytest.fixture
def test_session_id():
    """Generate a test session ID."""
    return uuid4()


@pytest.fixture
def test_agent_id():
    """Generate a test agent ID."""
    return uuid4()


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        "model": "llama3.1:8b",
        "created_at": "2025-11-10T12:00:00Z",
        "response": "This is a test response from the agent.",
        "done": True
    }


@pytest.fixture
def sample_discussion():
    """Sample discussion for testing."""
    return [
        {
            "agent": "Divergent",
            "content": "Consider using microservices for scalability.",
            "timestamp": 1699632000.0,
            "contribution_num": 1
        },
        {
            "agent": "Convergent",
            "content": "Balance microservices complexity with monolith simplicity.",
            "timestamp": 1699632002.0,
            "contribution_num": 1
        },
        {
            "agent": "Critical",
            "content": "Watch out for distributed system complexity and debugging challenges.",
            "timestamp": 1699632004.0,
            "contribution_num": 1
        }
    ]


@pytest.fixture
def temp_config_file(tmp_path: Path, config_yaml_content: str):
    """Create a temporary config file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_yaml_content)
    return config_file
