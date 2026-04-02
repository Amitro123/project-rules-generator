from pathlib import Path

import click

from cli.agent import _detect_provider, _set_api_key
from generator.planning.project_manager import ProjectManager


@click.command(name="manager")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider (gemini, groq, anthropic, openai). Auto-detected if omitted.",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def manager(project_path, provider, api_key, verbose):
    """👨‍💼 Project Manager: Full Lifecycle (Setup -> Verify -> Execute -> Report)."""
    project_path = Path(project_path).resolve()

    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    pm = ProjectManager(project_path=project_path, provider=provider, api_key=api_key, verbose=verbose)

    try:
        pm.run_lifecycle()
    except RuntimeError as exc:
        click.secho(f"\n❌ {exc}", fg="red", err=True)
        raise click.exceptions.Exit(1)
