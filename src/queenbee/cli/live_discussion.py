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
        self.console.print("💬 LIVE DISCUSSION", style="bold bright_white", justify="center")
        self.console.print("=" * 80, style="cyan")
        self.console.print()
        
        last_contribution_count = 0
        last_summary = ""
        last_agent_status = {}  # Track last agent status to avoid spam
        displayed_contributions = set()  # Track which contributions we've printed
        
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
                            self.console.print("─" * 80, style="yellow")
                            self.console.print("📝 FINAL SUMMARY", style="bold yellow")
                            self.console.print(final_summary, style="yellow", soft_wrap=True)
                            self.console.print("─" * 80, style="yellow")
                        
                        self.console.print()
                        self.console.print("✓ Discussion complete!", style="bold green")
                        return result
                    
                    # Discussion in progress - print new contributions as they arrive
                    contributions = result.get("contributions", [])
                    rolling_summary = result.get("rolling_summary", "")
                    agent_status = result.get("agent_status", {})
                    
                    # Track if we printed anything this iteration
                    printed_something = False
                    
                    # Print new contributions
                    if len(contributions) > last_contribution_count:
                        for i in range(last_contribution_count, len(contributions)):
                            contrib = contributions[i]
                            contrib_id = f"{contrib.get('agent', '')}_{i}"
                            if contrib_id not in displayed_contributions:
                                self._print_contribution(contrib, is_new=True)
                                displayed_contributions.add(contrib_id)
                                printed_something = True
                        last_contribution_count = len(contributions)
                    
                    # Print/update rolling summary if changed
                    if rolling_summary and rolling_summary != last_summary:
                        self.console.print()
                        self.console.print("─" * 80, style="dim yellow")
                        self.console.print("📝 Summary (updating...)", style="yellow")
                        self.console.print(rolling_summary, style="yellow", soft_wrap=True)
                        self.console.print("─" * 80, style="dim yellow")
                        last_summary = rolling_summary
                        printed_something = True
                    
                    # Show agent activity status only if it changed AND we didn't just print content
                    # This prevents status from interrupting/cutting off agent responses
                    if agent_status and agent_status != last_agent_status and not printed_something:
                        status_parts = []
                        for agent, agent_stat in agent_status.items():
                            emoji = self.AGENT_EMOJIS.get(agent, "🤖")
                            status_parts.append(f"{emoji} {agent}: {agent_stat}")
                        if status_parts:
                            self.console.print(f"  [{', '.join(status_parts)}]", style="dim cyan")
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
            Layout(name="discussion"),  # Main chat area (full width)
            Layout(name="status", size=6),  # Agent Activity at bottom
        )
        
        # Header - show task
        if task:
            task_text = Text(f"📋 Task: {task}")  # No truncation
            layout["header"].update(Panel(task_text, border_style="cyan"))
        
        # Main discussion panel - includes both contributions AND summary as part of chat
        discussion_content = self._render_discussion_with_summary(contributions, summary, is_complete)
        layout["discussion"].update(
            Panel(
                discussion_content,
                title="[bold bright_white]💬 Live Discussion[/bold bright_white]",
                border_style="bright_white" if not is_complete else "green",
            )
        )
        
        # Agent Activity at bottom
        agent_content = self._render_agent_status(agent_status, is_complete)
        layout["status"].update(
            Panel(
                agent_content,
                title="[bold blue]� Agent Activity[/bold blue]",
                border_style="blue",
            )
        )
        
        return layout

    def _render_discussion_with_summary(self, contributions: list[dict], summary: str, is_complete: bool) -> Group:
        """Render the discussion as a chatroom with summary integrated.
        
        The summary appears as a special message in the chat flow, making it feel
        like a natural part of the conversation rather than a separate panel.

        Args:
            contributions: List of contributions.
            summary: Current rolling summary or final summary.
            is_complete: Whether discussion is complete.

        Returns:
            Rich Group with contributions and summary.
        """
        messages = []
        
        # Render contributions
        if contributions:
            # Show last 15 contributions with scroll indicator
            max_visible = 15
            visible_contributions = contributions[-max_visible:]
            
            # Show indicator if there are earlier messages
            if len(contributions) > max_visible:
                hidden_count = len(contributions) - max_visible
                messages.append(Text(f"⬆️  {hidden_count} earlier messages", style="dim italic cyan"))
                messages.append(Text(""))
            
            # Render each contribution
            for i, contrib in enumerate(visible_contributions):
                agent_name = contrib.get("agent", "Unknown")
                content = contrib.get("content", "")
                
                # Get agent styling
                color = self.AGENT_COLORS.get(agent_name, "white")
                emoji = self.AGENT_EMOJIS.get(agent_name, "🤖")
                
                # Highlight the newest message
                is_newest = (i == len(visible_contributions) - 1) and not is_complete
                
                if is_newest:
                    agent_line = Text(f"✨ {emoji} {agent_name}", style=f"bold {color} on #1a1a1a")
                else:
                    agent_line = Text(f"{emoji} {agent_name}", style=f"bold {color}")
                
                message_line = Text(content, style=color if not is_newest else f"{color} on #1a1a1a")
                
                messages.append(agent_line)
                messages.append(message_line)
                messages.append(Text(""))
        else:
            if is_complete:
                messages.append(Text("No contributions made.", style="dim italic"))
            else:
                messages.append(Text("💬 Waiting for agents to contribute...", style="dim italic cyan"))
        
        # Add summary as a special message in the chat
        if summary:
            messages.append(Text(""))
            messages.append(Text("─" * 80, style="dim"))
            messages.append(Text("📝 Summary" if not is_complete else "📝 Final Summary", style="bold yellow"))
            messages.append(Text(summary, style="yellow"))
            if not is_complete:
                messages.append(Text("(updating...)", style="dim italic yellow"))
        
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
