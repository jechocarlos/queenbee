"""Quantifier agent - metrics and data-driven analysis."""

import logging
from uuid import UUID

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType

logger = logging.getLogger(__name__)


class QuantifierAgent(BaseAgent):
    """Quantifier agent provides data-driven, metrics-focused analysis."""

    def __init__(self, session_id: UUID, config: Config, db: DatabaseManager):
        """Initialize Quantifier agent.

        Args:
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        super().__init__(AgentType.QUANTIFIER, session_id, config, db)
        logger.info(f"Quantifier agent initialized: {self.agent_id}")

    def quantify(self, task: str, context: str = "") -> str:
        """Provide quantitative analysis and metrics.

        Args:
            task: Task description.
            context: Optional context from previous conversation.

        Returns:
            Data-driven analysis with specific numbers and metrics.
        """
        logger.info(f"Quantifier agent analyzing metrics: {task[:50]}...")
        
        prompt = f"""
Task: {task}

{f'Context: {context}' if context else ''}

Your role as a Quantifier is to:
1. Define specific, measurable metrics
2. Request concrete numbers and data
3. Establish success criteria with thresholds
4. Challenge vague qualitative claims
5. Provide cost/benefit analysis with actual numbers

Provide data-driven perspective that grounds discussions in measurable outcomes.
"""
        
        response = self.generate_response(prompt)
        return str(response)
