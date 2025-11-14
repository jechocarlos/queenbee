#!/usr/bin/env python3
"""Test the new integrated layout with summary in chat."""

from rich.console import Console, Group
from rich.text import Text
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
import time

# Agent colors and emojis
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

def render_chat_with_summary(contributions: list[dict], summary: str) -> Group:
    """Render chat with integrated summary."""
    messages = []
    
    # Show contributions
    if contributions:
        max_visible = 15
        visible = contributions[-max_visible:]
        
        if len(contributions) > max_visible:
            messages.append(Text(f"⬆️  {len(contributions) - max_visible} earlier messages", style="dim italic cyan"))
            messages.append(Text(""))
        
        for i, contrib in enumerate(visible):
            agent = contrib["agent"]
            content = contrib["content"]
            color = AGENT_COLORS[agent]
            emoji = AGENT_EMOJIS[agent]
            
            is_newest = i == len(visible) - 1
            
            if is_newest:
                messages.append(Text(f"✨ {emoji} {agent}", style=f"bold {color} on #1a1a1a"))
            else:
                messages.append(Text(f"{emoji} {agent}", style=f"bold {color}"))
            
            messages.append(Text(content, style=color if not is_newest else f"{color} on #1a1a1a"))
            messages.append(Text(""))
    else:
        messages.append(Text("💬 Waiting for agents to contribute...", style="dim italic cyan"))
    
    # Add summary
    if summary:
        messages.append(Text(""))
        messages.append(Text("─" * 80, style="dim"))
        messages.append(Text("📝 Summary", style="bold yellow"))
        messages.append(Text(summary, style="yellow"))
        messages.append(Text("(updating...)", style="dim italic yellow"))
    
    return Group(*messages)

# Create test data
contributions = []
summary = ""

console = Console()
console.print("[bold cyan]Testing New Integrated Layout[/bold cyan]\n")

with Live(console=console, refresh_per_second=4) as live:
    for i in range(1, 11):
        # Add contribution
        agent = ["Critical", "Divergent", "Creative", "Analytical"][i % 4]
        contributions.append({
            "agent": agent,
            "content": f"Contribution {i}: Analysis from {agent} perspective."
        })
        
        # Update summary every 3 messages
        if i % 3 == 0:
            summary = f"So far we have {i} contributions discussing the topic from multiple angles. Key insights are emerging from the diverse perspectives."
        
        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="discussion"),
            Layout(name="status", size=6),
        )
        
        layout["header"].update(Panel(
            Text("📋 Task: What is the meaning of life?"),
            border_style="cyan"
        ))
        
        chat_content = render_chat_with_summary(contributions, summary)
        layout["discussion"].update(Panel(
            chat_content,
            title="[bold bright_white]💬 Live Discussion[/bold bright_white]",
            border_style="bright_white"
        ))
        
        layout["status"].update(Panel(
            Text(f"🔍 Critical: thinking\n🌟 Divergent: idle\n💡 Creative: contributing\n📊 Analytical: idle", style="cyan"),
            title="[bold cyan]🤖 Agent Activity[/bold cyan]",
            border_style="cyan"
        ))
        
        live.update(layout)
        time.sleep(0.7)

console.print("\n[bold green]✓ New layout test complete![/bold green]")
console.print(f"Total contributions: {len(contributions)}")
console.print("Summary is now integrated into the chat flow! 🎉")
