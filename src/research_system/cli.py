"""Command Line Interface for the Multi-Agent Research System."""

import argparse
import sys
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from src.research_system.config import get_settings
from src.research_system.pipeline import ResearchPipeline

console = Console()

STAGE_MESSAGES = {
    "research": "[1/5] Researching sources with Tavily...",
    "reading": "[2/5] Fetching and extracting web pages in parallel...",
    "drafting": "[3/5] Drafting research report...",
    "critiquing": "[4/5] Auditing report for accuracy, gaps, and style...",
    "revising": "[5/5] Revising report with critique and diagrams...",
    "completed": "Research complete.",
}


def print_banner(model_name: str, k: int):
    """Display the system banner."""
    console.rule("[bold cyan]Multi-Agent Research System[/bold cyan]")
    console.print(
        f"[dim]Model: {model_name} | Max Sources: {k} | Output Directory: output/[/dim]\n"
    )


def print_critique_table(critique):
    """Render the editorial review log in a styled table."""
    if not critique or not critique.items:
        return

    table = Table(
        title="Editorial Critique & Review Log",
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Severity", justify="center")
    table.add_column("Issue Identified", style="white")
    table.add_column("Actionable Suggestion", style="green")

    severity_colors = {
        "High": "[bold red]High[/bold red]",
        "Medium": "[bold yellow]Medium[/bold yellow]",
        "Low": "[dim green]Low[/dim green]",
    }

    for item in critique.items:
        sev = severity_colors.get(item.severity, item.severity)
        table.add_row(item.category, sev, item.description, item.suggestion)

    console.print(table)
    if critique.overall_assessment:
        console.print(
            Panel(
                f"[bold]Overall Assessment:[/bold] {critique.overall_assessment}",
                border_style="magenta",
                title="Editor's Assessment",
            )
        )


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Research System")
    parser.add_argument("query", nargs="?", help="Research topic or question")
    parser.add_argument("--fast", action="store_true", help="Fast mode: skip critique pass")
    parser.add_argument("-k", "--sources", type=int, help="Number of sources to fetch")
    args = parser.parse_args()

    settings = get_settings()
    print_banner(settings.model_name, args.sources or settings.tavily_k)

    try:
        settings.validate_api_keys()
    except ValueError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        console.print("[dim]Create or edit .env based on .env.example with your API keys.[/dim]")
        sys.exit(1)

    query = args.query
    if not query:
        try:
            query = Prompt.ask("[bold green]Enter research query[/bold green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Aborted by user.[/dim]")
            sys.exit(0)

    if not query or not query.strip():
        console.print("[yellow]No query provided. Exiting.[/yellow]")
        sys.exit(0)

    pipeline = ResearchPipeline()

    try:
        with console.status(STAGE_MESSAGES["research"], spinner="dots") as status:

            def on_stage_start(stage: str):
                msg = STAGE_MESSAGES.get(stage, f"Processing {stage}...")
                status.update(f"[bold cyan]{msg}[/bold cyan]")

            result = pipeline.run(
                query=query.strip(),
                max_sources=args.sources,
                skip_critique=args.fast,
                on_stage_start=on_stage_start,
            )

        # 1. Print formatted markdown report
        console.print(
            Panel(
                Markdown(result.to_markdown()),
                title=f"[bold green]Report: {result.report.title}[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )

        # 2. Print critique table if present
        if result.critique and result.critique.items:
            print_critique_table(result.critique)

        # 3. Save report to output/
        saved_path = pipeline.save_report(result, query=query)
        console.print(f"[bold green]Report saved to:[/bold green] [underline]{saved_path}[/underline]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Research interrupted by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error running pipeline:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
