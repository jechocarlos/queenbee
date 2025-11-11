"""Ollama API integration."""

import json
import logging
from typing import Any, AsyncIterator, Iterator

import httpx

from queenbee.config.loader import OllamaConfig

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, config: OllamaConfig):
        """Initialize Ollama client.

        Args:
            config: Ollama configuration.
        """
        self.config = config
        self.base_url = config.host.rstrip("/")
        self.model = config.model
        self.timeout = config.timeout

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        stream: bool = False,
        max_tokens: int | None = None,
    ) -> str | Iterator[str]:
        """Generate text completion.

        Args:
            prompt: User prompt.
            system: Optional system prompt.
            temperature: Sampling temperature.
            stream: Whether to stream the response.
            max_tokens: Maximum number of tokens to generate.

        Returns:
            Generated text or iterator of text chunks.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        if system:
            payload["system"] = system

        logger.debug(f"Ollama request: {url} with model={self.model}")

        if stream:
            return self._generate_stream(url, payload)
        else:
            return self._generate_sync(url, payload)

    def _generate_sync(self, url: str, payload: dict[str, Any]) -> str:
        """Synchronous generation."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")

    def _generate_stream(self, url: str, payload: dict[str, Any]) -> Iterator[str]:
        """Streaming generation."""
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode chunk: {line}")

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str | Iterator[str]:
        """Chat completion with message history.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Sampling temperature.
            stream: Whether to stream the response.

        Returns:
            Generated text or iterator of text chunks.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
            },
        }

        logger.debug(f"Ollama chat request: {url} with {len(messages)} messages")

        if stream:
            return self._chat_stream(url, payload)
        else:
            return self._chat_sync(url, payload)

    def _chat_sync(self, url: str, payload: dict[str, Any]) -> str:
        """Synchronous chat."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")

    def _chat_stream(self, url: str, payload: dict[str, Any]) -> Iterator[str]:
        """Streaming chat."""
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                yield chunk["message"]["content"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode chunk: {line}")

    def list_models(self) -> list[str]:
        """List available models.

        Returns:
            List of model names.
        """
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
