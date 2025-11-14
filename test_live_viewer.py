#!/usr/bin/env python3
"""Test live discussion viewer rendering."""

from rich.console import Console, Group
from rich.text import Text

# Simulate what the viewer does
contributions = [
    {"agent": "Divergent", "content": "This is a test message from Divergent agent"},
    {"agent": "Convergent", "content": "This is a test message from Convergent agent"},
    {"agent": "Critical", "content": "This is a test message from Critical agent"},
]

console = Console()

def render_discussion(contributions):
    """Test render."""
    max_visible = 10
    visible_contributions = contributions[-max_visible:]
    
    messages = []
    
    if len(contributions) > max_visible:
        hidden_count = len(contributions) - max_visible
        messages.append(Text(f"⬆️  {hidden_count} earlier messages", style="dim italic cyan"))
        messages.append(Text(""))
    
    for i, contrib in enumerate(visible_contributions):
        agent_name = contrib.get("agent", "Unknown")
        content = contrib.get("content", "")
        
        emoji_map = {
            "Divergent": "🌟",
            "Convergent": "🔗",
            "Critical": "🔍",
        }
        color_map = {
            "Divergent": "bright_magenta",
            "Convergent": "bright_cyan",
            "Critical": "bright_yellow",
        }
        
        color = color_map.get(agent_name, "white")
        emoji = emoji_map.get(agent_name, "🤖")
        
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

# Test with initial contributions
console.print("=" * 80)
console.print("Initial state (3 contributions):")
console.print("=" * 80)
result = render_discussion(contributions)
console.print(result)

# Add more contributions
for i in range(4, 15):
    contributions.append({
        "agent": ["Divergent", "Convergent", "Critical"][i % 3],
        "content": f"Message number {i} - testing scrolling behavior"
    })

console.print("\n" + "=" * 80)
console.print(f"After adding more (total {len(contributions)} contributions):")
console.print("=" * 80)
result = render_discussion(contributions)
console.print(result)

console.print(f"\n[bold green]✓ Showing last 10 of {len(contributions)} contributions[/bold green]")
