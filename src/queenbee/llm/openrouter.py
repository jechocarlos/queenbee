"""OpenRouter API integration using direct OpenAI client."""

import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Iterator

import httpx
from openai import OpenAI, RateLimitError

from queenbee.config.loader import OpenRouterConfig

if TYPE_CHECKING:
    from queenbee.db.connection import DatabaseManager
    from queenbee.db.models import RateLimitRepository

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API requests."""
    
    def __init__(self, requests_per_minute: int):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute.
        """
        self.requests_per_minute = requests_per_minute
        self.tokens = requests_per_minute
        self.max_tokens = requests_per_minute
        self.last_update = time.time()
        self.cooldown_until = 0.0  # Cooldown period from rate limit headers
        self.lock = threading.Lock()
        
    def set_cooldown(self, reset_timestamp_ms: int) -> None:
        """Set cooldown period based on rate limit reset timestamp.
        
        Args:
            reset_timestamp_ms: Reset timestamp in milliseconds from epoch.
        """
        with self.lock:
            reset_time = reset_timestamp_ms / 1000.0
            self.cooldown_until = max(self.cooldown_until, reset_time)
            wait_time = reset_time - time.time()
            if wait_time > 0:
                logger.warning(f"Rate limit hit, cooling down for {wait_time:.1f}s until {reset_time}")
        
    def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        while True:
            with self.lock:
                now = time.time()
                
                # Check if we're in cooldown period
                if now < self.cooldown_until:
                    # Release lock and wait
                    pass
                else:
                    elapsed = now - self.last_update
                    
                    # Refill tokens based on elapsed time
                    self.tokens = min(
                        self.max_tokens,
                        self.tokens + (elapsed * self.requests_per_minute / 60.0)
                    )
                    self.last_update = now
                    
                    if self.tokens >= 1.0:
                        self.tokens -= 1.0
                        return
            
            # Not enough tokens or in cooldown, wait a bit
            time.sleep(0.1)


class OpenRouterClient:
    """Client for interacting with OpenRouter using OpenAI-compatible API.
    
    This client uses the OpenAI Python SDK configured for OpenRouter's endpoint,
    providing compatibility with the QueenBee framework.
    """

    def __init__(self, config: OpenRouterConfig, db: "DatabaseManager | None" = None):
        """Initialize OpenRouter client.

        Args:
            config: OpenRouter configuration.
            db: Database manager for rate limit persistence (optional).
        """
        self.config = config
        self.base_url = config.base_url
        self.model = config.model
        self.model_id = config.model
        self.timeout = config.timeout
        self.api_key = config.api_key
        
        # Initialize database repository for rate limit tracking
        self.db = db
        self.rate_limit_repo: "RateLimitRepository | None" = None
        if db:
            from queenbee.db.models import RateLimitRepository
            self.rate_limit_repo = RateLimitRepository(db)
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(config.requests_per_minute)
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay
        
        # Check database for existing rate limit
        if self.rate_limit_repo:
            reset_ms = self.rate_limit_repo.get_rate_limit_reset('openrouter', self.model_id)
            if reset_ms and reset_ms > 0:
                self.rate_limiter.set_cooldown(reset_ms)
                logger.info(f"Loaded existing rate limit cooldown until {reset_ms/1000.0}")
        
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
        
        # Acquire rate limit token before making request
        self.rate_limiter.acquire()
        
        # Generate response with retry logic for rate limits
        for attempt in range(self.max_retries):
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
                            if chunk.choices and chunk.choices[0].delta:
                                delta = chunk.choices[0].delta
                                # Try content first (standard models)
                                if delta.content:
                                    yield delta.content
                                # Fall back to reasoning (reasoning models)
                                elif hasattr(delta, 'reasoning') and delta.reasoning:
                                    yield delta.reasoning
                    
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
                    # Handle both standard and reasoning models
                    message = response.choices[0].message
                    content = message.content or ""
                    
                    # For reasoning models (like gpt-oss-20b), extract from reasoning field
                    if not content and hasattr(message, 'reasoning') and message.reasoning:
                        content = message.reasoning
                    
                    return content
            except RateLimitError as e:
                # Extract rate limit reset time from response headers
                if hasattr(e, 'response') and e.response is not None:
                    headers = e.response.headers
                    reset_header = headers.get('X-RateLimit-Reset') or headers.get('x-ratelimit-reset')
                    if reset_header:
                        try:
                            reset_ms = int(reset_header)
                            self.rate_limiter.set_cooldown(reset_ms)
                        except (ValueError, TypeError):
                            pass
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    # Acquire another token for retry
                    self.rate_limiter.acquire()
                else:
                    logger.error(f"Rate limit exceeded after {self.max_retries} attempts")
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
        # Acquire rate limit token before making request
        self.rate_limiter.acquire()
        
        # Retry logic for rate limits
        for attempt in range(self.max_retries):
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
                            if chunk.choices and chunk.choices[0].delta:
                                delta = chunk.choices[0].delta
                                # Try content first (standard models)
                                if delta.content:
                                    yield delta.content
                                # Fall back to reasoning (reasoning models)
                                elif hasattr(delta, 'reasoning') and delta.reasoning:
                                    yield delta.reasoning
                    
                    return stream_generator()
                else:
                    response = self.client.chat.completions.create(
                        model=self.model_id,
                        messages=messages,  # type: ignore
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=False,
                    )
                    # Handle both standard and reasoning models
                    message = response.choices[0].message
                    content = message.content or ""
                    
                    # For reasoning models (like gpt-oss-20b), extract from reasoning field
                    if not content and hasattr(message, 'reasoning') and message.reasoning:
                        content = message.reasoning
                    
                    return content
            except RateLimitError as e:
                # Extract rate limit reset time from response headers
                if hasattr(e, 'response') and e.response is not None:
                    headers = e.response.headers
                    reset_header = headers.get('X-RateLimit-Reset') or headers.get('x-ratelimit-reset')
                    if reset_header:
                        try:
                            reset_ms = int(reset_header)
                            self.rate_limiter.set_cooldown(reset_ms)
                        except (ValueError, TypeError):
                            pass
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    # Acquire another token for retry
                    self.rate_limiter.acquire()
                else:
                    logger.error(f"Rate limit exceeded after {self.max_retries} attempts")
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
