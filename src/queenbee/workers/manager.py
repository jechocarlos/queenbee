"""Worker process manager for specialist agents."""

import json
import logging
import multiprocessing as mp
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
            results = self._run_collaborative_discussion(user_input, context, max_rounds)

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

    def _run_collaborative_discussion(self, user_input: str, context: str, max_rounds: int) -> dict[str, Any]:
        """Run iterative discussion between specialist agents.

        Each agent can respond to what others have said, building on the conversation.

        Args:
            user_input: Original user question.
            context: Conversation context.
            max_rounds: Maximum discussion rounds.

        Returns:
            Dictionary with all rounds of discussion.
        """
        logger.info(f"Starting collaborative discussion (max {max_rounds} rounds)")

        # Initialize shared discussion transcript
        discussion = []
        
        with self.db:
            # Create agents once and reuse them
            divergent = DivergentAgent(self.session_id, self.config, self.db)
            convergent = ConvergentAgent(self.session_id, self.config, self.db)
            critical = CriticalAgent(self.session_id, self.config, self.db)

            agents = [
                {"name": "Divergent", "agent": divergent, "role": "explorer"},
                {"name": "Convergent", "agent": convergent, "role": "synthesizer"},
                {"name": "Critical", "agent": critical, "role": "validator"}
            ]

            rounds = []

            for round_num in range(1, max_rounds + 1):
                logger.info(f"Round {round_num}/{max_rounds}")
                round_responses = []

                # Each agent gets a chance to speak
                for agent_info in agents:
                    agent_name = agent_info["name"]
                    agent = agent_info["agent"]
                    
                    # Build prompt with discussion history
                    response = self._get_agent_response(
                        agent_name=agent_name,
                        agent=agent,
                        user_input=user_input,
                        discussion=discussion,
                        round_num=round_num,
                        context=context
                    )

                    if response:  # Agent chose to respond
                        contribution = {
                            "agent": agent_name,
                            "round": round_num,
                            "content": response,
                            "timestamp": time.time()
                        }
                        
                        discussion.append(contribution)
                        round_responses.append(contribution)
                        logger.info(f"{agent_name} contributed in round {round_num}")
                    else:
                        logger.info(f"{agent_name} passed on round {round_num}")

                rounds.append({
                    "round": round_num,
                    "responses": round_responses
                })

                # Check if we should continue (did anyone speak this round?)
                if not round_responses:
                    logger.info(f"No responses in round {round_num}, ending discussion")
                    break

            # Cleanup agents
            divergent.terminate()
            convergent.terminate()
            critical.terminate()

            return {
                "task": user_input,
                "context": context,
                "rounds": rounds,
                "total_contributions": len(discussion),
                "full_discussion": discussion
            }

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
