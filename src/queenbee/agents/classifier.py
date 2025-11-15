"""Classifier agent - decides if query needs specialists."""

import logging
from uuid import UUID

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType

logger = logging.getLogger(__name__)


class ClassifierAgent(BaseAgent):
    """Classifier agent that decides if a query needs specialist discussion."""

    def __init__(self, session_id: UUID, config: Config, db: DatabaseManager):
        """Initialize Classifier agent.

        Args:
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        super().__init__(AgentType.CLASSIFIER, session_id, config, db)
        logger.info(f"Classifier agent initialized: {self.agent_id}")

    def classify(self, user_input: str) -> bool:
        """Classify if user input requires specialist discussion.

        Args:
            user_input: User's question or request.

        Returns:
            True if complex (needs specialists), False if simple (Queen can answer directly).
        """
        classification_prompt = f"""Your job is to classify this user question as SIMPLE or COMPLEX.

User Question: "{user_input}"

Classification Rules:

SIMPLE = Direct factual answer exists, no discussion needed
Examples:
- "what is 2+2?" → SIMPLE (basic math)
- "what's the capital of France?" → SIMPLE (factual lookup)
- "who created Python?" → SIMPLE (factual)
- "define recursion" → SIMPLE (definition)
- "what does REST stand for?" → SIMPLE (acronym)

COMPLEX = Requires analysis, trade-offs, multiple perspectives, or subjective judgment
Examples:
- "should I use microservices or monolith?" → COMPLEX (needs analysis)
- "what are the best practices for X?" → COMPLEX (needs discussion)
- "how do I design a scalable system?" → COMPLEX (needs architecture discussion)
- "compare React vs Vue" → COMPLEX (needs multiple perspectives)
- "analyze this approach" → COMPLEX (needs critical thinking)

Answer with EXACTLY ONE WORD: SIMPLE or COMPLEX

Your classification:"""

        # Inject token limit from config
        classifier_max_tokens = getattr(self.config.agents.classifier, 'max_tokens', 10)
        classification_prompt += f"\n\n**Token Limit**: Keep your response to approximately {classifier_max_tokens} tokens maximum."

        try:
            response = self.generate_response(
                prompt=classification_prompt,
                temperature=0.0,
                stream=False,
                max_tokens=classifier_max_tokens
            )
            
            decision = str(response).strip().upper()
            is_complex = "COMPLEX" in decision
            
            logger.info(f"Classifier decision for '{user_input[:50]}...': {decision} (is_complex={is_complex})")
            return is_complex
            
        except Exception as e:
            logger.warning(f"Error in classification, defaulting to complex: {e}")
            # On error, default to complex to ensure specialists handle it safely
            return True
