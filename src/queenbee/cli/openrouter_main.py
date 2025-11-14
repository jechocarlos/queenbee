"""OpenRouter CLI interface."""

import os
import sys

# Set environment variable to use OpenRouter
os.environ['QUEENBEE_USE_OPENROUTER'] = '1'

# Import and run the main CLI
from queenbee.cli.main import main


def main_openrouter() -> int:
    """Entry point for QueenBee CLI with OpenRouter."""
    return main()


if __name__ == "__main__":
    sys.exit(main_openrouter())
