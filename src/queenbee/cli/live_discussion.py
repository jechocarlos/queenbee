"""Live discussion viewer - shows agents thinking and contributing in real-time."""

import json
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from queenbee.db.models import TaskRepository


class LiveDiscussionViewer:
    """Real-time viewer for agent discussions."""

    AGENT_COLORS = {
        "Divergent": "bright_magenta",
        "Convergent": "bright_cyan",
        "Critical": "bright_yellow",
    }

    AGENT_EMOJIS = {
        "Divergent": "🌟",
        "Convergent": "🔗",
        "Critical": "🔍",
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
        self.console = console
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
        
        with Live(
            self._generate_layout("", [], "", {}),
            console=self.console,
            refresh_per_second=2,
            vertical_overflow="visible"
        ) as live:
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
                            # Show final state
                            contributions = result.get("contributions", [])
                            rolling_summary = result.get("rolling_summary", "")
                            final_summary = result.get("summary", "")
                            user_task = result.get("task", "")
                            
                            live.update(
                                self._generate_layout(
                                    user_task,
                                    contributions,
                                    rolling_summary if rolling_summary else final_summary,
                                    {},
                                    is_complete=True
                                )
                            )
                            time.sleep(2)  # Let user see final state
                            return result
                        
                        # Discussion in progress
                        if result.get("status") == "in_progress":
                            contributions = result.get("contributions", [])
                            rolling_summary = result.get("rolling_summary", "")
                            user_task = result.get("task", "")
                            agent_status = result.get("agent_status", {})
                            
                            # Update display
                            live.update(
                                self._generate_layout(
                                    user_task,
                                    contributions,
                                    rolling_summary,
                                    agent_status
                                )
                            )
                            
                            self.last_contribution_count = len(contributions)
                    except json.JSONDecodeError:
                        pass
                
                time.sleep(0.5)  # Poll every 500ms
        
        # Timeout reached
        task = self.task_repo.get_task(self.task_id)
        if task and task.get("result"):
            return json.loads(task["result"])
        return {"error": "Timeout reached"}

    def _generate_layout(
        self,
        task: str,
        contributions: list[dict],
        summary: str,
        agent_status: dict[str, str],
        is_complete: bool = False
    ) -> Layout:
        """Generate the live display layout.

        Args:
            task: User's original task/question.
            contributions: List of agent contributions so far.
            summary: Current rolling summary or final summary.
            agent_status: Dict of agent_name -> status (idle/thinking/contributing).
            is_complete: Whether the discussion is complete.

        Returns:
            Rich Layout object.
        """
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="status", size=6),  # Space for 4 agents (Divergent, Convergent, Critical, Summarizer)
        )
        
        # Header - show task
        if task:
            task_text = Text(f"📋 Task: {task[:80]}{'...' if len(task) > 80 else ''}")
            layout["header"].update(Panel(task_text, border_style="cyan"))
        
        # Main area - split between discussion and summary
        layout["main"].split_row(
            Layout(name="discussion", ratio=3),
            Layout(name="summary", ratio=2),
        )
        
        # Discussion panel - show contributions
        discussion_content = self._render_discussion(contributions, is_complete)
        layout["discussion"].update(
            Panel(
                discussion_content,
                title="[bold bright_white]🗨️  Live Discussion[/bold bright_white]",
                border_style="bright_white" if not is_complete else "green",
            )
        )
        
        # Summary panel
        summary_content = self._render_summary(summary, is_complete)
        layout["summary"].update(
            Panel(
                summary_content,
                title="[bold yellow]📝 Summary[/bold yellow]",
                border_style="yellow",
            )
        )
        
        # Status bar - show agent activity (sized for 4 agents)
        agent_content = self._render_agent_status(agent_status, is_complete)
        layout["status"].update(
            Panel(
                agent_content,
                title="[bold blue]� Agent Activity[/bold blue]",
                border_style="blue",
            )
        )
        
        return layout

    def _render_discussion(self, contributions: list[dict], is_complete: bool) -> Group:
        """Render the discussion as a chatroom-style display.

        Args:
            contributions: List of contributions.
            is_complete: Whether discussion is complete.

        Returns:
            Rich Group with contributions.
        """
        if not contributions:
            if is_complete:
                return Group(Text("No contributions made.", style="dim italic"))
            else:
                return Group(Text("💬 Waiting for agents to contribute...", style="dim italic cyan"))
        
        # Show LATEST 10 contributions (chatroom style - newest at bottom)
        visible_contributions = contributions[-10:]
        
        messages = []
        
        # Show indicator if there are earlier messages
        if len(contributions) > 10:
            hidden_count = len(contributions) - 10
            messages.append(Text(f"⬆️  {hidden_count} earlier messages", style="dim italic cyan"))
            messages.append(Text(""))  # Blank line
        
        # Render each contribution like a chat message
        for i, contrib in enumerate(visible_contributions):
            agent_name = contrib.get("agent", "Unknown")
            content = contrib.get("content", "")
            
            # Get agent styling
            color = self.AGENT_COLORS.get(agent_name, "white")
            emoji = self.AGENT_EMOJIS.get(agent_name, "🤖")
            
            # Chat message format: [Emoji Name]: message
            # Highlight the newest message
            is_newest = (i == len(visible_contributions) - 1) and not is_complete
            
            if is_newest:
                # Newest message gets a subtle highlight
                agent_line = Text(f"✨ {emoji} {agent_name}", style=f"bold {color} on #1a1a1a")
            else:
                agent_line = Text(f"{emoji} {agent_name}", style=f"bold {color}")
            
            message_line = Text(content, style=color if not is_newest else f"{color} on #1a1a1a")
            
            messages.append(agent_line)
            messages.append(message_line)
            messages.append(Text(""))  # Blank line between messages
        
        return Group(*messages)

    def _render_summary(self, summary: str, is_complete: bool) -> Text:
        """Render the summary text.

        Args:
            summary: Current summary text.
            is_complete: Whether discussion is complete.

        Returns:
            Rich Text object.
        """
        if not summary:
            if is_complete:
                return Text("No summary available.", style="dim italic")
            else:
                return Text("Generating summary...", style="dim italic")
        
        # Show complete summary without truncation
        style = "green" if is_complete else "white"
        return Text(summary, style=style)

    def _render_agent_status(self, agent_status: dict[str, str], is_complete: bool) -> Group:
        """Render agent status indicators.

        Args:
            agent_status: Dict of agent_name -> status.
            is_complete: Whether discussion is complete.

        Returns:
            Rich Group with status indicators.
        """
        if is_complete:
            status_text = Text("✅ Discussion Complete", style="bold green")
            return Group(status_text)
        
        if not agent_status:
            status_text = Text("⏳ Initializing agents...", style="dim")
            return Group(status_text)
        
        # Create status line for each agent
        status_lines = []
        for agent_name in ["Divergent", "Convergent", "Critical"]:
            status = agent_status.get(agent_name, "idle")
            indicator = self.STATUS_INDICATORS.get(status, "❓")
            color = self.AGENT_COLORS.get(agent_name, "white")
            emoji = self.AGENT_EMOJIS.get(agent_name, "🤖")
            
            status_display = Text()
            status_display.append(f"{emoji} {agent_name}: ", style=f"bold {color}")
            status_display.append(f"{indicator} {status}", style=color)
            status_lines.append(status_display)
        
        return Group(*status_lines)
