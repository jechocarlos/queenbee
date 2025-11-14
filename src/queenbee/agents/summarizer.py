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

Provide a comprehensive summary of the KEY INSIGHTS, MAIN POINTS, and RECOMMENDATIONS that have emerged so far. 

Include:
- What perspectives have been shared
- Key recommendations or solutions proposed
- Important trade-offs or concerns raised
- Current direction of the discussion

Be thorough but concise - aim for a complete picture that would help someone understand the discussion without reading every contribution. 4-6 sentences is ideal."""

        # Use lower temperature for consistent, focused summarization
        response = self.ollama.generate(
            prompt=prompt,
            system="You are an expert summarizer who creates comprehensive yet clear summaries. Extract and synthesize key insights from expert discussions, ensuring all important points are captured. Focus on the substance of what's being discussed, not meta-commentary about the discussion itself.",
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

Synthesize this discussion into a clear, comprehensive answer that directly addresses the user's question.

Your synthesis should:
1. Start with a direct answer to the question
2. Include KEY INSIGHTS and RECOMMENDATIONS from the specialists
3. Cover important TRADE-OFFS, CONCERNS, or CONSIDERATIONS raised
4. Provide ACTIONABLE next steps or conclusions

Be thorough and complete - this is the final response the user will see. The answer should stand on its own and fully address their question. Aim for 6-10 sentences to provide a comprehensive response."""

        # Use slightly higher temperature for synthesis
        response = self.ollama.generate(
            prompt=prompt,
            system="You are an expert synthesizer who creates thorough, well-structured answers. Synthesize multi-perspective discussions into complete, actionable responses that directly answer the user's question. Be comprehensive - users rely on this as their final answer.",
            temperature=0.4,
            stream=stream
        )

        return response
