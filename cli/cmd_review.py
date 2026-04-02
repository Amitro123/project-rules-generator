"""review command — Review a generated artifact for quality and hallucinations."""

import sys
from pathlib import Path
from typing import Any, Optional

import click

from cli._version import __version__
from cli.utils import detect_provider as _detect_provider
from cli.utils import set_api_key_env as _set_api_key


@click.command(name="review")
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory for README context",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file (default: CRITIQUE.md next to input)",
)
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider (gemini, groq, anthropic, openai). Auto-detected if omitted.",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option("--tasks", is_flag=True, help="Generate executable tasks from review")
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def review(filepath, project_path, output, provider, api_key, tasks, verbose):
    """Review a generated artifact for quality and hallucinations."""
    filepath = Path(filepath).resolve()
    project_path = Path(project_path).resolve()

    provider = _detect_provider(provider, api_key)

    if provider is None:
        click.echo(
            "Error: No AI provider available. Set an API key environment variable "
            "(e.g. ANTHROPIC_API_KEY, OPENAI_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY).",
            err=True,
        )
        sys.exit(1)

    _set_api_key(provider, api_key)

    if verbose:
        click.echo(f"Project Rules Generator v{__version__} — Self-Review")
        click.echo(f"Reviewing: {filepath}")
        click.echo(f"Provider: {provider}")

    from generator.planning import SelfReviewer

    reviewer = SelfReviewer(provider=provider, api_key=api_key)

    try:
        report = reviewer.review(filepath, project_path=project_path)
    except Exception as e:
        click.echo(f"Review failed: {e}", err=True)
        sys.exit(1)

    _display_review_report(report, verbose)

    output_path = _resolve_output_path(filepath, output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.to_markdown(), encoding="utf-8")
    click.echo(f"\nCritique written to: {output_path}")

    if tasks:
        _generate_tasks_from_review(filepath, project_path, api_key, verbose)


def _display_review_report(report: Any, verbose: bool) -> None:
    """Print the review report to stdout using rich if available."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Review Summary")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Verdict", report.verdict)
        table.add_row("Strengths", str(len(report.strengths)))
        table.add_row("Issues", str(len(report.issues)))
        table.add_row("Hallucinations", str(len(report.hallucinations)))
        console.print(table)

        if report.strengths and verbose:
            click.echo("\nStrengths:")
            for s in report.strengths:
                click.echo(f"  + {s}")

        if report.issues:
            click.echo("\nIssues:")
            for i in report.issues:
                click.echo(f"  - {i}")

        if report.hallucinations:
            click.echo("\nHallucinations:")
            for h in report.hallucinations:
                click.echo(f"  ! {h}")

        if report.action_plan and verbose:
            click.echo("\nAction Plan:")
            for a in report.action_plan:
                click.echo(f"  [ ] {a}")

    except ImportError:
        click.echo(f"\nVerdict: {report.verdict}")
        click.echo(f"Strengths: {len(report.strengths)}")
        click.echo(f"Issues: {len(report.issues)}")
        click.echo(f"Hallucinations: {len(report.hallucinations)}")
        for i in report.issues:
            click.echo(f"  - {i}")
        for h in report.hallucinations:
            click.echo(f"  ! {h}")


def _resolve_output_path(filepath: Path, output: Optional[str]) -> Path:
    """Resolve the critique output path."""
    if not output:
        return filepath.parent / "CRITIQUE.md"
    path = Path(output)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _generate_tasks_from_review(
    filepath: Path,
    project_path: Path,
    api_key: Optional[str],
    verbose: bool,
) -> None:
    """Generate executable tasks from a review report."""
    from generator.planning.task_creator import TaskCreator
    from generator.task_decomposer import TaskDecomposer

    if verbose:
        click.echo("Generating executable tasks from review...")

    try:
        decomposer = TaskDecomposer(api_key=api_key)
        subtasks = decomposer.from_plan(filepath)

        creator = TaskCreator()
        output_dir = project_path / ".clinerules" / "tasks"
        creator.create_from_subtasks(
            subtasks,
            plan_file=filepath.name,
            task_description=f"Generated from {filepath.name}",
            output_dir=output_dir,
        )
        click.echo(f"✅ Created {len(subtasks)} tasks in {output_dir}")
    except Exception as e:
        click.echo(f"❌ Failed to generate tasks: {e}", err=True)
