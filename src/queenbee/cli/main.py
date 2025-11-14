"""Main CLI interface."""

import logging
import os
import signal
import sys
from pathlib import Path
from typing import Iterator

from rich.console import Console
from rich.live import Live
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
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


def verify_ollama_models(config, provider_config) -> dict[str, bool]:
    """Verify that all configured Ollama models are available.
    
    Args:
        config: System configuration.
        provider_config: Provider-specific inference pack configuration.
        
    Returns:
        Dictionary mapping model names to availability status.
    """
    from queenbee.llm import OllamaClient
    
    ollama = OllamaClient(config.ollama)
    
    try:
        available_models = ollama.list_models()
        logger = logging.getLogger(__name__)
        logger.debug(f"Available Ollama models: {available_models}")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not list Ollama models: {e}")
        # Return empty dict - we'll assume models might be available
        return {}
    
    # Check each pack's model
    model_status = {}
    for pack_name, pack in provider_config.packs.items():
        model_name = pack.model
        # Ollama models can have tags (e.g., llama3.1:8b)
        # Check if model name matches any available model
        is_available = any(model_name in m or m in model_name for m in available_models)
        model_status[model_name] = is_available
    
    return model_status


def verify_openrouter_models(config, provider_config) -> dict[str, bool]:
    """Verify OpenRouter API key is configured.
    
    Args:
        config: System configuration.
        provider_config: Provider-specific inference pack configuration.
        
    Returns:
        Dictionary mapping model names to availability status (all True if API key exists).
    """
    model_status = {}
    api_key_valid = bool(config.openrouter.api_key and config.openrouter.api_key != "")
    
    for pack_name, pack in provider_config.packs.items():
        model_status[pack.model] = api_key_valid
    
    return model_status


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
    # Clear the terminal for a clean start
    console.clear()
    
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
        
        # Check if using OpenRouter
        using_openrouter = os.environ.get('QUEENBEE_USE_OPENROUTER') == '1'
        
        # Show key config values
        console.print(f"[dim]✓ Database: {config.database.host}:{config.database.port}/{config.database.name}[/dim]")
        console.print(f"[dim]✓ Log level: {config.logging.level}[/dim]")
        
        # Show inference pack configuration
        openrouter_packs = len(config.inference_packs.openrouter.packs) if config.inference_packs.openrouter else 0
        ollama_packs = len(config.inference_packs.ollama.packs) if config.inference_packs.ollama else 0
        total_packs = openrouter_packs + ollama_packs
        
        # Determine active provider
        active_provider = 'openrouter' if using_openrouter else 'ollama'
        provider_config = config.inference_packs.openrouter if using_openrouter else config.inference_packs.ollama
        
        # Verify model availability
        console.print(f"[dim]Verifying model availability...[/dim]")
        if active_provider == 'ollama':
            model_status = verify_ollama_models(config, provider_config)
        else:
            model_status = verify_openrouter_models(config, provider_config)
        
        if total_packs > 0:
            console.print(f"[dim]✓ Provider: {active_provider.capitalize()} ({len(provider_config.packs)} packs available)[/dim]")
            
            # Track if any models are unavailable
            unavailable_agents = []
            
            # Show all agent assignments with availability status
            for agent_type in ['queen', 'divergent', 'convergent', 'critical', 'summarizer', 'web_searcher']:
                pack_name = getattr(config.agent_inference, agent_type, 'standard')
                
                # Get the pack from the active provider
                pack = provider_config.packs.get(pack_name)
                
                if not pack:
                    # Try default pack
                    pack_name = provider_config.default_pack
                    pack = provider_config.packs.get(pack_name)
                
                if pack:
                    model_short = pack.model.split('/')[-1] if '/' in pack.model else pack.model
                    model_available = model_status.get(pack.model, False)
                    
                    if model_available:
                        console.print(f"[dim]  {agent_type:12} → {model_short} [green]✓[/green][/dim]")
                    else:
                        console.print(f"[dim]  {agent_type:12} → {model_short} [red]✗ NOT FOUND[/red][/dim]")
                        unavailable_agents.append((agent_type, pack.model))
                else:
                    console.print(f"[dim]  {agent_type:12} → [red]UNAVAILABLE (no pack)[/red][/dim]")
                    unavailable_agents.append((agent_type, "no pack configured"))
            
            # If any models are unavailable, show warning and instructions
            if unavailable_agents:
                # Check if any critical agents are unavailable
                critical_agents = {'queen', 'divergent', 'convergent', 'critical', 'summarizer'}
                critical_unavailable = [
                    (agent_type, model) 
                    for agent_type, model in unavailable_agents 
                    if agent_type in critical_agents
                ]
                
                console.print()
                console.print("[yellow]⚠ Warning: Some models are not available:[/yellow]")
                for agent_type, model in unavailable_agents:
                    console.print(f"[yellow]  • {agent_type}: {model}[/yellow]")
                
                if active_provider == 'ollama':
                    console.print("\n[dim]To pull missing models:[/dim]")
                    unique_models = set(model for _, model in unavailable_agents if model != "no pack configured")
                    for model in unique_models:
                        console.print(f"[dim]  docker exec -it queenbee-ollama ollama pull {model}[/dim]")
                    console.print()
                else:
                    console.print("\n[dim]Check your OpenRouter API key in .env file[/dim]\n")
                
                # Exit if critical agents are unavailable
                if critical_unavailable:
                    console.print("[red]✗ Error: Critical agents cannot start without their models.[/red]")
                    console.print("[red]  Required agents: queen, divergent, convergent, critical, summarizer[/red]")
                    console.print("[yellow]  Please install the missing models and try again.[/yellow]")
                    return 1
        elif using_openrouter:
            console.print(f"[dim]✓ Provider: OpenRouter[/dim]")
            console.print(f"[dim]✓ Default model: {config.openrouter.model}[/dim]")
        else:
            console.print(f"[dim]✓ Provider: Ollama[/dim]")
            console.print(f"[dim]✓ Default model: {config.ollama.model}[/dim]")
        
        console.print()  # Add spacing
        
        # Show progress during initialization
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Initializing system...", total=None)
            
            setup_logging(config.logging.level)

            logger = logging.getLogger(__name__)
            logger.info("Starting QueenBee")

            # Check LLM availability based on provider
            progress.update(task, description="[cyan]Connecting to LLM provider...")
            if using_openrouter:
                from queenbee.llm.openrouter import OpenRouterClient

                # Initialize database and OpenRouter client
                db = DatabaseManager(config.database)
                
                # Test OpenRouter client initialization
                try:
                    llm_client = OpenRouterClient(config.openrouter, db)
                    logger.info(f"Connected to OpenRouter at {config.openrouter.base_url}")
                except ValueError as e:
                    progress.stop()
                    console.print(
                        f"[red]Error: {e}[/red]\n"
                        "[yellow]Please set OPENROUTER_API_KEY in your .env file[/yellow]"
                    )
                    return 1
            else:
                # Check Ollama availability
                from queenbee.llm import OllamaClient
                ollama = OllamaClient(config.ollama)
                if not ollama.is_available():
                    progress.stop()
                    console.print(
                        "[red]Error: Ollama server is not available[/red]\n"
                        f"[yellow]Please ensure Ollama is running at {config.ollama.host}[/yellow]\n"
                        "[dim]Run: docker-compose -f docker-compose.local.yml up -d[/dim]"
                    )
                    return 1

                logger.info(f"Connected to Ollama at {config.ollama.host}")
                db = DatabaseManager(config.database)
            
            progress.update(task, description="[cyan]Connecting to database...")
            try:
                db.connect()
                logger.info("Connected to database")
            except Exception as e:
                progress.stop()
                console.print(f"[red]Error: Failed to connect to database: {e}[/red]")
                console.print(
                    "[yellow]Please ensure PostgreSQL is running and migrations are applied.[/yellow]\n"
                    "[dim]Run: python scripts/migrate.py[/dim]"
                )
                return 1

            # Start session
            progress.update(task, description="[cyan]Starting session...")
            session_mgr = SessionManager(db)
            session_mgr.__enter__()
            session_id = session_mgr.current_session_id
            if session_id is None:
                progress.stop()
                console.print("[red]✗ Failed to create session[/red]")
                return 1
            
            # Initialize worker manager and start worker for this session
            progress.update(task, description="[cyan]Starting specialist workers...")
            worker_mgr = WorkerManager(config)
            worker_mgr.start_worker(session_id)
            
            # Initialize Queen agent and chat repository
            progress.update(task, description="[cyan]Initializing Queen agent...")
            queen = QueenAgent(
                session_id=session_id,
                config=config,
                db=db,
            )
            chat_repo = ChatRepository(db)
        
        # Progress complete - show ready state
        console.print()  # Add spacing

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
            # Close session manager
            session_mgr.__exit__(None, None, None)

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
