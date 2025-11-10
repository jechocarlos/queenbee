"""Convergent agent - synthesizes and evaluates solutions."""

import logging
from typing import Any
from uuid import UUID

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType

logger = logging.getLogger(__name__)


class ConvergentAgent(BaseAgent):
    """Convergent agent synthesizes information and narrows down to best options."""

    def __init__(self, session_id: UUID, config: Config, db: DatabaseManager):
        """Initialize Convergent agent.

        Args:
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        super().__init__(AgentType.CONVERGENT, session_id, config, db)
        logger.info(f"Convergent agent initialized: {self.agent_id}")

    def synthesize(self, task: str, perspectives: list[str], context: str = "") -> dict[str, Any]:
        """Synthesize perspectives and evaluate options.

        Args:
            task: Original task description.
            perspectives: List of perspectives from Divergent agent.
            context: Optional context.

        Returns:
            Dictionary with synthesis results including ranked options and reasoning.
        """
        logger.info(f"Convergent agent synthesizing {len(perspectives)} perspectives")
        
        # Format perspectives for the prompt
        perspectives_text = "\n".join([f"{i+1}. {p}" for i, p in enumerate(perspectives)])
        
        prompt = f"""
Task: {task}

{f'Context: {context}' if context else ''}

Perspectives to evaluate:
{perspectives_text}

Your role as a Convergent thinker is to:
1. Analyze and compare the perspectives
2. Identify common themes and patterns
3. Evaluate feasibility and practicality
4. Synthesize into coherent recommendations
5. Rank the top 2-3 approaches

Provide your synthesis with:
- Key insights
- Top recommendations (ranked)
- Reasoning for each recommendation
"""
        
        response = self.generate_response(prompt, temperature=0.5, stream=False)  # Lower temp for precision
        
        result = {
            "synthesis": str(response),
            "perspectives_evaluated": len(perspectives),
            "original_task": task
        }
        
        logger.info("Convergent synthesis completed")
        return result

    def evaluate_trade_offs(self, options: list[str], criteria: list[str]) -> dict[str, Any]:
        """Evaluate trade-offs between options based on criteria.

        Args:
            options: List of options to evaluate.
            criteria: List of evaluation criteria.

        Returns:
            Dictionary with trade-off analysis.
        """
        logger.info(f"Evaluating {len(options)} options against {len(criteria)} criteria")
        
        options_text = "\n".join([f"Option {i+1}: {o}" for i, o in enumerate(options)])
        criteria_text = "\n".join([f"- {c}" for c in criteria])
        
        prompt = f"""
Options to evaluate:
{options_text}

Evaluation criteria:
{criteria_text}

Analyze the trade-offs between these options considering the criteria.
Provide:
1. Strengths and weaknesses of each option
2. Which criteria each option satisfies best
3. Overall recommendation with justification
"""
        
        response = self.generate_response(prompt, temperature=0.5, stream=False)
        
        result = {
            "trade_off_analysis": str(response),
            "options_count": len(options),
            "criteria_count": len(criteria)
        }
        
        logger.info("Trade-off evaluation completed")
        return result
