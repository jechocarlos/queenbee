"""Divergent agent - explores multiple perspectives."""

import logging
from uuid import UUID

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType

logger = logging.getLogger(__name__)


class DivergentAgent(BaseAgent):
    """Divergent agent generates creative solutions and explores possibilities."""

    def __init__(self, session_id: UUID, config: Config, db: DatabaseManager):
        """Initialize Divergent agent.

        Args:
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        super().__init__(AgentType.DIVERGENT, session_id, config, db)
        logger.info(f"Divergent agent initialized: {self.agent_id}")

    def explore(self, task: str, context: str = "") -> list[str]:
        """Explore multiple perspectives and generate diverse options.

        Args:
            task: Task description.
            context: Optional context from previous conversation.

        Returns:
            List of diverse perspectives/options.
        """
        logger.info(f"Divergent agent exploring task: {task[:50]}...")
        
        prompt = f"""
Task: {task}

{f'Context: {context}' if context else ''}

Your role as a Divergent thinker is to:
1. Generate multiple diverse perspectives
2. Explore unconventional approaches
3. Challenge assumptions
4. Think creatively and broadly

Provide 3-5 distinct perspectives or approaches. Format each as a separate point.
"""
        
        response = self.generate_response(prompt, temperature=0.9, stream=False)  # Higher temp for creativity
        
        # Parse response into list of perspectives
        perspectives = self._parse_perspectives(str(response))
        logger.info(f"Generated {len(perspectives)} perspectives")
        
        return perspectives

    def _parse_perspectives(self, response: str) -> list[str]:
        """Parse response into list of perspectives.

        Args:
            response: Agent's response.

        Returns:
            List of perspective strings.
        """
        # Split by numbered points or bullet points
        lines = response.strip().split('\n')
        perspectives = []
        current = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current:
                    perspectives.append(' '.join(current))
                    current = []
                continue
            
            # Check if it's a new point (numbered or bulleted)
            if line[0].isdigit() or line.startswith(('*', '-', '•')):
                if current:
                    perspectives.append(' '.join(current))
                # Remove numbering/bullets
                cleaned = line.lstrip('0123456789.*-• ').lstrip('.')
                current = [cleaned]
            else:
                current.append(line)
        
        # Add last perspective
        if current:
            perspectives.append(' '.join(current))
        
        # If parsing failed, return whole response as single perspective
        if not perspectives:
            perspectives = [response]
        
        return perspectives
