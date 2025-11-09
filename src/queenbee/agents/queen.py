"""Queen agent - main orchestrator."""

import logging
import re
from uuid import UUID

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType, ChatRepository, MessageRole

logger = logging.getLogger(__name__)


class QueenAgent(BaseAgent):
    """Queen agent orchestrates the system and manages specialists."""

    def __init__(self, session_id: UUID, config: Config, db: DatabaseManager):
        """Initialize Queen agent.

        Args:
            session_id: Session ID.
            config: System configuration.
            db: Database manager.
        """
        super().__init__(AgentType.QUEEN, session_id, config, db)
        self.chat_repo = ChatRepository(db)

    def process_request(self, user_input: str) -> str:
        """Process user request and return response.

        Args:
            user_input: User's input text.

        Returns:
            Response to user.
        """
        # Log user message to chat history
        self.chat_repo.add_message(
            session_id=self.session_id,
            role=MessageRole.USER,
            content=user_input,
        )

        # Analyze complexity
        is_complex = self._analyze_complexity(user_input)

        if is_complex:
            response = self._handle_complex_request(user_input)
        else:
            response = self._handle_simple_request(user_input)

        # Log Queen's response to chat history
        self.chat_repo.add_message(
            session_id=self.session_id,
            agent_id=self.agent_id,
            role=MessageRole.QUEEN,
            content=response,
        )

        return response

    def _analyze_complexity(self, user_input: str) -> bool:
        """Analyze if request is complex and requires specialists.

        Args:
            user_input: User's input text.

        Returns:
            True if complex, False if simple.
        """
        # Simple heuristics for MVP
        # Complex if:
        # - Multiple questions
        # - Contains words like "analyze", "compare", "design", "evaluate"
        # - Long input (> 50 words)
        # - Contains "should I" or "which is better"

        word_count = len(user_input.split())
        
        complex_keywords = [
            r'\banalyze\b', r'\bcompare\b', r'\bevaluate\b', r'\bdesign\b',
            r'\barchitecture\b', r'\btrade-?offs?\b', r'\bpros and cons\b',
            r'\bshould i\b', r'\bwhich (?:is )?better\b', r'\bhow (?:do i|to)\b',
            r'\bwhat are the\b', r'\bexplain\b', r'\bdiscuss\b'
        ]
        
        has_complex_keywords = any(
            re.search(pattern, user_input.lower())
            for pattern in complex_keywords
        )
        
        has_multiple_questions = user_input.count('?') > 1
        is_long = word_count > 50

        is_complex = has_complex_keywords or has_multiple_questions or is_long

        logger.debug(
            f"Complexity analysis: keywords={has_complex_keywords}, "
            f"multiple_questions={has_multiple_questions}, "
            f"long={is_long}, result={is_complex}"
        )

        return is_complex

    def _handle_simple_request(self, user_input: str) -> str:
        """Handle simple request directly.

        Args:
            user_input: User's input text.

        Returns:
            Response.
        """
        logger.info("Handling simple request directly")
        response = self.generate_response(user_input)
        return response

    def _handle_complex_request(self, user_input: str) -> str:
        """Handle complex request by spawning specialists.

        Args:
            user_input: User's input text.

        Returns:
            Aggregated response.
        """
        logger.info("Detected complex request - spawning specialists")
        
        # For Phase 1 MVP, we'll provide a notice that specialists would be spawned
        # Full implementation will come in Phase 2
        placeholder_response = (
            "[QueenBee] This is a complex multi-perspective question. "
            "In the full system, I would spawn specialist agents (Divergent, Convergent, Critical) "
            "to analyze this collaboratively.\n\n"
            "For now, here's my direct analysis:\n\n"
        )
        
        # Generate response directly for now
        direct_response = self.generate_response(user_input)
        
        return placeholder_response + direct_response
