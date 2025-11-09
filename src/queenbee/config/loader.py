"""Configuration loader and settings."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="queenbee")
    user: str = Field(default="queenbee")
    password: str
    ssl_mode: str = Field(default="prefer")

    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.name}?sslmode={self.ssl_mode}"
        )


class OllamaConfig(BaseSettings):
    """Ollama configuration."""

    host: str = Field(default="http://localhost:11434")
    model: str = Field(default="llama3.1:8b")
    timeout: int = Field(default=120)


class AgentTTLConfig(BaseSettings):
    """Agent TTL configuration."""

    idle_timeout_minutes: int = Field(default=10)
    check_interval_seconds: int = Field(default=30)


class AgentPromptConfig(BaseSettings):
    """Agent prompt configuration."""

    system_prompt_file: str
    max_iterations: int = Field(default=5)
    complexity_threshold: str = Field(default="auto")


class AgentsConfig(BaseSettings):
    """Agents configuration."""

    ttl: AgentTTLConfig
    max_concurrent_specialists: int = Field(default=10)
    queen: AgentPromptConfig
    divergent: AgentPromptConfig
    convergent: AgentPromptConfig
    critical: AgentPromptConfig


class ConsensusConfig(BaseSettings):
    """Consensus configuration."""

    max_rounds: int = Field(default=10)
    agreement_threshold: str = Field(default="all")


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO")
    format: str = Field(default="json")
    output: str = Field(default="stdout")


class SystemConfig(BaseSettings):
    """System configuration."""

    name: str = Field(default="queenbee")
    version: str = Field(default="1.0.0")
    environment: str = Field(default="development")


class Config(BaseSettings):
    """Main configuration."""

    system: SystemConfig
    database: DatabaseConfig
    ollama: OllamaConfig
    agents: AgentsConfig
    consensus: ConsensusConfig
    logging: LoggingConfig


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file with environment variable substitution.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Config: Loaded configuration object.
    """
    # Load environment variables
    load_dotenv()

    # Load YAML config
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r") as f:
        raw_config = yaml.safe_load(f)

    # Substitute environment variables
    config_dict = _substitute_env_vars(raw_config)

    # Convert nested dicts to proper config objects
    return Config(**config_dict)


def _substitute_env_vars(config: Any) -> Any:
    """Recursively substitute environment variables in config.

    Environment variables are specified as ${VAR_NAME:default_value}
    """
    if isinstance(config, dict):
        return {key: _substitute_env_vars(value) for key, value in config.items()}
    elif isinstance(config, list):
        return [_substitute_env_vars(item) for item in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        # Extract variable name and default value
        var_spec = config[2:-1]  # Remove ${ and }
        if ":" in var_spec:
            var_name, default_value = var_spec.split(":", 1)
            return os.getenv(var_name, default_value)
        else:
            var_name = var_spec
            value = os.getenv(var_name)
            if value is None:
                raise ValueError(f"Environment variable {var_name} is required but not set")
            return value
    else:
        return config
