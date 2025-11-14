#!/usr/bin/env python3
"""Test the scrolling behavior with realistic content."""

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.console import Group
import time

# Agent colors and emojis (from live_discussion.py)
AGENT_COLORS = {
    "Critical": "bright_red",
    "Divergent": "bright_magenta",
    "Creative": "bright_cyan",
    "Analytical": "bright_blue",
}

AGENT_EMOJIS = {
    "Critical": "🔍",
    "Divergent": "🌟",
    "Creative": "💡",
    "Analytical": "📊",
}

def render_discussion(contributions: list[dict], max_lines: int = 37) -> Group:
    """Render discussion with line counting."""
    messages = []
    line_count = 0
    
    # Work backwards from newest to oldest
    visible_contributions = []
    for contrib in reversed(contributions):
        content = contrib.get("content", "")
        
        # Rough estimate: 80 chars per terminal line
        estimated_content_lines = max(1, len(content) // 80 + (1 if len(content) % 80 else 0))
        
        # Truncate very long messages to 5 lines max
        if estimated_content_lines > 5:
            estimated_content_lines = 5
            contrib = contrib.copy()
            contrib["content"] = content[:400] + "..." if len(content) > 400 else content
        
        contribution_lines = 1 + estimated_content_lines + 1  # name + content + blank
        
        if line_count + contribution_lines > max_lines - 2:
            break
        
        visible_contributions.insert(0, contrib)
        line_count += contribution_lines
    
    # Show indicator
    if len(visible_contributions) < len(contributions):
        hidden_count = len(contributions) - len(visible_contributions)
        messages.append(Text(f"⬆️  {hidden_count} earlier messages", style="dim italic cyan"))
        messages.append(Text(""))
    
    # Render each contribution
    for i, contrib in enumerate(visible_contributions):
        agent_name = contrib.get("agent", "Unknown")
        content = contrib.get("content", "")
        
        color = AGENT_COLORS.get(agent_name, "white")
        emoji = AGENT_EMOJIS.get(agent_name, "🤖")
        
        is_newest = (i == len(visible_contributions) - 1)
        
        if is_newest:
            agent_line = Text(f"✨ {emoji} {agent_name}", style=f"bold {color} on #1a1a1a")
        else:
            agent_line = Text(f"{emoji} {agent_name}", style=f"bold {color}")
        
        message_line = Text(content, style=color if not is_newest else f"{color} on #1a1a1a")
        
        messages.append(agent_line)
        messages.append(message_line)
        messages.append(Text(""))
    
    return Group(*messages)

# Create realistic contributions
contributions = [
    {"agent": "Critical", "content": f"Message {i}: This is a short message."} 
    for i in range(1, 11)
]

console = Console()
console.print("[bold cyan]Testing Scrolling Simulation[/bold cyan]\n")

# Test static rendering
with Live(console=console, refresh_per_second=4) as live:
    for count in range(1, 21):
        # Add new contribution
        agent = ["Critical", "Divergent", "Creative", "Analytical"][count % 4]
        contributions.append({
            "agent": agent,
            "content": f"Message {10 + count}: This is contribution number {10 + count} from {agent}."
        })
        
        # Render
        layout = Layout()
        layout.split_column(
            Layout(name="discussion"),
            Layout(name="status", size=3)
        )
        
        discussion_group = render_discussion(contributions)
        layout["discussion"].update(
            Panel(
                discussion_group,
                title=f"[bold cyan]Live Discussion[/bold cyan] ({len(contributions)} messages)",
                border_style="cyan",
                height=40
            )
        )
        
        layout["status"].update(
            Panel(
                Text(f"Adding message {10 + count}/30...", style="green"),
                border_style="green"
            )
        )
        
        live.update(layout)
        time.sleep(0.5)

console.print("\n[bold green]✓ Scrolling simulation complete![/bold green]")
console.print(f"Total messages: {len(contributions)}")
