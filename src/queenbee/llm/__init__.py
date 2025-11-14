"""Ollama API integration using Agno."""

import logging
from typing import Iterator

import httpx
from agno.agent import Agent
from agno.models.ollama import Ollama

from queenbee.config.loader import OllamaConfig

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama using Agno.
    
    This client wraps Agno's Ollama model to provide a consistent interface
    for the QueenBee framework while leveraging Agno's capabilities.
    """

    def __init__(self, config: OllamaConfig):
        """Initialize Ollama client with Agno.

        Args:
            config: Ollama configuration.
        """
        self.config = config
        self.base_url = config.host.rstrip("/")
        self.model = config.model  # Keep model as string for compatibility
        self.model_id = config.model
        self.timeout = config.timeout
        
        # Create base Agno Ollama model instance
        self._agno_model = Ollama(
            id=self.model_id,
            host=self.base_url,
            timeout=self.timeout,
        )
        
        logger.info(f"Initialized Agno Ollama client: model={self.model_id}, host={self.base_url}")

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        stream: bool = False,
        max_tokens: int | None = None,
    ) -> str | Iterator[str]:
        """Generate text completion using Agno.

        Args:
            prompt: User prompt.
            system: Optional system prompt.
            temperature: Sampling temperature.
            stream: Whether to stream the response.
            max_tokens: Maximum number of tokens to generate.

        Returns:
            Generated text or iterator of text chunks.
        """
        # Configure model options
        options = {"temperature": temperature}
        if max_tokens and max_tokens > 0:
            options["num_predict"] = max_tokens
        
        # Create Ollama model with options
        model = Ollama(
            id=self.model_id,
            host=self.base_url,
            timeout=self.timeout,
            options=options,
        )
        
        # Create Agno agent with the model
        # Use description for system prompt (Agno v2 best practice)
        agent = Agent(
            model=model,
            description=system,  # System prompt goes here in Agno v2
            markdown=False,
        )
        
        logger.debug(f"Agno request: model={self.model_id}, stream={stream}, temp={temperature}, max_tokens={max_tokens}")
        
        if stream:
            return self._stream_response(agent, prompt)
        else:
            # Get complete response
            response = agent.run(prompt, stream=False)
            return self._extract_content(response)

    def _extract_content(self, response) -> str:
        """Extract text content from Agno response.
        
        Args:
            response: Agno RunOutput response.
            
        Returns:
            Text content.
        """
        if hasattr(response, 'content') and response.content:
            return str(response.content)
        elif hasattr(response, 'text') and response.text:
            return str(response.text)
        elif hasattr(response, 'messages') and response.messages:
            # Extract from last message
            last_msg = response.messages[-1]
            if hasattr(last_msg, 'content'):
                return str(last_msg.content)
        return str(response)

    def _stream_response(self, agent: Agent, prompt: str) -> Iterator[str]:
        """Stream response from Agno agent.
        
        Args:
            agent: Agno Agent instance.
            prompt: User prompt.
            
        Yields:
            Text chunks from the response.
        """
        try:
            # Use Agno's streaming capability
            response_stream = agent.run(prompt, stream=True)
            
            for event in response_stream:
                # Try to extract content from event
                content = None
                
                # First try .content attribute
                if hasattr(event, 'content'):
                    content = event.content
                # Then try .delta attribute (for streaming events)
                elif hasattr(event, 'delta'):
                    delta = event.delta  # type: ignore
                    # Only yield if delta is a non-empty string (not Mock)
                    if delta and isinstance(delta, str):
                        content = delta
                
                # Yield only if we have valid string content
                if content and isinstance(content, str):
                    yield content
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str | Iterator[str]:
        """Chat completion with message history using Agno.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Sampling temperature.
            stream: Whether to stream the response.

        Returns:
            Generated text or iterator of text chunks.
        """
        # Prepare model options
        options = {"temperature": temperature}
        
        # Convert messages to Agno format
        # Extract system message if present
        system_msg = None
        user_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content")
            else:
                user_messages.append(msg)
        
        # Create Ollama model with specific options
        model = Ollama(
            id=self.model_id,
            host=self.base_url,
            timeout=self.timeout,
            options=options,
        )
        
        # Create agent with system message as description (Agno v2 pattern)
        agent = Agent(
            model=model,
            description=system_msg,
            markdown=False,
        )
        
        # Get the last user message as the prompt
        last_message = user_messages[-1].get("content", "") if user_messages else ""
        
        logger.debug(f"Chat with Agno Ollama: {len(messages)} messages, stream={stream}")
        
        if stream:
            return self._stream_response(agent, last_message)
        else:
            response = agent.run(last_message, stream=False)
            return self._extract_content(response)

    def list_models(self) -> list[str]:
        """List available models.

        Returns:
            List of model names.
        """
        # This still uses direct API call since Agno doesn't provide a list method
        url = f"{self.base_url}/api/tags"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            result = response.json()
            return [model["name"] for model in result.get("models", [])]

    def is_available(self) -> bool:
        """Check if Ollama server is available.

        Returns:
            True if server is reachable.
        """
        try:
            url = f"{self.base_url}/api/tags"
            with httpx.Client(timeout=5) as client:
                response = client.get(url)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

