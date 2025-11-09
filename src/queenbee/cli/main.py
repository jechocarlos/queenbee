"""Main CLI interface."""

import logging
import signal
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.prompt import Prompt

from queenbee import __version__
from queenbee.agents.queen import QueenAgent
from queenbee.config.loader import load_config
from queenbee.db.connection import DatabaseManager
from queenbee.session.manager import SessionManager

console = Console()


def setup_logging(level: str = "INFO") -> None:
    """Set up logging with Rich handler.

    Args:
        level: Logging level.
    """
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def print_banner() -> None:
    """Print welcome banner."""
    banner = f"""
    [bold yellow]🐝 QueenBee v{__version__}[/bold yellow]
    [dim]Meta-Agent Orchestration System[/dim]
    
    Type your questions or commands. Press Ctrl+C to exit.
    """
    console.print(Panel(banner, border_style="yellow"))


def handle_shutdown(signum, frame) -> None:
    """Handle shutdown signals gracefully."""
    console.print("\n[yellow]Shutting down QueenBee...[/yellow]")
    sys.exit(0)


def main() -> int:
    """Main entry point for QueenBee CLI."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        # Load configuration
        config_path = "config.yaml"
        if not Path(config_path).exists():
            console.print(f"[red]Error: Configuration file not found: {config_path}[/red]")
            console.print("[yellow]Please create config.yaml or run from project root.[/yellow]")
            return 1

        config = load_config(config_path)
        setup_logging(config.logging.level)

        logger = logging.getLogger(__name__)
        logger.info("Starting QueenBee")

        # Check Ollama availability
        from queenbee.llm import OllamaClient
        ollama = OllamaClient(config.ollama)
        if not ollama.is_available():
            console.print(
                "[red]Error: Ollama server is not available[/red]\n"
                f"[yellow]Please ensure Ollama is running at {config.ollama.host}[/yellow]\n"
                "[dim]Run: docker-compose -f docker-compose.local.yml up -d[/dim]"
            )
            return 1

        logger.info(f"Connected to Ollama at {config.ollama.host}")

        # Set up database
        db = DatabaseManager(config.database)
        
        try:
            db.connect()
            logger.info("Connected to database")
        except Exception as e:
            console.print(f"[red]Error: Failed to connect to database: {e}[/red]")
            console.print(
                "[yellow]Please ensure PostgreSQL is running and migrations are applied.[/yellow]\n"
                "[dim]Run: python scripts/migrate.py[/dim]"
            )
            return 1

        # Start session
        with SessionManager(db) as session_mgr:
            session_id = session_mgr.current_session_id
            if session_id is None:
                console.print("[red]✗ Failed to create session[/red]")
                return 1
            
            # Initialize Queen agent
            queen = QueenAgent(
                session_id=session_id,
                config=config,
                db=db,
            )

            # Print banner
            print_banner()
            console.print(f"[green]✓ Session started: {session_id}[/green]")
            console.print(f"[green]✓ Queen agent ready[/green]\n")

            # Main interaction loop
            while True:
                try:
                    # Get user input
                    user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

                    if not user_input.strip():
                        continue

                    # Check for exit commands
                    if user_input.lower() in ["exit", "quit", "bye"]:
                        console.print("[yellow]Goodbye! 👋[/yellow]")
                        break

                    # Process request
                    console.print("[dim]Queen is thinking...[/dim]")
                    response = queen.process_request(user_input)

                    # Display response
                    console.print(f"\n[bold yellow]🐝 Queen[/bold yellow]: {response}\n")

                except KeyboardInterrupt:
                    console.print("\n[yellow]Use 'exit' or 'quit' to close gracefully.[/yellow]")
                    continue
                except Exception as e:
                    logger.error(f"Error processing request: {e}", exc_info=True)
                    console.print(f"[red]Error: {e}[/red]")
                    continue

        # Cleanup
        db.disconnect()
        logger.info("QueenBee shut down successfully")
        return 0

    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        logging.error("Fatal error", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
