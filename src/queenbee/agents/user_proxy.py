"""User Proxy agent - represents end-user perspective."""

import logging
from uuid import UUID

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType

logger = logging.getLogger(__name__)


class UserProxyAgent(BaseAgent):
    """User Proxy agent represents the end-user perspective and needs."""

    def __init__(self, session_id: UUID, config: Config, db: DatabaseManager):
        """Initialize User Proxy agent.

        Args:
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        super().__init__(AgentType.USER_PROXY, session_id, config, db)
        logger.info(f"User Proxy agent initialized: {self.agent_id}")

    def advocate_for_user(self, task: str, context: str = "") -> str:
        """Advocate for end-user needs and perspective.

        Args:
            task: Task description.
            context: Optional context from previous conversation.

        Returns:
            User-focused perspective on the proposed solutions.
        """
        logger.info(f"User Proxy agent advocating for users: {task[:50]}...")
        
        prompt = f"""
Task: {task}

{f'Context: {context}' if context else ''}

Your role as a User Proxy is to:
1. Represent the end-user perspective
2. Focus on user needs and experience
3. Challenge technical complexity that doesn't serve users
4. Advocate for usability and accessibility
5. Ground technical discussions in user value

Provide perspective that keeps the focus on actual user needs and value.
"""
        
        response = self.generate_response(prompt)
        return str(response)
