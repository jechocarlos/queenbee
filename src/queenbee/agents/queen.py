"""Queen agent - main orchestrator."""

import json
import logging
import re
import time
from typing import Iterator, Union
from uuid import UUID, uuid4

from queenbee.agents.base import BaseAgent
from queenbee.config.loader import Config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import (AgentType, ChatRepository, MessageRole,
                                TaskRepository, TaskStatus)

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
        self.task_repo = TaskRepository(db)
        self.enable_specialists = True  # Toggle to enable/disable specialist spawning

    def process_request(self, user_input: str, stream: bool = False) -> Union[str, Iterator[str]]:
        """Process user request and return response.

        Args:
            user_input: User's input text.
            stream: Whether to enable streaming responses.

        Returns:
            Response to user (str) or iterator of response chunks (Iterator[str]).
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
            response = self._handle_complex_request(user_input, stream=stream)
        else:
            response = self._handle_simple_request(user_input, stream=stream)

        # If streaming, we can't log yet - caller will handle logging
        if not stream:
            # Log Queen's response to chat history
            self.chat_repo.add_message(
                session_id=self.session_id,
                agent_id=self.agent_id,
                role=MessageRole.QUEEN,
                content=str(response),
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

    def _handle_simple_request(self, user_input: str, stream: bool = False) -> Union[str, Iterator[str]]:
        """Handle simple request directly.

        Args:
            user_input: User's input text.
            stream: Whether to enable streaming.

        Returns:
            Response (str) or iterator of chunks (Iterator[str]).
        """
        logger.info("Handling simple request directly")
        response = self.generate_response(user_input, stream=stream)
        return response

    def _handle_complex_request(self, user_input: str, stream: bool = False) -> Union[str, Iterator[str]]:
        """Handle complex request by spawning specialists.

        Args:
            user_input: User's input text.
            stream: Whether to enable streaming.

        Returns:
            Aggregated response (str) or iterator of chunks (Iterator[str]).
        """
        logger.info("Detected complex request - spawning specialists")
        
        if not self.enable_specialists:
            # Fallback to direct response
            placeholder_response = (
                "[QueenBee] Complex request detected, but specialist spawning is disabled.\n\n"
                "Direct analysis:\n\n"
            )
            direct_response = self.generate_response(user_input, stream=stream)
            
            if stream:
                def response_generator():
                    yield placeholder_response
                    for chunk in direct_response:  # type: ignore
                        yield chunk
                return response_generator()
            else:
                return placeholder_response + str(direct_response)
        
        # Create task for specialists
        task_data = {
            "type": "full_analysis",  # Divergent -> Convergent -> Critical
            "input": user_input,
            "context": self._get_conversation_context()
        }
        
        task_description = json.dumps(task_data)
        
        # Create placeholder agent IDs for specialists (they'll be created by the worker)
        # For now, use dummy UUIDs - the worker will create real agents
        assigned_to = [uuid4(), uuid4(), uuid4()]  # Divergent, Convergent, Critical
        
        logger.info(f"Creating task for specialists: {task_description[:100]}...")
        task_id = self.task_repo.create_task(
            session_id=self.session_id,
            assigned_by=self.agent_id,
            assigned_to=assigned_to,
            description=task_description
        )
        
        logger.info(f"Task {task_id} created, waiting for specialists to process...")
        
        # Wait for task completion (with timeout)
        max_wait = 120  # 2 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            task = self.task_repo.get_task(task_id)
            
            if not task:
                logger.error(f"Task {task_id} not found")
                break
            
            if task["status"] == TaskStatus.COMPLETED.value:
                logger.info(f"Task {task_id} completed")
                result = task["result"]
                
                if result:
                    try:
                        results = json.loads(result)
                        # Format the collaborative response
                        response = self._format_specialist_results(results, user_input)
                        
                        if stream:
                            # For streaming, yield the formatted response chunk by chunk
                            def response_generator():
                                chunk_size = 10  # words per chunk
                                words = response.split()
                                for i in range(0, len(words), chunk_size):
                                    chunk = " ".join(words[i:i+chunk_size])
                                    yield chunk + " "
                                    time.sleep(0.05)  # Simulate streaming delay
                            return response_generator()
                        else:
                            return response
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse task result: {result}")
                        return "Error: Specialists produced invalid results."
                
            elif task["status"] == TaskStatus.FAILED.value:
                logger.error(f"Task {task_id} failed")
                return "Error: Specialist agents encountered an error processing your request."
            
            # Wait a bit before checking again
            time.sleep(2)
        
        # Timeout - fallback to direct response
        logger.warning(f"Task {task_id} timed out, falling back to direct response")
        return "I delegated this to my specialist team, but they're taking longer than expected. Let me provide a direct answer:\n\n" + str(self.generate_response(user_input, stream=False))
    
    def _get_conversation_context(self, limit: int = 5) -> str:
        """Get recent conversation context.

        Args:
            limit: Number of recent messages to include.

        Returns:
            Formatted context string.
        """
        messages = self.chat_repo.get_session_history(self.session_id, limit=limit)
        
        if not messages:
            return ""
        
        context_parts = []
        for msg in messages[-limit:]:
            role = msg["role"].upper()
            content = msg["content"]
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)
    
    def _format_specialist_results(self, results: dict, original_task: str) -> str:
        """Format results from specialist agents into coherent response.

        Args:
            results: Dictionary with results from each specialist.
            original_task: Original user request.

        Returns:
            Formatted response.
        """
        response_parts = [
            "🐝 [QueenBee Collaborative Analysis]\n",
            f"I've consulted with my specialist team to analyze: '{original_task[:100]}...'\n"
        ]
        
        # Divergent perspectives
        if "divergent" in results:
            perspectives = results["divergent"].get("perspectives", [])
            response_parts.append("\n🔵 Divergent Perspectives:")
            for i, perspective in enumerate(perspectives, 1):
                response_parts.append(f"{i}. {perspective}")
        
        # Convergent synthesis
        if "convergent" in results:
            synthesis = results["convergent"].get("synthesis", "")
            response_parts.append("\n\n🟢 Convergent Synthesis:")
            response_parts.append(synthesis)
        
        # Critical validation
        if "critical" in results:
            validation = results["critical"].get("validation", "")
            response_parts.append("\n\n🔴 Critical Validation:")
            response_parts.append(validation)
        
        response_parts.append("\n\n✨ This analysis represents a collaborative effort from multiple thinking modes for a more comprehensive perspective.")
        
        return "\n".join(response_parts)
