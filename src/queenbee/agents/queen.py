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

        # Always delegate to specialists for collaborative discussion
        # The Queen's role is purely orchestration - specialists handle all analysis
        if self.enable_specialists:
            response = self._handle_complex_request(user_input, stream=stream)
        else:
            # Fallback to direct response only if specialists are explicitly disabled
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
        
        # Create task for specialists with LIVE CHATROOM VIEW
        max_rounds = getattr(self.config.consensus, 'discussion_rounds', 3)
        
        # Use the new live discussion viewer
        response = self._spawn_specialists_with_live_view(user_input, max_rounds=max_rounds)
        return response
    
    def _spawn_specialists_with_live_view(self, user_input: str, max_rounds: int = 3) -> str:
        """Spawn specialists and show live chatroom-style discussion.
        
        This provides a real-time view of the agents thinking and contributing,
        making the discussion feel like a live chatroom.
        
        Args:
            user_input: User's question/request.
            max_rounds: Maximum discussion rounds.
            
        Returns:
            Final Queen response incorporating specialist insights.
        """
        from rich.console import Console
        from rich.panel import Panel

        from queenbee.cli.live_discussion import LiveDiscussionViewer

        # Create task for specialists
        task_data = {
            "type": "collaborative_discussion",
            "input": user_input,
            "context": self._get_conversation_context(),
            "max_rounds": max_rounds
        }
        
        task_description = json.dumps(task_data)
        assigned_to = [uuid4(), uuid4(), uuid4()]  # Divergent, Convergent, Critical
        
        logger.info(f"Creating task for specialists with live view...")
        task_id = self.task_repo.create_task(
            session_id=self.session_id,
            assigned_by=self.agent_id,
            assigned_to=assigned_to,
            description=task_description
        )
        
        console = Console()
        console.print("\n[bold yellow]🐝 Starting Live Collaborative Discussion...[/bold yellow]\n")
        console.print("[dim]Watch the agents think and contribute in real-time![/dim]\n")
        
        # Create live viewer and watch the discussion
        viewer = LiveDiscussionViewer(
            console=console,
            task_repo=self.task_repo,
            task_id=task_id
        )
        
        # Wait a moment for worker to start processing
        time.sleep(1)
        
        # Watch discussion with live updates
        max_wait = getattr(self.config.consensus, 'specialist_timeout_seconds', 300)
        results = viewer.watch_discussion(timeout=max_wait)
        
        # Check if we got valid results
        if "error" in results:
            logger.error(f"Discussion error: {results['error']}")
            return "The specialist team encountered an issue. Let me provide a direct answer:\n\n" + str(self.generate_response(user_input, stream=False))
        
        # Get the summary from results
        summary = results.get("summary", results.get("rolling_summary", ""))
        
        if summary:
            # Generate Queen's final response
            queen_response = self._generate_final_response(user_input, summary)
            
            console.print("\n")
            console.print(Panel(
                f"[bold cyan]{queen_response}[/bold cyan]",
                title="[bold cyan]🐝 QUEEN'S FINAL RESPONSE[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            ))
            console.print()
            
            return queen_response
        else:
            total = results.get("total_contributions", 0)
            return f"Discussion complete with {total} contributions from the specialist team."

    def _generate_final_response(self, user_input: str, synthesis: str) -> str:
        """Generate Queen's final response based on the synthesis from SummarizerAgent.
        
        Args:
            user_input: Original user question.
            synthesis: The synthesis provided by the SummarizerAgent.
            
        Returns:
            Queen's final response to the user.
        """
        # Queen uses the synthesis to craft a final answer
        prompt = f"""The user asked: "{user_input}"

My specialist team has completed their analysis. Here is their synthesis:

{synthesis}

Based on this synthesis, provide a clear, direct answer to the user's question. You may:
- Acknowledge the specialists' insights
- Present the answer in your own words
- Add brief context if helpful
- Keep it concise and actionable

Focus on answering the user's question, not describing the process."""

        response = self.generate_response(prompt, stream=False)
        return str(response)
    
    def _get_conversation_context(self, limit: int = 10) -> str:
        """Get recent conversation context for specialists.
        
        Provides context from previous exchanges in the session, focusing on:
        - User questions
        - Queen's final responses (which synthesize previous discussions)
        
        This bridges multiple async discussions by giving specialists awareness
        of what has already been discussed and concluded.

        Args:
            limit: Number of recent messages to include.

        Returns:
            Formatted context string for specialists.
        """
        messages = self.chat_repo.get_session_history(self.session_id, limit=limit)
        
        if not messages:
            return ""
        
        # Filter to USER and QUEEN messages only (exclude internal specialist chatter)
        context_parts = ["=== PREVIOUS CONVERSATION IN THIS SESSION ===\n"]
        for msg in messages[-limit:]:
            role = msg["role"]
            content = msg["content"]
            
            if role == MessageRole.USER:
                context_parts.append(f"User asked: {content}")
            elif role == MessageRole.QUEEN:
                context_parts.append(f"Queen responded: {content}")
        
        if len(context_parts) == 1:  # Only header, no messages
            return ""
            
        context_parts.append("\n=== NEW QUESTION (your current task) ===")
        return "\n\n".join(context_parts)
    
    def _format_specialist_results(self, results: dict, original_task: str) -> str:
        """Format results from specialist agents into coherent response.

        Args:
            results: Dictionary with results from each specialist.
            original_task: Original user request.

        Returns:
            Formatted response.
        """
        # Check if we have iterative discussion results
        if "rounds" in results and "full_discussion" in results:
            return self._format_discussion_results(results, original_task)
        
        # Fallback to old format for backwards compatibility
        return self._format_legacy_results(results, original_task)

    def _format_discussion_results(self, results: dict, original_task: str) -> str:
        """Format iterative discussion results.

        Args:
            results: Discussion results with rounds.
            original_task: Original question.

        Returns:
            Formatted collaborative discussion.
        """
        response_parts = [
            "🐝 [QueenBee Collaborative Discussion]\n",
            f"My specialist team had a {len(results['rounds'])}-round discussion about:\n",
            f"'{original_task[:100]}{'...' if len(original_task) > 100 else ''}'\n"
        ]

        # Format each round
        for round_data in results["rounds"]:
            round_num = round_data["round"]
            responses = round_data["responses"]
            
            if responses:
                response_parts.append(f"\n{'='*60}")
                response_parts.append(f"Round {round_num}: {len(responses)} contribution(s)")
                response_parts.append('='*60)
                
                for contrib in responses:
                    agent = contrib["agent"]
                    content = contrib["content"]
                    
                    # Color code by agent
                    if agent == "Divergent":
                        icon = "🔵"
                    elif agent == "Convergent":
                        icon = "🟢"
                    elif agent == "Critical":
                        icon = "🔴"
                    else:
                        icon = "⚪"
                    
                    response_parts.append(f"\n{icon} {agent}:")
                    response_parts.append(content)

        # Summary
        total_contributions = results.get("total_contributions", 0)
        response_parts.append(f"\n\n{'='*60}")
        response_parts.append(f"✨ Discussion complete with {total_contributions} total contributions")
        response_parts.append("This represents a truly collaborative multi-perspective analysis.")
        response_parts.append('='*60)

        return "\n".join(response_parts)

    def _format_legacy_results(self, results: dict, original_task: str) -> str:
        """Format legacy (non-discussion) results.

        Args:
            results: Old-format results.
            original_task: Original question.

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
