#!/usr/bin/env python3
"""Test no truncation and status change detection."""

from rich.console import Console
import time

AGENT_COLORS = {
    "Critical": "bright_red",
    "Divergent": "bright_magenta",
}

AGENT_EMOJIS = {
    "Critical": "🔍",
    "Divergent": "🌟",
}

console = Console()

console.print("\n" + "=" * 80, style="cyan")
console.print("💬 LIVE DISCUSSION", style="bold bright_white", justify="center")
console.print("=" * 80, style="cyan")
console.print()

# Test 1: Long message (no truncation)
print("TEST 1: Long message should NOT be truncated")
long_message = "This is a very long message that would normally be truncated at 80 characters or 100 characters or whatever limit was set before. But now it should print in full without any truncation at all. " * 3

console.print("✨ 🔍 Critical", style="bold bright_red")
console.print(long_message, style="bright_red", overflow="ignore", no_wrap=False)
console.print()

# Test 2: Agent status only prints when changed
print("\nTEST 2: Agent status should only print when it changes")

last_status = {}
statuses = [
    {"Critical": "thinking", "Divergent": "idle"},
    {"Critical": "thinking", "Divergent": "idle"},  # Same - should NOT print
    {"Critical": "contributing", "Divergent": "thinking"},  # Changed - should print
    {"Critical": "contributing", "Divergent": "thinking"},  # Same - should NOT print
    {"Critical": "idle", "Divergent": "idle"},  # Changed - should print
]

for i, status in enumerate(statuses):
    if status != last_status:
        parts = [f"{AGENT_EMOJIS[agent]} {agent}: {stat}" for agent, stat in status.items()]
        console.print(f"  [{', '.join(parts)}]", style="dim cyan")
        last_status = status.copy()
        print(f"  → Status {i+1} printed (changed)")
    else:
        print(f"  → Status {i+1} skipped (same as before)")
    time.sleep(0.3)

console.print("\n✓ Tests complete!", style="bold green")
