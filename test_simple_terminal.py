#!/usr/bin/env python3
"""Test simple terminal printing approach."""

from rich.console import Console
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

def print_contribution(console, agent, content, is_new=False):
    """Print a contribution."""
    color = AGENT_COLORS[agent]
    emoji = AGENT_EMOJIS[agent]
    
    prefix = "✨ " if is_new else ""
    console.print(f"{prefix}{emoji} {agent}", style=f"bold {color}")
    console.print(content, style=color)
    console.print()

console = Console()

# Print header
console.print("\n" + "=" * 80, style="cyan")
console.print("💬 LIVE DISCUSSION", style="bold bright_white", justify="center")
console.print("=" * 80, style="cyan")
console.print()

# Simulate messages arriving
agents = ["Critical", "Divergent", "Creative", "Analytical"]
for i in range(1, 11):
    agent = agents[i % 4]
    content = f"This is contribution number {i}. Here's my analysis from the {agent.lower()} perspective."
    
    print_contribution(console, agent, content, is_new=True)
    time.sleep(0.3)
    
    # Print summary every 3 messages
    if i % 3 == 0:
        console.print("─" * 80, style="dim yellow")
        console.print("📝 Summary (updating...)", style="yellow")
        console.print(f"We've received {i} contributions so far. The discussion is progressing well with insights from multiple perspectives.", style="yellow")
        console.print("─" * 80, style="dim yellow")
        console.print()

# Final summary
console.print("─" * 80, style="yellow")
console.print("📝 FINAL SUMMARY", style="bold yellow")
console.print("The discussion concluded with 10 contributions from all four specialist agents, providing comprehensive analysis.", style="yellow")
console.print("─" * 80, style="yellow")
console.print()
console.print("✓ Discussion complete!", style="bold green")
