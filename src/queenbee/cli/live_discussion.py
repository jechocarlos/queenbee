"""Live discussion viewer - shows agents thinking and contributing in real-time."""

import json
import time
from typing import Any
from uuid import UUID

from rich.console import Console

from queenbee.db.models import TaskRepository


class LiveDiscussionViewer:
    """Real-time viewer for agent discussions."""

    AGENT_COLORS = {
        "Divergent": "bright_magenta",
        "Convergent": "bright_cyan",
        "Critical": "bright_yellow",
        "WebSearcher": "bright_green",
    }

    AGENT_EMOJIS = {
        "Divergent": "🌟",
        "Convergent": "🔗",
        "Critical": "🔍",
        "WebSearcher": "🔎",
    }

    STATUS_INDICATORS = {
        "idle": "💤",
        "thinking": "💭",
        "contributing": "✍️",
    }

    def __init__(self, console: Console, task_repo: TaskRepository, task_id: UUID):
        """Initialize live discussion viewer.

        Args:
            console: Rich console for output.
            task_repo: Task repository to poll for updates.
            task_id: Task ID to monitor.
        """
        # Force word wrapping by setting soft_wrap=True
        self.console = Console(soft_wrap=True) if not isinstance(console, Console) else console
        self.console.soft_wrap = True  # Enable word wrap
        self.task_repo = task_repo
        self.task_id = task_id
        self.last_contribution_count = 0
        self.last_summary_update = 0

    def watch_discussion(self, timeout: int = 120) -> dict[str, Any]:
        """Watch the discussion in real-time and display updates.

        Args:
            timeout: Maximum time to watch in seconds.

        Returns:
            Final task result.
        """
        start_time = time.time()
        
        # Print header
        self.console.print("\n" + "=" * 80, style="cyan")
        self.console.print("LIVE DISCUSSION", style="bold bright_white", justify="center")
        self.console.print("=" * 80, style="cyan")
        self.console.print()
        
        last_contribution_count = 0
        last_summary = ""
        last_agent_status = {}  # Track last agent status to avoid spam
        displayed_contributions = set()  # Track which contributions we've printed
        displayed_web_searches = set()  # Track which web search events we've printed
        
        while time.time() - start_time < timeout:
            # Poll task for updates
            task = self.task_repo.get_task(self.task_id)
            
            if not task:
                break
            
            status = task["status"]
            result_json = task.get("result")
            
            # Parse current state
            if result_json:
                try:
                    result = json.loads(result_json)
                    
                    # Check if discussion is complete
                    if status in ["completed", "failed"]:
                        contributions = result.get("contributions", [])
                        
                        # Print any remaining contributions we haven't shown
                        for i, contrib in enumerate(contributions):
                            contrib_id = f"{contrib.get('agent', '')}_{i}"
                            if contrib_id not in displayed_contributions:
                                self._print_contribution(contrib, is_new=False)
                                displayed_contributions.add(contrib_id)
                        
                        # Print final summary
                        final_summary = result.get("summary", "")
                        if final_summary:
                            self.console.print()
                            self.console.print("─" * 80, style="green")
                            self.console.print("📝 FINAL SUMMARY", style="bold green")
                            self.console.print(final_summary, style="green", soft_wrap=True)
                            self.console.print("─" * 80, style="green")
                        
                        self.console.print()
                        self.console.print("✓ Discussion complete!", style="bold green")
                        return result
                    
                    # Discussion in progress - print new contributions as they arrive
                    contributions = result.get("contributions", [])
                    rolling_summary = result.get("rolling_summary", "")
                    agent_status = result.get("agent_status", {})
                    web_search_events = result.get("web_search_events", [])
                    
                    # Track if we printed anything this iteration
                    printed_something = False
                    
                    # Print new web search requests
                    if web_search_events:
                        for i, event in enumerate(web_search_events):
                            event_id = f"{event.get('agent', '')}_{event.get('query', '')}_{i}"
                            if event_id not in displayed_web_searches:
                                agent = event.get('agent', 'Unknown')
                                query = event.get('query', '')
                                # Show full query without truncation
                                self.console.print(f"🔎 WebSearcher: helping {agent} with query '{query}'", style="bright_green")
                                displayed_web_searches.add(event_id)
                                printed_something = True
                    
                    # Print new contributions
                    if len(contributions) > last_contribution_count:
                        for i in range(last_contribution_count, len(contributions)):
                            contrib = contributions[i]
                            # Skip hidden contributions (like web search results)
                            if contrib.get("hidden", False):
                                continue
                            contrib_id = f"{contrib.get('agent', '')}_{i}"
                            if contrib_id not in displayed_contributions:
                                self._print_contribution(contrib, is_new=True)
                                displayed_contributions.add(contrib_id)
                                printed_something = True
                        last_contribution_count = len(contributions)
                    
                    # Print/update rolling summary if changed
                    if rolling_summary and rolling_summary != last_summary:
                        self.console.print()
                        self.console.print("─" * 80, style="dim green")
                        self.console.print("📝 Summary (updating...)", style="green")
                        self.console.print(rolling_summary, style="green", soft_wrap=True)
                        self.console.print("─" * 80, style="dim green")
                        last_summary = rolling_summary
                        printed_something = True
                    
                    # Show agent activity status only when individual agents change status
                    # This prevents status from interrupting/cutting off agent responses
                    if agent_status and not printed_something:
                        # Only print agents whose status actually changed
                        for agent, agent_stat in agent_status.items():
                            if agent not in last_agent_status or last_agent_status[agent] != agent_stat:
                                emoji = self.AGENT_EMOJIS.get(agent, "🤖")
                                self.console.print(f"{emoji} {agent}: {agent_stat}", style="dim cyan")
                        last_agent_status = agent_status.copy()
                    elif agent_status != last_agent_status:
                        # Still track the change even if we didn't print it
                        last_agent_status = agent_status.copy()
                    
                except json.JSONDecodeError:
                    pass
            
            time.sleep(0.2)  # Poll every 200ms
        
        # Timeout reached
        self.console.print("\n⚠️  Timeout reached", style="yellow")
        task = self.task_repo.get_task(self.task_id)
        if task and task.get("result"):
            return json.loads(task["result"])
        return {"error": "Timeout reached"}
    
    def _print_contribution(self, contrib: dict, is_new: bool = False) -> None:
        """Print a single contribution to the terminal.
        
        Args:
            contrib: Contribution dictionary with 'agent' and 'content'.
            is_new: Whether this is a brand new contribution (adds visual indicator).
        """
        agent_name = contrib.get("agent", "Unknown")
        content = contrib.get("content", "")
        
        # Get agent styling
        color = self.AGENT_COLORS.get(agent_name, "white")
        emoji = self.AGENT_EMOJIS.get(agent_name, "🤖")
        
        # Print agent name with emoji
        prefix = "✨ " if is_new else ""
        self.console.print(f"{prefix}{emoji} {agent_name}", style=f"bold {color}")
        
        # Print content with word wrapping enabled
        self.console.print(content, style=color, soft_wrap=True)
        self.console.print()  # Blank line
