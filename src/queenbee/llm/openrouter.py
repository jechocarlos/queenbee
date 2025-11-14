"""OpenRouter API integration using direct OpenAI client."""

import logging
import time
from typing import Any, Iterator

import httpx
from openai import OpenAI, RateLimitError

from queenbee.config.loader import OpenRouterConfig

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client for interacting with OpenRouter using OpenAI-compatible API.
    
    This client uses the OpenAI Python SDK configured for OpenRouter's endpoint,
    providing compatibility with the QueenBee framework.
    """

    def __init__(self, config: OpenRouterConfig):
        """Initialize OpenRouter client.

        Args:
            config: OpenRouter configuration.
        """
        self.config = config
        self.base_url = config.base_url
        self.model = config.model
        self.model_id = config.model
        self.timeout = config.timeout
        self.api_key = config.api_key
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY in .env file.")
        
        # Create HTTP client with optional SSL verification
        http_client = httpx.Client(verify=config.verify_ssl) if not config.verify_ssl else None
        if not config.verify_ssl:
            logger.warning("SSL verification disabled for OpenRouter - use only for testing!")
        
        # Create OpenAI client configured for OpenRouter
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            default_headers={
                "HTTP-Referer": "https://github.com/jechocarlos/queenbee",
                "X-Title": "QueenBee",
            },
            http_client=http_client,
        )
        
        logger.info(f"Initialized OpenRouter client: model={self.model_id}")

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        stream: bool = False,
        max_tokens: int | None = None,
    ) -> str | Iterator[str]:
        """Generate a response using OpenRouter.

        Args:
            prompt: User prompt.
            system: System prompt (optional).
            temperature: Sampling temperature (0.0 to 1.0).
            stream: Whether to stream the response.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text or iterator of text chunks if streaming.
        """
        # Build messages for chat-based API
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        # Generate response with retry logic for rate limits
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                if stream:
                    # Streaming response
                    response = self.client.chat.completions.create(
                        model=self.model_id,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                    
                    def stream_generator():
                        for chunk in response:  # type: ignore
                            if chunk.choices and chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
                    
                    return stream_generator()
                else:
                    # Non-streaming response
                    response = self.client.chat.completions.create(
                        model=self.model_id,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=False,
                    )
                    return response.choices[0].message.content or ""
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Rate limit exceeded after {max_retries} attempts")
                    logger.error(f"Model: {self.model_id}, Base URL: {self.base_url}")
                    raise
            except Exception as e:
                logger.error(f"OpenRouter API error: {e}", exc_info=True)
                logger.error(f"Model: {self.model_id}, Base URL: {self.base_url}")
                logger.error(f"Messages: {messages}")
                raise
        
        # Should never reach here due to raise in exception handlers
        return ""

    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        stream: bool = False,
        max_tokens: int | None = None,
    ) -> str | Iterator[str]:
        """Chat completion using OpenRouter.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Sampling temperature.
            stream: Whether to stream the response.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text or iterator of text chunks if streaming.
        """
        # Retry logic for rate limits
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                if stream:
                    response = self.client.chat.completions.create(
                        model=self.model_id,
                        messages=messages,  # type: ignore
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                    
                    def stream_generator():
                        for chunk in response:  # type: ignore
                            if chunk.choices and chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
                    
                    return stream_generator()
                else:
                    response = self.client.chat.completions.create(
                        model=self.model_id,
                        messages=messages,  # type: ignore
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=False,
                    )
                    return response.choices[0].message.content or ""
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Rate limit exceeded after {max_retries} attempts")
                    raise
            except Exception as e:
                logger.error(f"OpenRouter API error: {e}")
                raise
        
        return ""

    def is_available(self) -> bool:
        """Check if OpenRouter API is available.

        Returns:
            True if API is reachable and key is valid.
        """
        try:
            # Simple test request
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                stream=False,
            )
            return True
        except Exception as e:
            logger.error(f"OpenRouter API unavailable: {e}")
            return False

    def list_models(self) -> list[str]:
        """List available models (placeholder).

        Returns:
            List of model names.
        """
        # OpenRouter doesn't have a simple list endpoint via this interface
        # Return the configured model
        return [self.model_id]
