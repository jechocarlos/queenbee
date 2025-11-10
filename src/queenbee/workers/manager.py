"""Worker process manager for specialist agents."""

import json
import logging
import multiprocessing as mp
import threading
import time
from typing import Any
from uuid import UUID

from queenbee.agents.convergent import ConvergentAgent
from queenbee.agents.critical import CriticalAgent
from queenbee.agents.divergent import DivergentAgent
from queenbee.config.loader import Config, load_config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import AgentType, TaskRepository, TaskStatus

logger = logging.getLogger(__name__)


class SpecialistWorker:
    """Worker that processes tasks for specialist agents."""

    def __init__(self, config: Config, session_id: UUID):
        """Initialize specialist worker.

        Args:
            config: System configuration.
            session_id: Session ID.
        """
        self.config = config
        self.session_id = session_id
        self.db = DatabaseManager(config.database)
        self.task_repo = TaskRepository(self.db)

    def process_task(self, task: dict[str, Any]) -> None:
        """Process a single task with iterative multi-agent collaboration.

        Args:
            task: Task data from database.
        """
        task_id = task["id"]
        description = task["description"]
        assigned_to = task["assigned_to"]

        logger.info(f"Processing task {task_id}: {description[:50]}...")

        try:
            # Update status to in_progress
            self.task_repo.update_task_status(task_id, TaskStatus.IN_PROGRESS)

            # Parse task description
            try:
                task_data = json.loads(description)
                user_input = task_data.get("input", "")
                context = task_data.get("context", "")
                max_rounds = task_data.get("max_rounds", 3)  # Default 3 rounds of discussion
            except json.JSONDecodeError:
                user_input = description
                context = ""
                max_rounds = 3

            # Run iterative collaborative discussion
            results = self._run_collaborative_discussion(task_id, user_input, context, max_rounds)

            # Store results
            result_json = json.dumps(results, indent=2)
            self.task_repo.set_task_result(task_id, result_json)
            self.task_repo.update_task_status(task_id, TaskStatus.COMPLETED)

            logger.info(f"Task {task_id} completed successfully after {len(results.get('rounds', []))} rounds")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            self.task_repo.update_task_status(task_id, TaskStatus.FAILED)
            error_result = json.dumps({"error": str(e)})
            self.task_repo.set_task_result(task_id, error_result)

    def _run_collaborative_discussion(self, task_id: UUID, user_input: str, context: str, max_rounds: int) -> dict[str, Any]:
        """Run asynchronous collaborative discussion between specialist agents.

        Agents work in parallel and contribute whenever they see fit, not in forced rounds.

        Args:
            task_id: Task ID for storing intermediate results.
            user_input: Original user question.
            context: Conversation context.
            max_rounds: Maximum time limit (in iterations, ~2 seconds each).

        Returns:
            Dictionary with all contributions.
        """
        logger.info(f"Starting async collaborative discussion (max {max_rounds * 2}s)")

        # Shared discussion state with thread lock
        discussion_lock = threading.Lock()
        discussion = []
        stop_event = threading.Event()
        agent_status = {}  # Track if each agent is thinking or idle
        
        def agent_worker(agent_name: str, agent_type: str):
            """Worker thread for a single agent - contributes whenever it has something to add."""
            with self.db:
                # Create agent instance
                if agent_type == "divergent":
                    agent = DivergentAgent(self.session_id, self.config, self.db)
                elif agent_type == "convergent":
                    agent = ConvergentAgent(self.session_id, self.config, self.db)
                else:  # critical
                    agent = CriticalAgent(self.session_id, self.config, self.db)
                
                try:
                    contribution_count = 0
                    
                    # Mark agent as idle initially
                    with discussion_lock:
                        agent_status[agent_name] = "idle"
                    
                    while not stop_event.is_set():
                        # Get current discussion state
                        with discussion_lock:
                            current_discussion = discussion.copy()
                        
                        # Decide if this agent should contribute
                        should_contribute = self._should_agent_contribute(
                            agent_name, 
                            current_discussion, 
                            user_input,
                            contribution_count
                        )
                        
                        if should_contribute:
                            # Mark as thinking
                            with discussion_lock:
                                agent_status[agent_name] = "thinking"
                            
                            logger.info(f"{agent_name} is thinking...")
                            
                            # Get agent's contribution
                            response = self._get_async_agent_response(
                                agent_name=agent_name,
                                agent=agent,
                                user_input=user_input,
                                discussion=current_discussion,
                                context=context
                            )
                            
                            if response and not response.strip().upper().startswith("[PASS"):
                                # Mark as contributing
                                with discussion_lock:
                                    agent_status[agent_name] = "contributing"
                                
                                contribution = {
                                    "agent": agent_name,
                                    "content": response,
                                    "timestamp": time.time(),
                                    "contribution_num": contribution_count + 1
                                }
                                
                                # Add to shared discussion
                                with discussion_lock:
                                    discussion.append(contribution)
                                    
                                    # Store intermediate result
                                    intermediate_result = {
                                        "status": "in_progress",
                                        "contributions": discussion.copy(),
                                        "task": user_input
                                    }
                                    self.task_repo.set_task_result(task_id, json.dumps(intermediate_result))
                                
                                contribution_count += 1
                                logger.info(f"{agent_name} contributed (#{contribution_count})")
                            else:
                                logger.info(f"{agent_name} passed")
                        
                        # Mark as idle after decision/contribution
                        with discussion_lock:
                            agent_status[agent_name] = "idle"
                        
                        # Wait a bit before checking again (let others contribute)
                        time.sleep(2)
                
                finally:
                    agent.terminate()
        
        # Start agent threads
        threads = []
        agents = [
            ("Divergent", "divergent"),
            ("Convergent", "convergent"),
            ("Critical", "critical")
        ]
        
        for agent_name, agent_type in agents:
            thread = threading.Thread(
                target=agent_worker,
                args=(agent_name, agent_type),
                daemon=True
            )
            thread.start()
            threads.append(thread)
            logger.info(f"Started async agent: {agent_name}")
        
        # Monitor discussion - stop only when ALL agents are idle
        iterations = 0
        all_idle_count = 0
        
        while iterations < max_rounds * 10:  # Extend max time significantly
            time.sleep(1)  # Check every second
            iterations += 1
            
            with discussion_lock:
                # Check if ALL agents are idle
                statuses = list(agent_status.values())
                all_idle = all(status == "idle" for status in statuses) if statuses else False
                
                # Log current status
                if iterations % 5 == 0:  # Log every 5 seconds
                    status_str = ", ".join([f"{name}: {status}" for name, status in agent_status.items()])
                    logger.info(f"Agent status: {status_str}")
            
            if all_idle and len(discussion) > 0:
                # All agents idle, but wait a bit to be sure
                all_idle_count += 1
                if all_idle_count >= 6:  # 6 seconds of all idle
                    logger.info("All agents idle for 6 seconds, stopping discussion")
                    break
            else:
                # Reset counter if any agent is active
                all_idle_count = 0
        
        # Signal all agents to stop
        stop_event.set()
        
        # Wait for threads to finish (with timeout)
        for thread in threads:
            thread.join(timeout=5)
        
        # Generate final summary from Queen
        logger.info("Generating Queen's final summary...")
        summary = self._generate_queen_summary(user_input, discussion)
        
        return {
            "task": user_input,
            "context": context,
            "total_contributions": len(discussion),
            "contributions": discussion,
            "summary": summary
        }

    def _generate_queen_summary(self, user_input: str, discussion: list[dict]) -> str:
        """Generate Queen's final summary of the discussion.
        
        Args:
            user_input: Original question.
            discussion: Full discussion history.
            
        Returns:
            Queen's summary.
        """
        if not discussion:
            return "No discussion occurred."
        
        # Format the discussion for Queen
        discussion_text = []
        for i, contrib in enumerate(discussion, 1):
            agent = contrib["agent"]
            content = contrib["content"]
            discussion_text.append(f"{i}. {agent}: {content}")
        
        discussion_str = "\n\n".join(discussion_text)
        
        # Create summary prompt for Queen
        from queenbee.agents.queen import QueenAgent
        
        with self.db:
            queen = QueenAgent(self.session_id, self.config, self.db)
            
            summary_prompt = f"""The specialist team had the following discussion about: "{user_input}"

FULL DISCUSSION:
{discussion_str}

As the Queen orchestrator, provide a clear, actionable summary that:
1. Synthesizes the key insights from all perspectives
2. Presents the most important recommendations
3. Highlights any critical concerns or trade-offs
4. Gives a direct answer to the original question

Keep it concise but comprehensive (2-3 paragraphs)."""

            try:
                summary = queen.generate_response(summary_prompt, stream=False)
                queen.terminate()
                return str(summary)
            except Exception as e:
                logger.error(f"Error generating Queen summary: {e}")
                queen.terminate()
                return "Unable to generate summary."

    def _should_agent_contribute(
        self, 
        agent_name: str, 
        discussion: list[dict], 
        user_input: str,
        contribution_count: int
    ) -> bool:
        """Decide if agent should contribute based on discussion state.
        
        Args:
            agent_name: Name of the agent.
            discussion: Current discussion history.
            user_input: Original question.
            contribution_count: How many times this agent has contributed.
            
        Returns:
            True if agent should try to contribute.
        """
        # First contribution - always try
        if contribution_count == 0:
            return True
        
        # Don't spam - wait for others to contribute
        if discussion:
            last_contrib = discussion[-1]
            # Don't contribute twice in a row
            if last_contrib["agent"] == agent_name:
                return False
        
        # Limit contributions per agent (max 3)
        if contribution_count >= 3:
            return False
        
        # If discussion is long enough (6+ contributions), agents can be more selective
        if len(discussion) >= 6:
            # Only contribute every other check
            return contribution_count < 2
        
        return True
    
    def _get_async_agent_response(
        self,
        agent_name: str,
        agent: Any,
        user_input: str,
        discussion: list[dict],
        context: str
    ) -> str | None:
        """Get async agent response based on current discussion.
        
        Args:
            agent_name: Name of the agent.
            agent: Agent instance.
            user_input: Original question.
            discussion: Current discussion history.
            context: Additional context.
            
        Returns:
            Agent's response or None.
        """
        # Format discussion history with analysis
        discussion_text = self._format_discussion_for_analysis(discussion)
        
        # Build agent-specific prompt with explicit instruction to check for new value
        if agent_name == "Divergent":
            prompt = f"""Original question: {user_input}

Discussion so far:
{discussion_text if discussion_text else "No discussion yet - you'll be the first to contribute."}

You are the Divergent thinker. Your role is to explore diverse perspectives.

CRITICAL: Before responding, carefully analyze what has ALREADY been said:
1. Read through all existing contributions
2. Identify what perspectives, angles, and ideas are already covered
3. Ask yourself: "What NEW perspective can I add that hasn't been mentioned?"

Respond with [PASS] if:
- The question has been thoroughly explored from multiple angles
- You would just be repeating what others already said
- No new perspectives come to mind

Only contribute if you can add:
- A completely NEW perspective or angle not yet mentioned
- A challenge to assumptions no one else has raised
- A different way of thinking about the problem
- An unexplored aspect or dimension

Be specific and concrete. Add genuine value, not repetition."""

        elif agent_name == "Convergent":
            prompt = f"""Original question: {user_input}

Discussion so far:
{discussion_text if discussion_text else "No discussion yet - you'll be the first to contribute."}

You are the Convergent synthesizer. Your role is to find patterns and create actionable recommendations.

CRITICAL: Before responding, carefully analyze what has ALREADY been said:
1. Review all existing contributions thoroughly
2. Check what syntheses, patterns, or recommendations already exist
3. Ask yourself: "What NEW synthesis or refinement can I provide?"

Respond with [PASS] if:
- A clear synthesis has already been provided
- The recommendations are already well-defined
- You would just be restating existing conclusions

Only contribute if you can add:
- A NEW synthesis that builds on recent contributions
- Additional patterns or connections not yet highlighted
- Refined or prioritized recommendations based on new information
- Clearer action items or implementation guidance

Be specific about what you're adding beyond what's already been said."""

        else:  # Critical
            prompt = f"""Original question: {user_input}

Discussion so far:
{discussion_text if discussion_text else "No discussion yet - you'll be the first to contribute."}

You are the Critical validator. Your role is to identify risks, flaws, and validate solutions.

CRITICAL: Before responding, carefully analyze what has ALREADY been said:
1. Review all existing contributions and concerns raised
2. Check what risks, issues, and validations have been mentioned
3. Ask yourself: "What NEW concern or validation can I provide?"

Respond with [PASS] if:
- Major risks and concerns have been thoroughly identified
- Proposed solutions have been adequately validated
- You would just be repeating existing critiques

Only contribute if you can add:
- A NEW risk, concern, or edge case not yet mentioned
- Validation of recently proposed solutions
- A logical inconsistency or flaw others missed
- Important safeguards or considerations overlooked

Be specific about the new concern or validation you're adding."""

        # Get response from agent
        try:
            response = agent.generate_response(prompt, stream=False)
            return response if response else None
        except Exception as e:
            logger.error(f"{agent_name} error: {e}")
            return None
    
    def _format_discussion_for_analysis(self, discussion: list[dict]) -> str:
        """Format discussion history for agent analysis.

        Args:
            discussion: List of contributions.

        Returns:
            Formatted discussion string with clear separators.
        """
        if not discussion:
            return ""

        lines = []
        for i, contrib in enumerate(discussion, 1):
            agent = contrib["agent"]
            content = contrib["content"]
            contrib_num = contrib.get("contribution_num", "")
            
            lines.append(f"--- Contribution {i} ---")
            lines.append(f"Agent: {agent} (contribution #{contrib_num})")
            lines.append(f"Content: {content}")
            lines.append("")

        return "\n".join(lines)

    def _get_agent_response(
        self, 
        agent_name: str, 
        agent: Any, 
        user_input: str, 
        discussion: list[dict], 
        round_num: int,
        context: str
    ) -> str | None:
        """Get response from a specific agent based on discussion so far.

        Args:
            agent_name: Name of the agent.
            agent: Agent instance.
            user_input: Original question.
            discussion: List of previous contributions.
            round_num: Current round number.
            context: Additional context.

        Returns:
            Agent's response or None if agent chooses to pass.
        """
        # Format discussion history
        discussion_text = self._format_discussion(discussion)

        # Build agent-specific prompt
        if agent_name == "Divergent":
            prompt = self._build_divergent_prompt(user_input, discussion_text, round_num, context)
        elif agent_name == "Convergent":
            prompt = self._build_convergent_prompt(user_input, discussion_text, round_num, context)
        elif agent_name == "Critical":
            prompt = self._build_critical_prompt(user_input, discussion_text, round_num, context)
        else:
            return None

        # Get response
        try:
            response = agent.generate_response(prompt, stream=False, temperature=0.7)
            response_text = str(response)

            # Check if agent wants to pass (indicated by special markers)
            if any(marker in response_text.lower() for marker in ["[pass]", "[no response]", "i have nothing to add"]):
                return None

            return response_text
        except Exception as e:
            logger.error(f"Error getting response from {agent_name}: {e}")
            return None

    def _format_discussion(self, discussion: list[dict]) -> str:
        """Format discussion history for agent consumption.

        Args:
            discussion: List of contributions.

        Returns:
            Formatted discussion string.
        """
        if not discussion:
            return "No prior discussion yet."

        lines = ["Previous discussion:"]
        for contrib in discussion:
            agent = contrib["agent"]
            content = contrib["content"]
            round_num = contrib["round"]
            lines.append(f"\n[Round {round_num}] {agent}: {content}")

        return "\n".join(lines)

    def _build_divergent_prompt(self, task: str, discussion: str, round_num: int, context: str) -> str:
        """Build prompt for Divergent agent.

        Args:
            task: Original task.
            discussion: Discussion so far.
            round_num: Current round.
            context: Additional context.

        Returns:
            Formatted prompt.
        """
        return f"""Original Question: {task}

{f'Context: {context}' if context else ''}

{discussion}

You are the Divergent thinker (Round {round_num}). Your role is to explore different perspectives and possibilities.

Instructions:
- If this is your first contribution, brainstorm 2-3 diverse perspectives or approaches
- If others have already spoken, you can:
  * Add NEW perspectives they haven't covered
  * Challenge assumptions made by other agents
  * Suggest alternative angles to consider
- If you feel everything important has been explored, respond with "[PASS]" to skip your turn
- Keep your response focused and concise (2-3 paragraphs)

Your response:"""

    def _build_convergent_prompt(self, task: str, discussion: str, round_num: int, context: str) -> str:
        """Build prompt for Convergent agent.

        Args:
            task: Original task.
            discussion: Discussion so far.
            round_num: Current round.
            context: Additional context.

        Returns:
            Formatted prompt.
        """
        return f"""Original Question: {task}

{f'Context: {context}' if context else ''}

{discussion}

You are the Convergent thinker (Round {round_num}). Your role is to synthesize insights and narrow down to actionable recommendations.

Instructions:
- If this is your first contribution, synthesize the perspectives mentioned so far
- If others have already spoken, you can:
  * Refine your synthesis based on new information
  * Prioritize or rank the options discussed
  * Identify common patterns or themes
  * Provide clearer recommendations
- If you have nothing new to add, respond with "[PASS]" to skip your turn
- Keep your response focused and concise (2-3 paragraphs)

Your response:"""

    def _build_critical_prompt(self, task: str, discussion: str, round_num: int, context: str) -> str:
        """Build prompt for Critical agent.

        Args:
            task: Original task.
            discussion: Discussion so far.
            round_num: Current round.
            context: Additional context.

        Returns:
            Formatted prompt.
        """
        return f"""Original Question: {task}

{f'Context: {context}' if context else ''}

{discussion}

You are the Critical thinker (Round {round_num}). Your role is to validate ideas and identify potential issues.

Instructions:
- If this is your first contribution, identify risks, concerns, or flaws in the discussion
- If others have already spoken, you can:
  * Point out NEW issues or edge cases not yet mentioned
  * Validate solutions proposed by other agents
  * Challenge assumptions or logical inconsistencies
  * Suggest safeguards or improvements
- If all concerns have been addressed, respond with "[PASS]" to skip your turn
- Keep your response focused and concise (2-3 paragraphs)

Your response:"""

    def run(self) -> None:
        """Run worker loop to process pending tasks."""
        logger.info(f"Starting specialist worker for session {self.session_id}")

        with self.db:
            while True:
                try:
                    # Get pending tasks for this session
                    pending_tasks = self.task_repo.get_pending_tasks(self.session_id)

                    if not pending_tasks:
                        # No tasks, sleep and check again
                        time.sleep(2)
                        continue

                    # Process each task
                    for task in pending_tasks:
                        self.process_task(task)

                except KeyboardInterrupt:
                    logger.info("Worker interrupted, shutting down")
                    break
                except Exception as e:
                    logger.error(f"Worker error: {e}", exc_info=True)
                    time.sleep(5)  # Back off on error


def worker_process(config_path: str, session_id: str) -> None:
    """Worker process entry point.

    Args:
        config_path: Path to configuration file.
        session_id: Session ID as string.
    """
    # Set up logging for worker process
    logging.basicConfig(
        level=logging.INFO,
        format="[Worker] %(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info(f"Worker process started for session {session_id}")

    # Load configuration
    config = load_config(config_path)

    # Create and run worker
    worker = SpecialistWorker(config, UUID(session_id))
    worker.run()


class WorkerManager:
    """Manages worker processes for specialist agents."""

    def __init__(self, config: Config):
        """Initialize worker manager.

        Args:
            config: System configuration.
        """
        self.config = config
        self.workers: dict[UUID, mp.Process] = {}

    def start_worker(self, session_id: UUID) -> None:
        """Start a worker for a session.

        Args:
            session_id: Session ID.
        """
        if session_id in self.workers:
            logger.warning(f"Worker for session {session_id} already exists")
            return

        logger.info(f"Starting worker for session {session_id}")

        # Create worker process
        process = mp.Process(
            target=worker_process,
            args=("config.yaml", str(session_id)),
            daemon=True
        )
        process.start()

        self.workers[session_id] = process
        logger.info(f"Worker process started with PID {process.pid}")

    def stop_worker(self, session_id: UUID) -> None:
        """Stop a worker for a session.

        Args:
            session_id: Session ID.
        """
        if session_id not in self.workers:
            logger.warning(f"No worker found for session {session_id}")
            return

        process = self.workers[session_id]
        logger.info(f"Stopping worker for session {session_id} (PID {process.pid})")

        process.terminate()
        process.join(timeout=5)

        if process.is_alive():
            logger.warning(f"Worker {process.pid} did not terminate, killing")
            process.kill()

        del self.workers[session_id]

    def stop_all(self) -> None:
        """Stop all workers."""
        logger.info(f"Stopping all {len(self.workers)} workers")

        for session_id in list(self.workers.keys()):
            self.stop_worker(session_id)
