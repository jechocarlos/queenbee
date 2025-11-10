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
        """Process a single task.

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

            # Parse task description (should be JSON with task type and data)
            try:
                task_data = json.loads(description)
                task_type = task_data.get("type", "explore")
                user_input = task_data.get("input", "")
                context = task_data.get("context", "")
            except json.JSONDecodeError:
                # Fallback: treat entire description as input
                task_type = "explore"
                user_input = description
                context = ""

            # Execute task based on assigned agents
            results = {}

            # Check which agents are assigned
            has_divergent = any(str(agent_id) in str(assigned_to) for agent_id in assigned_to)
            has_convergent = any(str(agent_id) in str(assigned_to) for agent_id in assigned_to)
            has_critical = any(str(agent_id) in str(assigned_to) for agent_id in assigned_to)

            with self.db:
                # Phase 1: Divergent exploration
                perspectives = []
                if has_divergent or task_type == "explore":
                    divergent = DivergentAgent(self.session_id, self.config, self.db)
                    perspectives = divergent.explore(user_input, context)
                    results["divergent"] = {
                        "perspectives": perspectives,
                        "agent_id": str(divergent.agent_id)
                    }
                    divergent.terminate()

                # Phase 2: Convergent synthesis
                synthesis = None
                if has_convergent or task_type == "synthesize":
                    if not perspectives:
                        # If no divergent phase, use input directly
                        perspectives = [user_input]
                    
                    convergent = ConvergentAgent(self.session_id, self.config, self.db)
                    synthesis_result = convergent.synthesize(user_input, perspectives, context)
                    synthesis = synthesis_result["synthesis"]
                    results["convergent"] = {
                        "synthesis": synthesis,
                        "agent_id": str(convergent.agent_id)
                    }
                    convergent.terminate()

                # Phase 3: Critical validation
                if has_critical or task_type == "validate":
                    if not synthesis:
                        # If no convergent phase, use perspectives or input
                        synthesis = "\n".join(perspectives) if perspectives else user_input
                    
                    critical = CriticalAgent(self.session_id, self.config, self.db)
                    validation_result = critical.validate(user_input, synthesis, context)
                    results["critical"] = {
                        "validation": validation_result["validation"],
                        "agent_id": str(critical.agent_id)
                    }
                    critical.terminate()

            # Store results
            result_json = json.dumps(results, indent=2)
            self.task_repo.set_task_result(task_id, result_json)
            self.task_repo.update_task_status(task_id, TaskStatus.COMPLETED)

            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            self.task_repo.update_task_status(task_id, TaskStatus.FAILED)
            error_result = json.dumps({"error": str(e)})
            self.task_repo.set_task_result(task_id, error_result)

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
