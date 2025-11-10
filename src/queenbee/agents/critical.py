"""Critical agent - validates and identifies issues."""

import logging
from typing import Any
from uuid import UUID

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType

logger = logging.getLogger(__name__)


class CriticalAgent(BaseAgent):
    """Critical agent validates solutions and identifies potential issues."""

    def __init__(self, session_id: UUID, config: Config, db: DatabaseManager):
        """Initialize Critical agent.

        Args:
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        super().__init__(AgentType.CRITICAL, session_id, config, db)
        logger.info(f"Critical agent initialized: {self.agent_id}")

    def validate(self, task: str, synthesis: str, context: str = "") -> dict[str, Any]:
        """Validate synthesis and identify potential issues.

        Args:
            task: Original task description.
            synthesis: Synthesis from Convergent agent.
            context: Optional context.

        Returns:
            Dictionary with validation results including risks and concerns.
        """
        logger.info("Critical agent validating synthesis")
        
        prompt = f"""
Task: {task}

{f'Context: {context}' if context else ''}

Proposed solution/synthesis:
{synthesis}

Your role as a Critical thinker is to:
1. Identify potential flaws or weaknesses
2. Assess risks and edge cases
3. Challenge assumptions
4. Verify logical consistency
5. Suggest improvements or safeguards

Provide your critical analysis with:
- Identified risks or concerns
- Assumptions that need validation
- Edge cases to consider
- Recommendations for improvement
- Overall assessment (approve/approve with conditions/reject)
"""
        
        response = self.generate_response(prompt, temperature=0.3, stream=False)  # Low temp for consistency
        
        result = {
            "validation": str(response),
            "task": task,
            "concerns_identified": True  # Could parse response to detect if concerns were found
        }
        
        logger.info("Critical validation completed")
        return result

    def identify_risks(self, proposal: str, domain: str = "") -> dict[str, Any]:
        """Identify specific risks in a proposal.

        Args:
            proposal: The proposal to analyze.
            domain: Optional domain context (e.g., "security", "performance").

        Returns:
            Dictionary with risk analysis.
        """
        logger.info(f"Identifying risks in proposal{f' (domain: {domain})' if domain else ''}")
        
        prompt = f"""
Proposal:
{proposal}

{f'Domain context: {domain}' if domain else ''}

Identify and analyze potential risks:
1. Technical risks
2. Operational risks
3. Business/strategic risks
4. Security concerns (if applicable)
5. Performance concerns (if applicable)

For each risk:
- Describe the risk
- Assess likelihood (low/medium/high)
- Assess impact (low/medium/high)
- Suggest mitigation strategies
"""
        
        response = self.generate_response(prompt, temperature=0.3, stream=False)
        
        result = {
            "risk_analysis": str(response),
            "domain": domain or "general"
        }
        
        logger.info("Risk identification completed")
        return result

    def verify_consistency(self, statements: list[str]) -> dict[str, Any]:
        """Verify logical consistency across multiple statements.

        Args:
            statements: List of statements to check for consistency.

        Returns:
            Dictionary with consistency analysis.
        """
        logger.info(f"Verifying consistency across {len(statements)} statements")
        
        statements_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(statements)])
        
        prompt = f"""
Statements to verify:
{statements_text}

Analyze these statements for:
1. Logical consistency
2. Contradictions or conflicts
3. Missing assumptions
4. Gaps in reasoning

Identify any inconsistencies and explain why they are problematic.
If statements are consistent, confirm this and explain the logical flow.
"""
        
        response = self.generate_response(prompt, temperature=0.3, stream=False)
        
        result = {
            "consistency_check": str(response),
            "statements_analyzed": len(statements)
        }
        
        logger.info("Consistency verification completed")
        return result
