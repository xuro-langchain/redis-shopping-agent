#!/usr/bin/env python3
"""
Music Store Agent CLI

A beautiful command-line interface for interacting with the multi-agent
music store customer support system.
"""

# Load environment variables first, before any other imports
from dotenv import load_dotenv
load_dotenv()

# Suppress verbose logging for cleaner CLI experience
import logging
logging.getLogger("langgraph").setLevel(logging.WARNING)
logging.getLogger("redisvl").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

import sys
from uuid import uuid4
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.live import Live
from rich.text import Text
from rich.theme import Theme

from langchain.messages import HumanMessage, AIMessage
from langgraph.types import Command

from agents.agent import graph
from agents.checkpoint import get_checkpointer

# Custom theme for the CLI
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "user": "bold blue",
    "agent": "bold magenta",
    "muted": "dim white",
})

console = Console(theme=custom_theme)

app = typer.Typer(
    name="music-store",
    help="🎵 Music Store Agent - AI-powered customer support",
    add_completion=False,
)


def get_last_ai_message(messages: list) -> Optional[str]:
    """Extract the last AI message content from the message list."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
    return None


def is_graph_interrupted(thread_id: str) -> bool:
    """Check if the graph is currently interrupted and waiting for human input."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        # Check if there are pending tasks (interrupts)
        if state and state.next:
            return "human_input" in state.next
    except Exception:
        pass
    return False


def display_welcome(thread_id: str, is_new: bool) -> None:
    """Display the welcome banner."""
    status = "[success]new[/success]" if is_new else "[info]resumed[/info]"
    
    welcome_text = Text()
    welcome_text.append("🎵 ", style="bold")
    welcome_text.append("Music Store Agent\n", style="bold magenta")
    welcome_text.append(f"Thread: ", style="muted")
    welcome_text.append(f"{thread_id}\n", style="cyan")
    welcome_text.append(f"Status: ", style="muted")
    welcome_text.append_text(Text.from_markup(status))
    welcome_text.append("\n\n", style="muted")
    welcome_text.append("Commands: ", style="muted")
    welcome_text.append("exit", style="bold yellow")
    welcome_text.append(" or ", style="muted")
    welcome_text.append("quit", style="bold yellow")
    welcome_text.append(" to leave, ", style="muted")
    welcome_text.append("clear", style="bold yellow")
    welcome_text.append(" to reset", style="muted")
    
    console.print(Panel(
        welcome_text,
        border_style="magenta",
        padding=(1, 2),
    ))
    console.print()


def display_agent_response(content: str) -> None:
    """Display the agent's response in a styled panel."""
    console.print()
    console.print(Text("Agent", style="agent"))
    console.print(Panel(
        Markdown(content),
        border_style="magenta",
        padding=(0, 1),
    ))


def display_error(message: str) -> None:
    """Display an error message."""
    console.print(f"[error]Error:[/error] {message}")


def invoke_graph(thread_id: str, user_input: str) -> Optional[str]:
    """
    Invoke the graph with user input, handling both normal messages
    and resume commands appropriately.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    # Check if we're resuming from an interrupt
    is_interrupted = is_graph_interrupted(thread_id)
    
    with Live(
        Spinner("dots", text="Thinking...", style="magenta"),
        console=console,
        transient=True,
    ):
        try:
            if is_interrupted:
                # Resume with the user's input
                result = graph.invoke(
                    Command(resume=user_input),
                    config=config
                )
            else:
                # Send as a new human message
                result = graph.invoke(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=config
                )
            
            return get_last_ai_message(result.get("messages", []))
            
        except Exception as e:
            display_error(str(e))
            return None


def check_thread_exists(thread_id: str) -> bool:
    """Check if a thread already has state."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        return state is not None and state.values.get("messages")
    except Exception:
        return False


def run_repl(thread_id: str, is_new: bool) -> None:
    """Run the main REPL loop."""
    display_welcome(thread_id, is_new)
    
    # If resuming an existing thread, show context
    if not is_new:
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = graph.get_state(config)
            if state and state.values.get("messages"):
                last_msg = get_last_ai_message(state.values["messages"])
                if last_msg:
                    console.print("[muted]Last message from this thread:[/muted]")
                    display_agent_response(last_msg)
                    console.print()
        except Exception:
            pass
    
    while True:
        try:
            # Show prompt
            console.print()
            user_input = console.input("[user]You:[/user] ").strip()
            
            # Handle special commands
            if not user_input:
                continue
            
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("\n[muted]Goodbye! Your conversation is saved.[/muted]")
                console.print(f"[muted]Resume with:[/muted] uv run music-store --thread {thread_id}\n")
                break
            
            if user_input.lower() == "clear":
                console.clear()
                display_welcome(thread_id, is_new)
                continue
            
            if user_input.lower() == "thread":
                console.print(f"[muted]Thread ID:[/muted] {thread_id}")
                continue
            
            # Invoke the graph
            response = invoke_graph(thread_id, user_input)
            
            if response:
                display_agent_response(response)
                
        except KeyboardInterrupt:
            console.print("\n\n[muted]Interrupted. Goodbye![/muted]")
            console.print(f"[muted]Resume with:[/muted] uv run music-store --thread {thread_id}\n")
            break
        except EOFError:
            console.print("\n[muted]Goodbye![/muted]\n")
            break


@app.command()
def main(
    thread: Optional[str] = typer.Option(
        None,
        "--thread", "-t",
        help="Resume an existing conversation thread by ID",
    ),
    new: bool = typer.Option(
        False,
        "--new", "-n",
        help="Force create a new thread even if one is provided",
    ),
) -> None:
    """
    🎵 Start the Music Store Agent CLI.
    
    Chat with an AI-powered customer support agent for a digital music store.
    The agent can help you with:
    
    • Browse the music catalog (artists, albums, songs, genres)
    
    • Check your invoice and purchase history
    
    • Get personalized recommendations based on your preferences
    
    Examples:
    
        uv run music-store                    # Start new conversation
        
        uv run music-store --thread abc123    # Resume existing thread
    """
    try:
        # Determine thread ID
        if new or thread is None:
            thread_id = str(uuid4())
            is_new = True
        else:
            thread_id = thread
            is_new = not check_thread_exists(thread_id)
        
        run_repl(thread_id, is_new)
        
    except Exception as e:
        console.print(f"[error]Failed to start:[/error] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

