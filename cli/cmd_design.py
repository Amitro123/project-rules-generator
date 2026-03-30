"""design command — Generate a technical design document (Stage 1 of two-stage planning)."""

from pathlib import Path

import click

from cli._version import __version__
from cli.utils import detect_provider as _detect_provider
from cli.utils import set_api_key_env as _set_api_key


@click.command(name="design")
@click.argument("description")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="DESIGN.md",
    help="Output file (default: DESIGN.md)",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider (gemini, groq, anthropic, openai). Auto-detected if omitted.",
)
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def design(description, project_path, output, api_key, provider, verbose):
    """Generate a technical design document (Stage 1 of two-stage planning)."""
    project_path = Path(project_path).resolve()
    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    if verbose:
        click.echo(f"Project Rules Generator v{__version__} — Design Generator")
        click.echo(f"Request: {description}")
        click.echo(f"Project: {project_path}")

    enhanced_context = None
    try:
        from generator.parsers.enhanced_parser import EnhancedProjectParser

        parser = EnhancedProjectParser(project_path)
        enhanced_context = parser.extract_full_context()
        if verbose:
            meta = enhanced_context.get("metadata", {})
            click.echo(f"Context: {meta.get('project_type', 'unknown')} ({', '.join(meta.get('tech_stack', []))})")
    except Exception as exc:
        if verbose:
            click.echo(f"Context extraction skipped: {exc}")

    from generator.design_generator import DesignGenerator

    generator = DesignGenerator(provider=provider)

    if verbose:
        click.echo("Generating design...")

    design_obj = generator.generate_design(
        description,
        project_context=enhanced_context,
        project_path=project_path,
    )

    design_md = design_obj.to_markdown()

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_path / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(design_md, encoding="utf-8")

    click.echo(f"\nDesign: {design_obj.title}")
    click.echo(f"  Decisions: {len(design_obj.architecture_decisions)}")
    click.echo(f"  API contracts: {len(design_obj.api_contracts)}")
    click.echo(f"  Data models: {len(design_obj.data_models)}")
    click.echo(f"  Success criteria: {len(design_obj.success_criteria)}")
    click.echo(f"Written to: {output_path}")
