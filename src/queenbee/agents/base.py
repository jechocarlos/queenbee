"""Base agent implementation."""

import logging
import os
from pathlib import Path
from typing import Iterator, Union
from uuid import UUID

from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentRepository, AgentStatus, AgentType
from queenbee.llm import OllamaClient

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents."""

    def __init__(
        self,
        agent_type: AgentType,
        session_id: UUID,
        config: Config,
        db: DatabaseManager,
    ):
        """Initialize agent.

        Args:
            agent_type: Type of agent.
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        self.agent_type = agent_type
        self.session_id = session_id
        self.config = config
        self.db = db
        self.agent_repo = AgentRepository(db)
        
        # Get inference pack for this agent type
        pack_name = self._get_inference_pack_name()
        inference_pack = config.inference_packs.packs.get(pack_name)
        
        if not inference_pack:
            logger.warning(f"Inference pack '{pack_name}' not found for {agent_type}, using defaults")
            inference_pack = None
        
        # Initialize LLM based on inference pack or environment variable
        if inference_pack:
            # Use inference pack configuration
            if inference_pack.provider == "openrouter":
                from queenbee.llm.openrouter import OpenRouterClient
                self.llm = OpenRouterClient(config.openrouter, db, inference_pack)
                logger.info(f"Agent {agent_type} using inference pack '{pack_name}' with model {inference_pack.model}")
            else:  # ollama
                from queenbee.llm import OllamaClient

                # Create custom config for this pack
                ollama_config = config.ollama.model_copy()
                ollama_config.model = inference_pack.model
                self.llm = OllamaClient(ollama_config)
                logger.info(f"Agent {agent_type} using inference pack '{pack_name}' with Ollama model {inference_pack.model}")
        elif os.environ.get('QUEENBEE_USE_OPENROUTER'):
            # Fallback to environment variable detection
            from queenbee.llm.openrouter import OpenRouterClient
            self.llm = OpenRouterClient(config.openrouter, db)
            logger.info(f"Agent {agent_type} initialized with OpenRouter (default)")
        else:
            from queenbee.llm import OllamaClient
            self.llm = OllamaClient(config.ollama)
            logger.info(f"Agent {agent_type} initialized with Ollama (default)")
        
        # Store inference pack for later use
        self.inference_pack = inference_pack
        
        # Keep ollama for backward compatibility
        self.ollama = self.llm

        # Load system prompt
        self.system_prompt = self._load_system_prompt()

        # Create agent record in database
        self.agent_id = self.agent_repo.create_agent(
            agent_type=agent_type,
            session_id=session_id,
            system_prompt=self.system_prompt,
            configuration=self._get_agent_config(),
        )

        logger.info(f"Initialized {agent_type.value} agent: {self.agent_id}")

    def _get_inference_pack_name(self) -> str:
        """Get inference pack name for this agent type.

        Returns:
            Inference pack name from configuration.
        """
        if self.agent_type == AgentType.QUEEN:
            return self.config.agent_inference.queen
        elif self.agent_type == AgentType.DIVERGENT:
            return self.config.agent_inference.divergent
        elif self.agent_type == AgentType.CONVERGENT:
            return self.config.agent_inference.convergent
        elif self.agent_type == AgentType.CRITICAL:
            return self.config.agent_inference.critical
        elif self.agent_type == AgentType.SUMMARIZER:
            return self.config.agent_inference.summarizer
        elif self.agent_type == AgentType.WEB_SEARCHER:
            return self.config.agent_inference.web_searcher
        else:
            return "standard"

    def _load_system_prompt(self) -> str:
        """Load system prompt from file.

        Returns:
            System prompt text.
        """
        # Get prompt file path based on agent type
        if self.agent_type == AgentType.QUEEN:
            prompt_file = self.config.agents.queen.system_prompt_file
        elif self.agent_type == AgentType.DIVERGENT:
            prompt_file = self.config.agents.divergent.system_prompt_file
        elif self.agent_type == AgentType.CONVERGENT:
            prompt_file = self.config.agents.convergent.system_prompt_file
        elif self.agent_type == AgentType.CRITICAL:
            prompt_file = self.config.agents.critical.system_prompt_file
        elif self.agent_type == AgentType.SUMMARIZER:
            prompt_file = self.config.agents.summarizer.system_prompt_file
        elif self.agent_type == AgentType.WEB_SEARCHER:
            prompt_file = self.config.agents.web_searcher.system_prompt_file
        else:
            raise ValueError(f"Unknown agent type: {self.agent_type}")

        prompt_path = Path(prompt_file)
        if not prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found: {prompt_file}")

        with open(prompt_path, "r") as f:
            prompt = f.read()

        logger.debug(f"Loaded prompt for {self.agent_type.value} from {prompt_file}")
        return prompt

    def _get_agent_config(self) -> dict:
        """Get agent-specific configuration.

        Returns:
            Configuration dictionary.
        """
        if self.agent_type == AgentType.QUEEN:
            return {
                "complexity_threshold": self.config.agents.queen.complexity_threshold,
            }
        elif self.agent_type in [AgentType.DIVERGENT, AgentType.CONVERGENT, AgentType.CRITICAL, AgentType.SUMMARIZER]:
            if self.agent_type == AgentType.DIVERGENT:
                specialist_config = self.config.agents.divergent
            elif self.agent_type == AgentType.CONVERGENT:
                specialist_config = self.config.agents.convergent
            elif self.agent_type == AgentType.CRITICAL:
                specialist_config = self.config.agents.critical
            else:  # SUMMARIZER
                specialist_config = self.config.agents.summarizer

            return {
                "max_iterations": specialist_config.max_iterations,
            }
        return {}

    def update_status(self, status: AgentStatus) -> None:
        """Update agent status.

        Args:
            status: New status.
        """
        self.agent_repo.update_agent_status(self.agent_id, status)

    def record_activity(self) -> None:
        """Record agent activity (resets TTL)."""
        self.agent_repo.update_agent_activity(self.agent_id)

    def generate_response(self, prompt: str, temperature: float = 0.7, stream: bool = False, max_tokens: int | None = None) -> Union[str, Iterator[str]]:
        """Generate response using Ollama.

        Args:
            prompt: User prompt.
            temperature: Sampling temperature.
            stream: Whether to enable streaming (returns iterator if True).
            max_tokens: Maximum number of tokens to generate.

        Returns:
            Generated response (str) or iterator of response chunks (Iterator[str]).
        """
        self.record_activity()
        response = self.ollama.generate(
            prompt=prompt,
            system=self.system_prompt,
            temperature=temperature,
            stream=stream,
            max_tokens=max_tokens,
        )
        return response

    def terminate(self) -> None:
        """Terminate agent."""
        self.update_status(AgentStatus.TERMINATED)
        logger.info(f"Terminated agent: {self.agent_id}")
