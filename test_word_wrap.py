#!/usr/bin/env python3
"""Test word wrapping."""

from rich.console import Console

console = Console(soft_wrap=True)

long_text = "This is a very long message that would normally be truncated at 80 characters or 100 characters or whatever limit was set before. But now it should print in full without any truncation at all and wrap properly at word boundaries so that the text remains readable and doesn't get cut off in the middle of words. This should demonstrate proper word wrapping behavior in the terminal."

print("TEST: Long message with word wrapping enabled")
print("=" * 80)

console.print("✨ 🔍 Critical", style="bold bright_red")
console.print(long_text, style="bright_red", soft_wrap=True)
console.print()

console.print("📝 Summary (updating...)", style="yellow")
console.print(long_text + " " + long_text, style="yellow", soft_wrap=True)
console.print()

console.print("✓ Word wrapping test complete!", style="bold green")
