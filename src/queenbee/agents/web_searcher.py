"""Web Searcher agent - performs web searches for other agents."""

import logging
from typing import Iterator, Union
from uuid import UUID

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType

logger = logging.getLogger(__name__)


class WebSearcherAgent(BaseAgent):
    """Web Searcher agent that performs web searches using OpenRouter models with search capability."""

    def __init__(self, session_id: UUID, config: Config, db: DatabaseManager):
        """Initialize Web Searcher agent.

        Args:
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        super().__init__(AgentType.WEB_SEARCHER, session_id, config, db)
        
        # Verify this agent is using OpenRouter with a search-capable model
        if not hasattr(self.llm, 'base_url') or 'openrouter' not in str(self.llm.base_url).lower():
            logger.warning("WebSearcher agent should use OpenRouter for web search capability")

    def search(
        self, 
        query: str, 
        requesting_agent: str = "unknown",
        stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """Perform a web search and return results.

        Args:
            query: Search query from requesting agent.
            requesting_agent: Name of the agent requesting the search.
            stream: Whether to stream the response.

        Returns:
            Search results as string or iterator of chunks.
        """
        logger.info(f"Web search requested by {requesting_agent}: {query[:100]}")

        # Build search prompt that instructs the model to use web search
        search_prompt = f"""Perform a web search to answer the following query:

{query}

Instructions:
- Use your web search capability to find current, accurate information
- Provide factual results with sources when possible
- Keep the response focused and relevant to the query
- If multiple sources have different information, note the differences
- If information is not found, clearly state that

Search results:"""

        try:
            # Use the agent's LLM (should be a search-capable OpenRouter model)
            response = self.generate_response(
                prompt=search_prompt,
                stream=stream,
                temperature=0.3  # Lower temperature for more factual responses
            )
            
            if not stream:
                logger.info(f"Web search completed for {requesting_agent}")
            
            return response

        except Exception as e:
            error_msg = f"Web search failed: {str(e)}"
            logger.error(f"{error_msg} (requested by {requesting_agent})")
            return error_msg

    def generate_response(
        self, 
        prompt: str,
        temperature: float = 0.3,
        stream: bool = False,
        max_tokens: int | None = None
    ) -> Union[str, Iterator[str]]:
        """Generate response using the web search model.

        Args:
            prompt: Input prompt.
            temperature: Sampling temperature.
            stream: Whether to stream the response.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated response or iterator of chunks.
        """
        try:
            response = self.llm.generate(
                prompt=prompt,
                system=self.system_prompt,
                temperature=temperature,
                stream=stream,
                max_tokens=max_tokens,
            )
            return response
        except Exception as e:
            logger.error(f"Error generating web search response: {e}")
            raise
