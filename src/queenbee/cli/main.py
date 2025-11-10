"""Main CLI interface."""

import logging
import signal
import sys
from pathlib import Path
from typing import Iterator

from rich.console import Console
from rich.live import Live
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from queenbee import __version__
from queenbee.agents.queen import QueenAgent
from queenbee.config.loader import load_config
from queenbee.db.connection import DatabaseManager
from queenbee.db.models import ChatRepository, MessageRole
from queenbee.session.manager import SessionManager
from queenbee.workers import WorkerManager

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


def display_chat_history(chat_repo: ChatRepository, session_id, limit: int = 10) -> None:
    """Display recent chat history.

    Args:
        chat_repo: Chat repository.
        session_id: Session ID.
        limit: Number of recent messages to show.
    """
    messages = chat_repo.get_session_history(session_id, limit=limit)
    
    if not messages:
        return
    
    console.print("\n[bold cyan]📜 Recent Chat History:[/bold cyan]")
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Role", style="cyan", width=12)
    table.add_column("Message", style="white")
    
    for msg in messages[-limit:]:
        role = msg["role"].upper()
        content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        
        # Color code by role
        if role == "USER":
            role_display = f"[bold cyan]{role}[/bold cyan]"
        elif role == "QUEEN":
            role_display = f"[bold yellow]🐝 {role}[/bold yellow]"
        else:
            role_display = f"[bold green]{role}[/bold green]"
        
        table.add_row(role_display, content)
    
    console.print(table)
    console.print()


def stream_response(response_iter: Iterator[str]) -> str:
    """Stream response chunks and display them in real-time.

    Args:
        response_iter: Iterator of response chunks.

    Returns:
        Complete response text.
    """
    console.print("\n[bold yellow]🐝 Queen[/bold yellow]: ", end="")
    
    full_response = []
    for chunk in response_iter:
        console.print(chunk, end="")
        full_response.append(chunk)
    
    console.print("\n")
    return "".join(full_response)


def main() -> int:
    """Main entry point for QueenBee CLI."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        # Load configuration
        config_path = "config.yaml"
        config_path_resolved = Path(config_path).resolve()
        
        console.print(f"[dim]Loading config from: {config_path_resolved}[/dim]")
        
        if not Path(config_path).exists():
            console.print(f"[red]Error: Configuration file not found: {config_path}[/red]")
            console.print("[yellow]Please create config.yaml or run from project root.[/yellow]")
            return 1

        config = load_config(config_path)
        
        # Show key config values for debugging
        console.print(f"[dim]✓ Ollama model: {config.ollama.model}[/dim]")
        console.print(f"[dim]✓ Ollama host: {config.ollama.host}[/dim]")
        console.print(f"[dim]✓ Database: {config.database.host}:{config.database.port}/{config.database.name}[/dim]")
        console.print(f"[dim]✓ Log level: {config.logging.level}[/dim]")
        
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
            
            # Initialize worker manager and start worker for this session
            worker_mgr = WorkerManager(config)
            worker_mgr.start_worker(session_id)
            console.print("[green]✓ Specialist worker process started[/green]")
            
            # Initialize Queen agent and chat repository
            queen = QueenAgent(
                session_id=session_id,
                config=config,
                db=db,
            )
            chat_repo = ChatRepository(db)

            # Print banner
            print_banner()
            console.print(f"[green]✓ Session started: {session_id}[/green]")
            console.print(f"[green]✓ Queen agent ready[/green]")
            console.print(f"[dim]💡 Tip: Type 'history' to see recent messages, 'specialists on/off' to toggle[/dim]\n")

            # Main interaction loop
            try:
                while True:
                    try:
                        # Get user input
                        user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

                        if not user_input.strip():
                            continue

                        # Check for special commands
                        if user_input.lower() in ["exit", "quit", "bye"]:
                            console.print("[yellow]Goodbye! 👋[/yellow]")
                            break
                        
                        if user_input.lower() in ["history", "hist", "h"]:
                            display_chat_history(chat_repo, session_id, limit=20)
                            continue
                        
                        # Toggle specialists
                        if user_input.lower() in ["specialists on", "enable specialists"]:
                            queen.enable_specialists = True
                            console.print("[green]✓ Specialist spawning enabled[/green]\n")
                            continue
                        
                        if user_input.lower() in ["specialists off", "disable specialists"]:
                            queen.enable_specialists = False
                            console.print("[yellow]⚠ Specialist spawning disabled[/yellow]\n")
                            continue

                        # Process request with streaming
                        console.print("[dim]Queen is thinking...[/dim]")
                        response = queen.process_request(user_input, stream=True)

                        # Handle streaming response
                        if isinstance(response, str):
                            # Non-streaming response
                            console.print(f"\n[bold yellow]🐝 Queen[/bold yellow]: {response}\n")
                        else:
                            # Streaming response
                            full_response = stream_response(response)
                            
                            # Log the complete response to chat history
                            chat_repo.add_message(
                                session_id=session_id,
                                agent_id=queen.agent_id,
                                role=MessageRole.QUEEN,
                                content=full_response,
                            )

                        # Show updated chat history indicator
                        message_count = len(chat_repo.get_session_history(session_id))
                        console.print(f"[dim]💬 Total messages in session: {message_count} (type 'history' to view)[/dim]\n")

                    except KeyboardInterrupt:
                        console.print("\n[yellow]Use 'exit' or 'quit' to close gracefully.[/yellow]")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing request: {e}", exc_info=True)
                        console.print(f"[red]Error: {e}[/red]")
                        continue
            finally:
                # Stop worker on exit
                console.print("[dim]Stopping specialist workers...[/dim]")
                worker_mgr.stop_worker(session_id)

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
