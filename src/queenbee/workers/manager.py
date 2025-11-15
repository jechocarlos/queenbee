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
from queenbee.agents.pragmatist import PragmatistAgent
from queenbee.agents.quantifier import QuantifierAgent
from queenbee.agents.user_proxy import UserProxyAgent
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
        rolling_summary = {"content": "", "last_update": 0}  # Track rolling summary
        web_search_events = []  # Track web search requests: {"agent": "Divergent", "query": "..."}
        web_search_queue = []  # Queue for pending web search requests: [{"agent": "...", "query": "..."}]
        
        # Track agent passes for early termination
        agent_pass_count = {}  # {agent: consecutive_pass_count}
        last_contribution_round = {}  # {agent: contribution_number_of_last_contribution}
        
        # Statistics tracking
        start_time = time.time()
        stats = {
            "agent_contributions": {},  # Count per agent
            "agent_tokens": {},  # {agent: {"prompt": X, "completion": Y}}
            "agent_response_times": {},  # {agent: [time1, time2, ...]}
            "agent_passes": {},  # Count of passes per agent
            "web_searches": 0,
            "web_searches_by_agent": {},
            "peak_concurrent_thinking": 0
        }
        
        def update_rolling_summary():
            """Background thread that continuously updates the rolling summary using SummarizerAgent."""
            with self.db:
                # Create SummarizerAgent for generating summaries
                from queenbee.agents.summarizer import SummarizerAgent
                summarizer = SummarizerAgent(self.session_id, self.config, self.db)
                
                # Get summary interval from config
                summary_interval = self.config.consensus.summary_interval_seconds
                logger.info(f"Rolling summary will update every {summary_interval} seconds")
                
                try:
                    while not stop_event.is_set():
                        time.sleep(summary_interval)
                        
                        with discussion_lock:
                            current_discussion = discussion.copy()
                            contrib_count = len(current_discussion)
                        
                        # Only update if there are new contributions
                        if contrib_count > 0 and contrib_count != rolling_summary["last_update"]:
                            logger.info(f"Updating rolling summary (contributions: {contrib_count})...")
                            
                            try:
                                # Use SummarizerAgent to generate rolling summary
                                summary_response = summarizer.generate_rolling_summary(
                                    user_input=user_input,
                                    contributions=current_discussion,
                                    stream=False
                                )
                                
                                with discussion_lock:
                                    rolling_summary["content"] = str(summary_response)
                                    rolling_summary["last_update"] = contrib_count
                                    
                                    # Store in task result with agent status
                                    intermediate_result = {
                                        "status": "in_progress",
                                        "contributions": discussion.copy(),
                                        "rolling_summary": rolling_summary["content"],
                                        "task": user_input,
                                        "agent_status": agent_status.copy(),
                                        "web_search_events": web_search_events.copy()
                                    }
                                    self.task_repo.set_task_result(task_id, json.dumps(intermediate_result))
                                
                                logger.info("Rolling summary updated")
                            except Exception as e:
                                logger.error(f"Error updating rolling summary: {e}")
                
                finally:
                    summarizer.terminate()
                    logger.info("Summarizer agent terminated")
        
        def agent_worker(agent_name: str, agent_type: str):
            """Worker thread for a single agent - contributes whenever it has something to add."""
            with self.db:
                # Create agent instance
                if agent_type == "divergent":
                    agent = DivergentAgent(self.session_id, self.config, self.db)
                elif agent_type == "convergent":
                    agent = ConvergentAgent(self.session_id, self.config, self.db)
                elif agent_type == "pragmatist":
                    agent = PragmatistAgent(self.session_id, self.config, self.db)
                elif agent_type == "user_proxy":
                    agent = UserProxyAgent(self.session_id, self.config, self.db)
                elif agent_type == "quantifier":
                    agent = QuantifierAgent(self.session_id, self.config, self.db)
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
                            # Track response start time
                            response_start = time.time()
                            
                            # Mark as thinking and update UI
                            with discussion_lock:
                                agent_status[agent_name] = "thinking"
                                
                                # Track peak concurrent thinking
                                thinking_count = sum(1 for s in agent_status.values() if s == "thinking")
                                stats["peak_concurrent_thinking"] = max(stats["peak_concurrent_thinking"], thinking_count)
                                
                                # Update task result so live viewer sees the status change
                                intermediate_result = {
                                    "status": "in_progress",
                                    "contributions": discussion.copy(),
                                    "rolling_summary": rolling_summary["content"],
                                    "task": user_input,
                                    "agent_status": agent_status.copy(),
                                    "web_search_events": web_search_events.copy()
                                }
                                self.task_repo.set_task_result(task_id, json.dumps(intermediate_result))
                            
                            logger.info(f"{agent_name} is thinking...")
                            
                            # Get agent's contribution
                            response = self._get_async_agent_response(
                                agent_name=agent_name,
                                agent=agent,
                                user_input=user_input,
                                discussion=current_discussion,
                                context=context
                            )
                            
                            # Check if agent requested a web search
                            if response and response.startswith("__WEB_SEARCH_REQUEST__"):
                                search_query = response.replace("__WEB_SEARCH_REQUEST__", "", 1)
                                
                                # Check if WebSearcher is already busy
                                with discussion_lock:
                                    websearcher_status = agent_status.get("WebSearcher", "idle")
                                
                                if websearcher_status == "searching":
                                    # WebSearcher is busy, add to queue and wait
                                    with discussion_lock:
                                        web_search_queue.append({
                                            "agent": agent_name,
                                            "query": search_query
                                        })
                                    logger.info(f"{agent_name} queued web search request (WebSearcher busy). Queue length: {len(web_search_queue)}")
                                    
                                    # Add a contribution informing about waiting
                                    with discussion_lock:
                                        contribution = {
                                            "agent": agent_name,
                                            "content": f"*Waiting for @WebSearcher to finish current search before requesting: '{search_query[:80]}{'...' if len(search_query) > 80 else ''}'*",
                                            "timestamp": time.time(),
                                            "contribution_num": len(discussion) + 1,
                                            "hidden": True  # Don't display to user, but available to agents
                                        }
                                        discussion.append(contribution)
                                        agent_status[agent_name] = "waiting"
                                    
                                    # Agent will check queue on next iteration
                                    continue
                                
                                logger.info(f"{agent_name} requested web search: {search_query[:100]}")
                                
                                # Record web search event and track statistics
                                with discussion_lock:
                                    web_search_events.append({
                                        "agent": agent_name,
                                        "query": search_query,
                                        "timestamp": time.time()
                                    })
                                    agent_status["WebSearcher"] = "searching"
                                    
                                    # Track web search stats
                                    stats["web_searches"] += 1
                                    stats["web_searches_by_agent"][agent_name] = stats["web_searches_by_agent"].get(agent_name, 0) + 1
                                    
                                    # Update UI immediately
                                    intermediate_result = {
                                        "status": "in_progress",
                                        "contributions": discussion.copy(),
                                        "rolling_summary": rolling_summary["content"],
                                        "task": user_input,
                                        "agent_status": agent_status.copy(),
                                        "web_search_events": web_search_events.copy()
                                    }
                                    self.task_repo.set_task_result(task_id, json.dumps(intermediate_result))
                                
                                # Perform web search
                                from queenbee.agents.web_searcher import \
                                    WebSearcherAgent
                                web_searcher = WebSearcherAgent(self.session_id, self.config, self.db)
                                search_results = web_searcher.search(
                                    query=search_query,
                                    requesting_agent=agent_name,
                                    stream=False
                                )
                                
                                # Add search results as a contribution (hidden from display but available to agents)
                                with discussion_lock:
                                    agent_status["WebSearcher"] = "idle"
                                    contribution = {
                                        "agent": "WebSearcher",
                                        "content": f"Search results for '{search_query}':\n\n{search_results}",
                                        "timestamp": time.time(),
                                        "contribution_num": len(discussion) + 1,
                                        "hidden": True  # Don't display in live discussion, but agents can see it
                                    }
                                    discussion.append(contribution)
                                    
                                    # Check if there are queued requests
                                    if web_search_queue:
                                        next_request = web_search_queue.pop(0)
                                        next_agent = next_request["agent"]
                                        next_query = next_request["query"]
                                        logger.info(f"Processing queued web search from {next_agent}: {next_query[:100]}")
                                        
                                        # Set WebSearcher back to searching for queued request
                                        agent_status["WebSearcher"] = "searching"
                                        agent_status[next_agent] = "thinking"
                                        
                                        # Track web search stats
                                        stats["web_searches"] += 1
                                        stats["web_searches_by_agent"][next_agent] = stats["web_searches_by_agent"].get(next_agent, 0) + 1
                                        
                                        # Record web search event
                                        web_search_events.append({
                                            "agent": next_agent,
                                            "query": next_query,
                                            "timestamp": time.time()
                                        })
                                        
                                        # Update UI immediately
                                        intermediate_result = {
                                            "status": "in_progress",
                                            "contributions": discussion.copy(),
                                            "rolling_summary": rolling_summary["content"],
                                            "task": user_input,
                                            "agent_status": agent_status.copy(),
                                            "web_search_events": web_search_events.copy()
                                        }
                                        self.task_repo.set_task_result(task_id, json.dumps(intermediate_result))
                                        
                                        # Perform the queued web search
                                        queued_search_results = web_searcher.search(
                                            query=next_query,
                                            requesting_agent=next_agent,
                                            stream=False
                                        )
                                        
                                        # Add queued search results
                                        queued_contribution = {
                                            "agent": "WebSearcher",
                                            "content": f"Search results for '{next_query}':\n\n{queued_search_results}",
                                            "timestamp": time.time(),
                                            "contribution_num": len(discussion) + 1,
                                            "hidden": True  # Don't display to user
                                        }
                                        discussion.append(queued_contribution)
                                        agent_status["WebSearcher"] = "idle"
                                        agent_status[next_agent] = "idle"
                                    
                                    intermediate_result = {
                                        "status": "in_progress",
                                        "contributions": discussion.copy(),
                                        "rolling_summary": rolling_summary["content"],
                                        "task": user_input,
                                        "agent_status": agent_status.copy(),
                                        "web_search_events": web_search_events.copy()
                                    }
                                    self.task_repo.set_task_result(task_id, json.dumps(intermediate_result))
                                
                                # Let the requesting agent see the results and continue
                                agent_status[agent_name] = "idle"
                                continue
                            
                            if response and not response.startswith("__WEB_SEARCH_REQUEST__") and not response.strip().upper().startswith("[PASS"):
                                # Clean up response by removing tool-calling syntax
                                response_text = str(response)
                                # Remove all <|...|> tags and their content
                                import re
                                response_text = re.sub(r'<\|[^|]*\|>[^<]*', '', response_text)
                                # Remove standalone <|...|> tags
                                response_text = re.sub(r'<\|[^|]*\|>', '', response_text)
                                # Clean up extra whitespace
                                response_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', response_text).strip()
                                
                                if not response_text or len(response_text) < 10:
                                    # Response was all tool syntax, treat as pass
                                    logger.info(f"{agent_name} response was only tool syntax, treating as pass")
                                    agent_status[agent_name] = "idle"
                                    
                                    # Track pass
                                    with discussion_lock:
                                        stats["agent_passes"][agent_name] = stats["agent_passes"].get(agent_name, 0) + 1
                                    continue
                                
                                # Track response time
                                response_time = time.time() - response_start
                                with discussion_lock:
                                    if agent_name not in stats["agent_response_times"]:
                                        stats["agent_response_times"][agent_name] = []
                                    stats["agent_response_times"][agent_name].append(response_time)
                                
                                # Mark as contributing
                                with discussion_lock:
                                    agent_status[agent_name] = "contributing"
                                
                                contribution = {
                                    "agent": agent_name,
                                    "content": response_text,
                                    "timestamp": time.time(),
                                    "contribution_num": contribution_count + 1
                                }
                                
                                # Add to shared discussion
                                with discussion_lock:
                                    discussion.append(contribution)
                                    
                                    # Track contribution count
                                    stats["agent_contributions"][agent_name] = stats["agent_contributions"].get(agent_name, 0) + 1
                                    
                                    # Store intermediate result with agent status and rolling summary
                                    intermediate_result = {
                                        "status": "in_progress",
                                        "contributions": discussion.copy(),
                                        "rolling_summary": rolling_summary["content"],
                                        "task": user_input,
                                        "agent_status": agent_status.copy(),
                                        "web_search_events": web_search_events.copy()
                                    }
                                    self.task_repo.set_task_result(task_id, json.dumps(intermediate_result))
                                
                                contribution_count += 1
                                logger.info(f"{agent_name} contributed (#{contribution_count})")
                                
                                # Reset pass count when agent contributes
                                with discussion_lock:
                                    agent_pass_count[agent_name] = 0
                                    last_contribution_round[agent_name] = len(discussion)
                            else:
                                # Track explicit pass
                                with discussion_lock:
                                    stats["agent_passes"][agent_name] = stats["agent_passes"].get(agent_name, 0) + 1
                                    agent_pass_count[agent_name] = agent_pass_count.get(agent_name, 0) + 1
                                    
                                    logger.info(f"{agent_name} passed (pass count: {agent_pass_count[agent_name]})")
                                    
                                    # Check if ALL agents have passed consecutively
                                    all_agents_in_discussion = [a for a in agent_status.keys() if a != "WebSearcher"]
                                    all_passed = all(
                                        agent_pass_count.get(agent, 0) >= 1 
                                        for agent in all_agents_in_discussion
                                    )
                                    
                                    if all_passed and len(discussion) >= 2:  # At least some discussion happened
                                        logger.info(f"All {len(all_agents_in_discussion)} agents have passed. Ending discussion.")
                                        stop_event.set()
                                        break
                        
                        # Mark as idle after decision/contribution and update UI
                        with discussion_lock:
                            agent_status[agent_name] = "idle"
                            
                            # Update task result so live viewer sees the status change
                            intermediate_result = {
                                "status": "in_progress",
                                "contributions": discussion.copy(),
                                "rolling_summary": rolling_summary["content"],
                                "task": user_input,
                                "agent_status": agent_status.copy(),
                                "web_search_events": web_search_events.copy()
                            }
                            self.task_repo.set_task_result(task_id, json.dumps(intermediate_result))
                        
                        # Wait a bit before checking again (let others contribute)
                        time.sleep(2)
                
                finally:
                    agent.terminate()
        
        # Start rolling summary thread
        summary_thread = threading.Thread(
            target=update_rolling_summary,
            daemon=True
        )
        summary_thread.start()
        logger.info("Started rolling summary thread")
        
        # Start agent threads
        threads = []
        agents = [
            ("Divergent", "divergent"),
            ("Convergent", "convergent"),
            ("Critical", "critical"),
            ("Pragmatist", "pragmatist"),
            ("UserProxy", "user_proxy"),
            ("Quantifier", "quantifier")
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
        
        # Give agents a moment to initialize, then send initial status
        time.sleep(0.5)
        with discussion_lock:
            # Store initial state so live viewer has something to display immediately
            initial_result = {
                "status": "in_progress",
                "contributions": [],
                "rolling_summary": "",
                "task": user_input,
                "agent_status": agent_status.copy(),
                "web_search_events": web_search_events.copy()
            }
            self.task_repo.set_task_result(task_id, json.dumps(initial_result))
        logger.info("Sent initial status to live viewer")
        
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
                if all_idle_count >= 15:  # 15 seconds of all idle
                    logger.info("All agents idle for 15 seconds, stopping discussion")
                    break
            else:
                # Reset counter if any agent is active
                all_idle_count = 0
        
        # Signal all agents to stop
        stop_event.set()
        
        # Wait for threads to finish (with timeout)
        for thread in threads:
            thread.join(timeout=5)
        
        # Wait for summary thread
        summary_thread.join(timeout=3)
        
        # Get the last rolling summary
        with discussion_lock:
            last_rolling = rolling_summary["content"]
        
        # Calculate final statistics
        end_time = time.time()
        duration = end_time - start_time
        
        # Calculate average response times
        avg_response_times = {}
        for agent, times in stats["agent_response_times"].items():
            if times:
                avg_response_times[agent] = sum(times) / len(times)
        
        # Compile final statistics
        final_stats = {
            "duration_seconds": round(duration, 2),
            "total_messages": len(discussion),
            "contributions_per_agent": stats["agent_contributions"],
            "passes_per_agent": stats["agent_passes"],
            "web_searches_total": stats["web_searches"],
            "web_searches_by_agent": stats["web_searches_by_agent"],
            "average_response_time_seconds": {k: round(v, 2) for k, v in avg_response_times.items()},
            "peak_concurrent_thinking": stats["peak_concurrent_thinking"],
            # Token stats will be added when we track LLM usage
            "token_usage_per_agent": stats.get("agent_tokens", {})
        }
        
        logger.info(f"Discussion complete - Duration: {duration:.2f}s, Messages: {len(discussion)}")
        
        # Generate final comprehensive summary from Queen using the rolling summary
        logger.info("Generating Queen's final summary...")
        final_summary = self._generate_queen_summary(user_input, discussion, last_rolling)
        
        return {
            "task": user_input,
            "context": context,
            "total_contributions": len(discussion),
            "contributions": discussion,
            "rolling_summary": last_rolling,  # Last rolling summary from live updates
            "summary": final_summary,  # Final comprehensive summary
            "statistics": final_stats  # Discussion statistics
        }

    def _generate_queen_summary(self, user_input: str, discussion: list[dict], rolling_summary: str = "") -> str:
        """Generate final synthesis using SummarizerAgent.
        
        Args:
            user_input: Original question.
            discussion: Full discussion history.
            rolling_summary: The last rolling summary generated during discussion.
            
        Returns:
            Final synthesis from SummarizerAgent.
        """
        if not discussion:
            return "No discussion occurred."
        
        # Use SummarizerAgent to generate final synthesis
        from queenbee.agents.summarizer import SummarizerAgent
        
        with self.db:
            summarizer = SummarizerAgent(self.session_id, self.config, self.db)
            
            try:
                synthesis = summarizer.generate_final_synthesis(
                    user_input=user_input,
                    contributions=discussion,
                    rolling_summary=rolling_summary,
                    stream=False
                )
                summarizer.terminate()
                return str(synthesis)
            except Exception as e:
                logger.error(f"Error generating final synthesis: {e}")
                summarizer.terminate()
                return "Unable to generate summary."

    def _should_agent_contribute(
        self, 
        agent_name: str, 
        discussion: list[dict], 
        user_input: str,
        contribution_count: int
    ) -> bool:
        """Intelligently decide if agent should contribute based on relevance and discussion state.
        
        Args:
            agent_name: Name of the agent.
            discussion: Current discussion history.
            user_input: Original question.
            contribution_count: How many times this agent has contributed.
            
        Returns:
            True if agent should try to contribute.
        """
        # First contribution - assess relevance before jumping in
        if contribution_count == 0:
            # For first 2 contributions total, let first agents contribute freely
            if len(discussion) < 2:
                return True
            # After that, check if agent's expertise is relevant
            return self._is_agent_expertise_relevant(agent_name, user_input, discussion)
        
        # Prevent consecutive contributions from same agent
        if discussion:
            last_contrib = discussion[-1]
            if last_contrib["agent"] == agent_name:
                return False
            
            # Prevent dominating discussion - check last 3 contributions
            if len(discussion) >= 3:
                recent = [d["agent"] for d in discussion[-3:]]
                if recent.count(agent_name) >= 2:
                    return False
        
        # Hard limit: max 3 contributions per agent (quality over quantity)
        if contribution_count >= 3:
            return False
        
        # Early discussion (< 6 contributions): Be more selective
        if len(discussion) < 6:
            # Only contribute if relevant to current discussion direction
            return self._is_contribution_needed(agent_name, discussion)
        
        # Mid discussion (6-12 contributions): Very selective
        if len(discussion) < 12:
            # Only if expertise directly addresses a gap
            if contribution_count >= 2:
                return False
            return self._is_agent_expertise_relevant(agent_name, user_input, discussion)
        
        # Late discussion (12+ contributions): Almost never contribute
        # Discussion should be converging, not expanding
        return False
    
    def _is_agent_expertise_relevant(
        self,
        agent_name: str,
        user_input: str,
        discussion: list[dict]
    ) -> bool:
        """Assess if agent's expertise is relevant to the question and current discussion.
        
        Args:
            agent_name: Name of the agent.
            user_input: Original user question.
            discussion: Current discussion history.
            
        Returns:
            True if agent's expertise is relevant.
        """
        user_input_lower = user_input.lower()
        
        # Keywords that indicate agent expertise relevance
        relevance_keywords = {
            "Divergent": ["options", "alternatives", "possibilities", "approaches", "ideas", "creative", "different ways", "what if"],
            "Convergent": ["decide", "choose", "recommend", "best", "solution", "action", "implement", "plan", "synthesis"],
            "Critical": ["risks", "problems", "concerns", "issues", "validate", "verify", "wrong", "fail", "security", "flaws"],
            "Pragmatist": ["practical", "feasible", "implement", "resources", "cost", "timeline", "realistic", "constraints"],
            "UserProxy": ["user", "experience", "usability", "customer", "audience", "accessible", "interface", "ux"],
            "Quantifier": ["metrics", "numbers", "measure", "data", "performance", "benchmark", "statistics", "quantify"],
        }
        
        keywords = relevance_keywords.get(agent_name, [])
        
        # Check if question mentions relevant keywords
        question_relevance = any(kw in user_input_lower for kw in keywords)
        
        # Check if recent discussion mentions relevant concepts
        if discussion:
            recent_discussion = " ".join([d["content"].lower() for d in discussion[-3:]])
            discussion_relevance = any(kw in recent_discussion for kw in keywords)
        else:
            discussion_relevance = False
        
        return question_relevance or discussion_relevance
    
    def _is_contribution_needed(
        self,
        agent_name: str,
        discussion: list[dict]
    ) -> bool:
        """Determine if agent's contribution would add value to current discussion.
        
        Args:
            agent_name: Name of the agent.
            discussion: Current discussion history.
            
        Returns:
            True if contribution is likely needed.
        """
        if not discussion:
            return True
        
        # Check if agent's perspective is missing
        agent_names_contributed = {d["agent"] for d in discussion}
        
        # Core agents (Divergent, Convergent, Critical) should contribute early
        core_agents = {"Divergent", "Convergent", "Critical"}
        if agent_name in core_agents:
            # If not all core agents have contributed yet, let them contribute
            if not core_agents.issubset(agent_names_contributed):
                return True
        
        # Support agents (Pragmatist, UserProxy, Quantifier) contribute when needed
        support_agents = {"Pragmatist", "UserProxy", "Quantifier"}
        if agent_name in support_agents:
            # Wait until core discussion has started (at least 2 contributions)
            if len(discussion) < 2:
                return False
            # Only contribute if can add specific value
            return agent_name not in agent_names_contributed
        
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
        
        # Get max_tokens from config for token limit instruction
        # Use getattr with default to handle MagicMock in tests
        max_tokens_divergent = getattr(self.config.agents.divergent, 'max_tokens', 0)
        max_tokens_convergent = getattr(self.config.agents.convergent, 'max_tokens', 0)
        max_tokens_critical = getattr(self.config.agents.critical, 'max_tokens', 0)
        
        # Ensure they are integers (handle MagicMock in tests)
        if not isinstance(max_tokens_divergent, int):
            max_tokens_divergent = 0
        if not isinstance(max_tokens_convergent, int):
            max_tokens_convergent = 0
        if not isinstance(max_tokens_critical, int):
            max_tokens_critical = 0
        
        # Build agent-specific prompt with explicit instruction to check for new value
        if agent_name == "Divergent":
            token_instruction = f"Maximum {max_tokens_divergent} tokens" if max_tokens_divergent > 0 else "Keep it concise"
            prompt = f"""Original question: {user_input}

{f'{context}\n' if context else ''}
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

IMPORTANT - WEB SEARCH FIRST:
- If the question involves current events, recent data, specific facts, benchmarks, or real-world examples, ALWAYS request a web search FIRST
- Don't rely on your training data for factual claims - get real sources
- Request search naturally: "Hey @WebSearcher! Search for [your query]"
- Examples: latest pricing, current statistics, recent developments, specific company info, technical benchmarks
- After getting search results, you can then contribute your perspective based on actual data

KEEP IT BRIEF: {token_instruction}. Be specific and concrete. Add genuine value, not repetition."""

        elif agent_name == "Convergent":
            token_instruction = f"Maximum {max_tokens_convergent} tokens" if max_tokens_convergent > 0 else "Keep it concise"
            prompt = f"""Original question: {user_input}

{f'{context}\n' if context else ''}
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

IMPORTANT - WEB SEARCH FIRST:
- If your synthesis requires current data, pricing, performance metrics, or specific real-world examples, ALWAYS request a web search FIRST
- Don't make recommendations based on outdated training data - get real sources
- Request search naturally: "Hey @WebSearcher! Search for [your query]"
- Examples: current best practices, actual costs, real performance data, existing solutions
- Base your synthesis on actual verified information, not assumptions

KEEP IT BRIEF: {token_instruction} (roughly 1-2 sentences). Be specific about what you're adding beyond what's already been said."""

        elif agent_name == "Pragmatist":
            token_instruction = f"Maximum {max_tokens_convergent} tokens" if max_tokens_convergent > 0 else "Keep it concise"
            prompt = f"""Original question: {user_input}

{f'{context}\n' if context else ''}
Discussion so far:
{discussion_text if discussion_text else "No discussion yet - you'll be the first to contribute."}

You are the Pragmatist. Your role is to ground discussions in practical reality and implementation feasibility.

CRITICAL: Before responding, carefully analyze what has ALREADY been said:
1. Review all proposed solutions and approaches
2. Check what feasibility concerns have been raised
3. Ask yourself: "What NEW practical constraint or reality check can I provide?"

Respond with [PASS] if:
- Practical constraints have been thoroughly covered
- Feasibility has been adequately addressed
- You would just be repeating existing reality checks

Only contribute if you can add:
- NEW practical constraints (time, resources, skills, budget)
- Realistic assessment of what's actually buildable
- Incremental or "good enough" alternatives
- Technical feasibility concerns not yet mentioned
- Resource or timeline reality checks

IMPORTANT - WEB SEARCH FIRST:
- If you need data on implementation timelines, resource requirements, or real-world feasibility, ALWAYS request a web search FIRST
- Don't guess about costs or timelines - get actual data
- Request search naturally: "Hey @WebSearcher! Search for [your query]"
- Examples: typical implementation times, resource requirements, real project costs, case studies
- Base your feasibility assessment on real-world data, not assumptions

KEEP IT BRIEF: {token_instruction} (roughly 1-2 sentences). Focus on practical constraints and what's actually achievable."""

        elif agent_name == "Critical":
            token_instruction = f"Maximum {max_tokens_critical} tokens" if max_tokens_critical > 0 else "Keep it concise"
            prompt = f"""Original question: {user_input}

{f'{context}\n' if context else ''}
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

IMPORTANT - WEB SEARCH FIRST:
- If you need to validate claims with real data, check for known issues, or verify technical details, ALWAYS request a web search FIRST
- Don't assume risks based on outdated knowledge - check current information
- Request search naturally: "Hey @WebSearcher! Search for [your query]"
- Examples: known security vulnerabilities, actual failure cases, documented limitations, compatibility issues
- Base your critique on verified real-world evidence, not speculation

KEEP IT BRIEF: {token_instruction} (roughly 1-2 sentences). Be specific about the new concern or validation you're adding."""

        elif agent_name == "UserProxy":
            token_instruction = f"Maximum {max_tokens_convergent} tokens" if max_tokens_convergent > 0 else "Keep it concise"
            prompt = f"""Original question: {user_input}

{f'{context}\n' if context else ''}
Discussion so far:
{discussion_text if discussion_text else "No discussion yet - you'll be the first to contribute."}

You are the UserProxy. Your role is to represent the end-user perspective and ensure solutions serve actual user needs.

CRITICAL: Before responding, carefully analyze what has ALREADY been said:
1. Review all proposed solutions and technical approaches
2. Check what user-focused concerns have been raised
3. Ask yourself: "What NEW user perspective can I provide?"

Respond with [PASS] if:
- User needs and experience have been thoroughly considered
- User impact has been adequately addressed
- You would just be repeating existing user advocacy

Only contribute if you can add:
- NEW user needs or pain points not yet mentioned
- User experience concerns overlooked by technical discussion
- Challenge to technical complexity that doesn't serve users
- User value assessment of proposed solutions
- Accessibility or usability concerns

IMPORTANT - WEB SEARCH FIRST:
- If you need data on user behavior, feedback, or usability research, ALWAYS request a web search FIRST
- Don't assume what users want - get real user data
- Request search naturally: "Hey @WebSearcher! Search for [your query]"
- Examples: user research, surveys, common complaints, usability studies, accessibility standards
- Base your advocacy on actual user evidence, not assumptions

KEEP IT BRIEF: {token_instruction} (roughly 1-2 sentences). Focus on user needs and whether solutions serve actual users."""

        elif agent_name == "Quantifier":
            token_instruction = f"Maximum {max_tokens_convergent} tokens" if max_tokens_convergent > 0 else "Keep it concise"
            prompt = f"""Original question: {user_input}

{f'{context}\n' if context else ''}
Discussion so far:
{discussion_text if discussion_text else "No discussion yet - you'll be the first to contribute."}

You are the Quantifier. Your role is to ground discussions in concrete numbers, metrics, and measurable outcomes.

CRITICAL: Before responding, carefully analyze what has ALREADY been said:
1. Review all discussions for vague qualitative claims
2. Check what metrics and numbers have been defined
3. Ask yourself: "What NEW quantitative perspective can I provide?"

Respond with [PASS] if:
- Concrete metrics and numbers have been thoroughly defined
- Success criteria with thresholds already established
- You would just be repeating existing quantitative analysis

Only contribute if you can add:
- NEW specific metrics or measurable criteria not yet defined
- Challenge vague terms ("faster," "better," "scalable") with "how much?"
- Concrete success thresholds and acceptance criteria
- Cost/benefit analysis with actual numbers
- Performance benchmarks or industry standards

IMPORTANT - WEB SEARCH FIRST:
- If you need actual benchmarks, costs, performance data, or industry metrics, ALWAYS request a web search FIRST
- Don't estimate or guess numbers - get real data
- Request search naturally: "Hey @WebSearcher! Search for [your query]"
- Examples: performance benchmarks, pricing comparisons, industry standards, typical metrics
- Base your quantitative analysis on actual verified data, not estimates

KEEP IT BRIEF: {token_instruction} (roughly 1-2 sentences). Demand specific numbers and define concrete metrics."""

        # Get max_tokens from config based on agent type
        max_tokens = 0  # default no limit
        if agent_name == "Divergent":
            max_tokens = self.config.agents.divergent.max_tokens
        elif agent_name == "Convergent":
            max_tokens = self.config.agents.convergent.max_tokens
        elif agent_name == "Critical":
            max_tokens = self.config.agents.critical.max_tokens
        elif agent_name == "Pragmatist":
            max_tokens = self.config.agents.convergent.max_tokens  # Use same as convergent for now
        elif agent_name == "UserProxy":
            max_tokens = self.config.agents.convergent.max_tokens  # Use same as convergent for now
        elif agent_name == "Quantifier":
            max_tokens = self.config.agents.convergent.max_tokens  # Use same as convergent for now
        
        # Get response from agent with max_tokens from config
        try:
            response = agent.generate_response(
                prompt, 
                stream=False,
                max_tokens=max_tokens if max_tokens > 0 else None
            )
            
            # Check if agent is requesting a web search (natural language pattern)
            if response and isinstance(response, str):
                response_text = str(response).strip()
                # Detect patterns like "Hey @WebSearcher! Search for X" or "@WebSearcher, search X"
                import re
                web_search_pattern = r'@WebSearcher[!,.]?\s*[Ss]earch\s+(?:for\s+)?["\']?([^"\'.\n]+)["\']?'
                match = re.search(web_search_pattern, response_text, re.IGNORECASE)
                if match:
                    search_query = match.group(1).strip()
                    return f"__WEB_SEARCH_REQUEST__{search_query}"
            
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
    # Load configuration first to get logging settings
    config = load_config(config_path)
    
    # Set up logging for worker process with config settings
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper()),
        format="[Worker] %(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True  # Override any previous basicConfig
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Worker process started for session {session_id}")

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
