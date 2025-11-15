"""Pragmatist agent - implementation reality check."""

import logging
from uuid import UUID

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType

logger = logging.getLogger(__name__)


class PragmatistAgent(BaseAgent):
    """Pragmatist agent validates practical feasibility and implementation constraints."""

    def __init__(self, session_id: UUID, config: Config, db: DatabaseManager):
        """Initialize Pragmatist agent.

        Args:
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        super().__init__(AgentType.PRAGMATIST, session_id, config, db)
        logger.info(f"Pragmatist agent initialized: {self.agent_id}")

    def validate_feasibility(self, task: str, context: str = "") -> str:
        """Validate practical feasibility of proposed solutions.

        Args:
            task: Task description.
            context: Optional context from previous conversation.

        Returns:
            Feasibility assessment with practical considerations.
        """
        logger.info(f"Pragmatist agent validating feasibility: {task[:50]}...")
        
        prompt = f"""
Task: {task}

{f'Context: {context}' if context else ''}

Your role as a Pragmatist is to:
1. Assess practical feasibility (time, resources, skills)
2. Identify implementation constraints
3. Suggest realistic execution approaches
4. Balance idealism with pragmatism
5. Ground discussions in reality

Provide a practical perspective that helps turn ideas into achievable action.
"""
        
        response = self.generate_response(prompt)
        return str(response)
