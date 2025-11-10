"""Summarizer agent - generates rolling summaries and final synthesis."""

import logging
from typing import Iterator, Union
from uuid import UUID

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType

logger = logging.getLogger(__name__)


class SummarizerAgent(BaseAgent):
    """Summarizer agent that generates rolling summaries and final synthesis."""

    def __init__(self, session_id: UUID, config: Config, db: DatabaseManager):
        """Initialize Summarizer agent.

        Args:
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        super().__init__(AgentType.SUMMARIZER, session_id, config, db)
        logger.info(f"Summarizer agent initialized: {self.agent_id}")

    def generate_rolling_summary(
        self,
        user_input: str,
        contributions: list[dict],
        stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """Generate a rolling summary of the ongoing discussion.

        Args:
            user_input: Original user question.
            contributions: List of contributions so far.
            stream: Whether to stream the response.

        Returns:
            Rolling summary text or iterator of chunks.
        """
        if not contributions:
            return "No contributions yet."

        # Format contributions focusing on content
        discussion_text = []
        for contrib in contributions:
            agent = contrib["agent"]
            content = contrib["content"]
            discussion_text.append(f"**{agent}:** {content}")

        discussion_str = "\n\n".join(discussion_text)

        # Create focused summarization prompt
        prompt = f"""Question: "{user_input}"

Here are the {len(contributions)} expert contributions made so far:

{discussion_str}

Provide a BRIEF summary (2-3 sentences max) of the KEY INSIGHTS and MAIN POINTS that have emerged. Focus on WHAT the experts are saying about the question, not the discussion process."""

        # Use lower temperature for consistent, focused summarization
        response = self.ollama.generate(
            prompt=prompt,
            system="You are a concise summarizer. Extract and synthesize key insights from expert discussions. Focus on the substance of what's being discussed, not meta-commentary about the discussion itself.",
            temperature=0.3,
            stream=stream
        )

        return response

    def generate_final_synthesis(
        self,
        user_input: str,
        contributions: list[dict],
        rolling_summary: str = "",
        stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """Generate final comprehensive synthesis of the discussion.

        Args:
            user_input: Original user question.
            contributions: Complete list of contributions.
            rolling_summary: Last rolling summary generated.
            stream: Whether to stream the response.

        Returns:
            Final synthesis text or iterator of chunks.
        """
        if not contributions:
            return "No discussion occurred."

        # Format complete discussion
        discussion_text = []
        for i, contrib in enumerate(contributions, 1):
            agent = contrib["agent"]
            content = contrib["content"]
            discussion_text.append(f"{i}. {agent}: {content}")

        discussion_str = "\n\n".join(discussion_text)

        # Include rolling summary context if available
        rolling_context = ""
        if rolling_summary:
            rolling_context = f"""
ROLLING SUMMARY (generated during discussion):
{rolling_summary}

"""

        # Create synthesis prompt
        prompt = f"""Question: "{user_input}"

{rolling_context}COMPLETE DISCUSSION ({len(contributions)} contributions):
{discussion_str}

Synthesize this discussion into a clear, comprehensive answer. Focus on:
1. The KEY INSIGHTS and RECOMMENDATIONS from the specialists
2. Any critical concerns or trade-offs identified
3. A direct, actionable answer to the user's question

Your response should focus on WHAT WAS DISCUSSED (the substance), not how the discussion proceeded.
Keep it concise: 4-5 sentences maximum."""

        # Use slightly higher temperature for synthesis
        response = self.ollama.generate(
            prompt=prompt,
            system="You are an expert synthesizer. Create comprehensive yet concise summaries that capture the essence of multi-perspective discussions. Focus on insights, recommendations, and actionable conclusions.",
            temperature=0.4,
            stream=stream
        )

        return response
