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
        
        # Create task for specialists with iterative discussion
        max_rounds = getattr(self.config.consensus, 'discussion_rounds', 3)
        
        task_data = {
            "type": "collaborative_discussion",
            "input": user_input,
            "context": self._get_conversation_context(),
            "max_rounds": max_rounds  # From config
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
        print("\n🐝 [QueenBee Collaborative Discussion Starting...]\n")
        
        # Wait for task completion (with timeout from config)
        max_wait = getattr(self.config.consensus, 'specialist_timeout_seconds', 300)  # Default 5 minutes
        start_time = time.time()
        displayed_contributions = 0  # Track what we've already shown
        last_rolling_summary = ""  # Track last displayed rolling summary
        
        while time.time() - start_time < max_wait:
            task = self.task_repo.get_task(task_id)
            
            if not task:
                logger.error(f"Task {task_id} not found")
                break
            
            # Check for intermediate results and display new contributions
            result = task.get("result")
            if result:
                try:
                    current_results = json.loads(result)
                    
                    # If in progress, show new contributions
                    if current_results.get("status") == "in_progress":
                        contributions = current_results.get("contributions", [])
                        
                        # Display any new contributions with color coding
                        for contrib in contributions[displayed_contributions:]:
                            agent = contrib["agent"]
                            contrib_num = contrib.get("contribution_num", "")
                            content = contrib["content"]
                            
                            # Color code by agent with rich console colors
                            if agent == "Divergent":
                                icon = "🔵"
                                color = "bright_blue"
                                agent_label = f"[{color}]{agent}{contrib_label if (contrib_label := f' #{contrib_num}' if contrib_num else '') else ''}[/{color}]"
                            elif agent == "Convergent":
                                icon = "🟢"
                                color = "bright_green"
                                agent_label = f"[{color}]{agent}{contrib_label if (contrib_label := f' #{contrib_num}' if contrib_num else '') else ''}[/{color}]"
                            elif agent == "Critical":
                                icon = "🔴"
                                color = "bright_red"
                                agent_label = f"[{color}]{agent}{contrib_label if (contrib_label := f' #{contrib_num}' if contrib_num else '') else ''}[/{color}]"
                            else:
                                icon = "⚪"
                                color = "white"
                                agent_label = f"{agent}{contrib_label if (contrib_label := f' #{contrib_num}' if contrib_num else '') else ''}"
                            
                            # Print with color using rich console
                            from rich.console import Console
                            console = Console()
                            console.print(f"\n{icon} {agent_label}")
                            console.print(f"[{color}]{content}[/{color}]")
                            console.print(f"[dim]{'─' * 60}[/dim]\n")
                        
                        displayed_contributions = len(contributions)
                        
                        # Check for updated rolling summary
                        rolling_summary = current_results.get("rolling_summary", "")
                        if rolling_summary and rolling_summary != last_rolling_summary:
                            from rich.console import Console
                            from rich.panel import Panel
                            console = Console()
                            
                            console.print(Panel(
                                f"[italic dim]{rolling_summary}[/italic dim]",
                                title="[dim]💭 Rolling Summary[/dim]",
                                border_style="dim",
                                padding=(0, 1)
                            ))
                            console.print()
                            
                            last_rolling_summary = rolling_summary
                        
                except json.JSONDecodeError:
                    pass  # Wait for valid JSON
            
            if task["status"] == TaskStatus.COMPLETED.value:
                print("✨ Discussion complete!\n")
                logger.info(f"Task {task_id} completed")
                result = task["result"]
                
                if result:
                    try:
                        results = json.loads(result)
                        
                        # Check if there are any new contributions we haven't displayed
                        if results.get("status") == "in_progress":
                            contributions = results.get("contributions", [])
                            
                            from rich.console import Console
                            console = Console()
                            
                            for contrib in contributions[displayed_contributions:]:
                                agent = contrib["agent"]
                                contrib_num = contrib.get("contribution_num", "")
                                content = contrib["content"]
                                
                                # Color code by agent
                                if agent == "Divergent":
                                    icon = "🔵"
                                    color = "bright_blue"
                                elif agent == "Convergent":
                                    icon = "🟢"
                                    color = "bright_green"
                                elif agent == "Critical":
                                    icon = "🔴"
                                    color = "bright_red"
                                else:
                                    icon = "⚪"
                                    color = "white"
                                
                                contrib_label = f" #{contrib_num}" if contrib_num else ""
                                console.print(f"\n{icon} [{color}]{agent}{contrib_label}[/{color}]")
                                console.print(f"[{color}]{content}[/{color}]")
                                console.print(f"[dim]{'─' * 60}[/dim]\n")
                        
                        # Check for summary and display it
                        summary = results.get("summary", "")
                        if summary:
                            from rich.console import Console
                            from rich.panel import Panel
                            console = Console()
                            
                            console.print("\n")
                            console.print(Panel(
                                f"[bold yellow]{summary}[/bold yellow]",
                                title="[bold yellow]🐝 QUEEN'S SUMMARY[/bold yellow]",
                                border_style="yellow",
                                padding=(1, 2)
                            ))
                            console.print()
                        
                        # Return simple completion message since we already showed everything
                        total = results.get("total_contributions", displayed_contributions)
                        return f"Discussion complete with {total} contributions from the specialist team."
                        
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
