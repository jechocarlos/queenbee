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
    ssl_mode: str = Field(default="disable")  # Use "require" for remote databases

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


class OpenRouterConfig(BaseSettings):
    """OpenRouter configuration."""

    api_key: str = Field(default="")
    model: str = Field(default="anthropic/claude-3.5-sonnet")
    timeout: int = Field(default=120)
    base_url: str = Field(default="https://openrouter.ai/api/v1")
    verify_ssl: bool = Field(default=True)  # Allow disabling SSL verification for testing
    
    # Rate limiting configuration
    requests_per_minute: int = Field(default=16)  # Free tier default
    max_retries: int = Field(default=3)
    retry_delay: int = Field(default=5)  # Base delay in seconds


class InferencePack(BaseSettings):
    """Inference pack configuration for specific use cases."""

    model: str = Field(..., description="Model identifier (e.g., 'openai/gpt-4o-mini' or 'llama3.1:8b')")
    extract_reasoning: bool = Field(default=False, description="Extract from reasoning field for reasoning models")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=0, description="Max tokens (0 = no limit)")


class ProviderPacksConfig(BaseSettings):
    """Collection of inference packs for a specific provider."""

    default_pack: str = Field(default="standard", description="Default pack name for this provider")
    packs: dict[str, InferencePack] = Field(default_factory=dict)


class InferencePacksConfig(BaseSettings):
    """Collection of inference packs grouped by provider."""

    openrouter: ProviderPacksConfig = Field(default_factory=ProviderPacksConfig)
    ollama: ProviderPacksConfig = Field(default_factory=ProviderPacksConfig)


class AgentInferenceConfig(BaseSettings):
    """Agent-specific inference pack assignments."""

    queen: str = Field(default="standard", description="Inference pack name for queen agent")
    divergent: str = Field(default="standard", description="Inference pack name for divergent agent")
    convergent: str = Field(default="standard", description="Inference pack name for convergent agent")
    critical: str = Field(default="standard", description="Inference pack name for critical agent")
    pragmatist: str = Field(default="reasoning", description="Inference pack name for pragmatist agent")
    user_proxy: str = Field(default="standard", description="Inference pack name for user proxy agent")
    quantifier: str = Field(default="reasoning", description="Inference pack name for quantifier agent")
    summarizer: str = Field(default="standard", description="Inference pack name for summarizer agent")
    web_searcher: str = Field(default="web_search", description="Inference pack name for web searcher agent")


class AgentTTLConfig(BaseSettings):
    """Agent TTL configuration."""

    idle_timeout_minutes: int = Field(default=10)
    check_interval_seconds: int = Field(default=30)


class AgentPromptConfig(BaseSettings):
    """Agent prompt configuration."""

    system_prompt_file: str
    max_iterations: int = Field(default=5)
    complexity_threshold: str = Field(default="auto")
    max_tokens: int = Field(default=0)  # 0 means no limit


class AgentsConfig(BaseSettings):
    """Agents configuration."""

    ttl: AgentTTLConfig
    max_concurrent_specialists: int = Field(default=10)
    queen: AgentPromptConfig
    divergent: AgentPromptConfig
    convergent: AgentPromptConfig
    critical: AgentPromptConfig
    pragmatist: AgentPromptConfig
    user_proxy: AgentPromptConfig
    quantifier: AgentPromptConfig
    summarizer: AgentPromptConfig
    web_searcher: AgentPromptConfig


class ConsensusConfig(BaseSettings):
    """Consensus configuration."""

    max_rounds: int = Field(default=10)
    agreement_threshold: str = Field(default="all")
    discussion_rounds: int = Field(default=3)
    specialist_timeout_seconds: int = Field(default=300)  # 5 minutes
    summary_interval_seconds: int = Field(default=10)  # How often to update rolling summary


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
    openrouter: OpenRouterConfig
    inference_packs: InferencePacksConfig = Field(default_factory=InferencePacksConfig)
    agent_inference: AgentInferenceConfig = Field(default_factory=AgentInferenceConfig)
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
