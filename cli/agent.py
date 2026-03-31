"""Agent commands for project rules generator.

The three largest commands (design, plan, review) live in their own modules.
This file houses the remaining small commands and re-exports everything so
cli/cli.py can continue to import from cli.agent without change.
"""

import os
import sys
from pathlib import Path

import click

from cli._version import __version__
from cli.cmd_design import design
from cli.cmd_plan import plan
from cli.cmd_review import review
from cli.utils import detect_provider as _detect_provider
from cli.utils import set_api_key_env as _set_api_key


@click.command(name="start")
@click.argument("task_description")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def start(task_description, project_path, provider, api_key, verbose):
    """Full agent workflow: plan -> tasks -> preflight -> auto-fix -> ready."""
    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    from generator.planning.workflow import AgentWorkflow

    workflow = AgentWorkflow(
        project_path=Path(project_path).resolve(),
        task_description=task_description,
        provider=provider,
        api_key=api_key,
        verbose=verbose,
    )

    try:
        workflow.run_full()
    except Exception as e:
        click.echo(f"Workflow failed: {e}", err=True)
        sys.exit(1)


@click.command(name="setup")
@click.argument("task_description")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def setup(task_description, project_path, provider, api_key, verbose):
    """Setup workflow: plan -> tasks -> preflight -> auto-fix (no execution)."""
    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    from generator.planning.workflow import AgentWorkflow

    workflow = AgentWorkflow(
        project_path=Path(project_path).resolve(),
        task_description=task_description,
        provider=provider,
        api_key=api_key,
        verbose=verbose,
    )

    try:
        manifest = workflow.run_setup()
        click.echo(f"\nSetup complete: {len(manifest.tasks)} tasks created.")
        click.echo("Run 'prg status' to see progress or 'prg exec tasks/<file>' to begin.")
    except Exception as e:
        click.echo(f"Setup failed: {e}", err=True)
        sys.exit(1)


@click.command(name="agent")
@click.argument("query")
def agent_command(query):
    """Simulate agent auto-trigger matching for a query."""
    from generator.planning.agent_executor import AgentExecutor

    project_path = Path(os.getcwd())
    executor = AgentExecutor(project_path)
    matched_skill = executor.match_skill(query)

    if matched_skill:
        click.echo(f"🎯 Auto-trigger: {matched_skill}")
    else:
        click.echo("No matching skill found.")


# Re-export for cli.py backward compat
__all__ = ["design", "plan", "review", "start", "setup", "agent_command"]
