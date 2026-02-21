"""Autopilot command for project rules generator."""

from pathlib import Path

import click

from cli.agent import _detect_provider, _set_api_key
from generator.planning.autopilot import AutopilotOrchestrator


@click.command(name="autopilot")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--discovery-only", is_flag=True, help="Stop after rule generation and task creation")
@click.option("--execute-only", is_flag=True, help="Assume tasks exist and start execution loop")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq"]),
    default=None,
    help="AI Provider (gemini, groq). Auto-detected if omitted.",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def autopilot(project_path, discovery_only, execute_only, provider, api_key, verbose):
    """Full End-to-End Autopilot: Discovery -> Planning -> Execution."""
    project_path = Path(project_path).resolve()

    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    orchestrator = AutopilotOrchestrator(project_path=project_path, provider=provider, api_key=api_key, verbose=verbose)

    manifest = None

    if not execute_only:
        # PHASE 1: Discovery
        manifest = orchestrator.discovery()

        if discovery_only:
            click.echo("\n✅ Discovery complete. Stopped due to --discovery-only.")
            return

    if manifest is None:
        # Load existing manifest if in --execute-only or if discovery was somehow skipped
        from generator.planning.task_creator import TaskManifest

        manifest_path = project_path / "tasks" / "TASKS.yaml"
        if manifest_path.exists():
            manifest = TaskManifest.from_yaml(manifest_path)
        else:
            click.echo("❌ No tasks found to execute. Run discovery first or check your project path.", err=True)
            return

    # PHASE 2: Execution Loop
    orchestrator.execution_loop(manifest)
