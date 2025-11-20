"""CLI interface for the AI Strategist."""

import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from research2jira.orchestrator import AIStrategist

__all__ = ("main",)

app = typer.Typer(help="AI Strategist - Turn research requests into Jira tasks")
console = Console()


@app.command()
def start(
    session_id: Annotated[
        str | None, typer.Option(help="Session ID (auto-generated if not provided)")
    ] = None,
) -> None:
    """Start an interactive AI Strategist session."""
    strategist = AIStrategist(session_id=session_id)

    console.print(
        Panel(
            "[bold green]AI Strategist[/bold green]\n\n"
            "I'll help you turn your research request into structured Jira tasks.\n"
            "Please describe your research request.",
            title="Welcome",
            border_style="green",
        )
    )

    try:
        while True:
            # Get user input
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("\n[bold yellow]Session ended.[/bold yellow]")
                break

            # Process turn
            user_view, telemetry_block = strategist.process_turn(user_input)

            # Display user view
            console.print("\n[bold blue]AI Strategist:[/bold blue]")
            console.print(Markdown(user_view))

            # Display telemetry (in a collapsible way)
            console.print("\n[dim]--- TELEMETRY ---[/dim]")
            console.print(telemetry_block)
            console.print("[dim]--- END TELEMETRY ---[/dim]\n")

            # Check if complete
            if strategist.is_complete():
                console.print(
                    Panel(
                        "[bold green]✓ Research plan dispatched to Jira![/bold green]",
                        title="Complete",
                        border_style="green",
                    )
                )
                break

    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Session interrupted.[/bold yellow]")
        sys.exit(0)
    except (ValueError, RuntimeError, KeyError) as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command()
def process(
    input_text: Annotated[str, typer.Argument(help="Research request text")],
    session_id: Annotated[str | None, typer.Option(help="Session ID")] = None,
    show_telemetry: Annotated[
        bool | None, typer.Option("--telemetry/--no-telemetry", help="Show telemetry")
    ] = None,
) -> None:
    """Process a single research request (non-interactive)."""
    if show_telemetry is None:
        show_telemetry = True
    strategist = AIStrategist(session_id=session_id)

    user_view, telemetry_block = strategist.process_turn(input_text)

    console.print(Markdown(user_view))

    if show_telemetry:
        console.print("\n[dim]--- TELEMETRY ---[/dim]")
        console.print(telemetry_block)
        console.print("[dim]--- END TELEMETRY ---[/dim]")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
