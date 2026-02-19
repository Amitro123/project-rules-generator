"""Gaps and Spec commands for traceability and requirement management."""

from pathlib import Path

import click

from generator.planning.task_creator import TaskManifest
from generator.requirements import Requirement, RequirementsInferrer
from generator.tasks import TraceabilityMatrix
from refactor.agent import _detect_provider, _set_api_key


@click.command(name="gaps")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--spec", type=click.Path(exists=True), help="Path to spec.md")
@click.option("--infer", is_flag=True, help="Infer requirements from code/history")
@click.option("--provider", type=click.Choice(["gemini", "groq"]), default=None)
@click.option("--api-key", help="API Key")
def gaps(project_path, spec, infer, provider, api_key):
    """Show spec-task gaps and traceability matrix."""
    project_path = Path(project_path).resolve()
    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    inferrer = RequirementsInferrer(provider=provider, api_key=api_key)
    requirements = []

    if spec:
        # Load from spec.md (minimal placeholder parsing)
        content = Path(spec).read_text(encoding="utf-8")
        # Extract ID: DESC: pattern
        import re
        matches = re.finditer(r"ID:\s*(.+)\nDESC:\s*(.+)", content)
        for m in matches:
            requirements.append(Requirement(id=m.group(1).strip(), description=m.group(2).strip(), source="spec.md"))
    
    if infer or not requirements:
        click.echo("Inferring requirements...")
        requirements.extend(inferrer.infer(project_path))

    # Load tasks
    manifest_path = project_path / "tasks" / "TASKS.yaml"
    if not manifest_path.exists():
        click.echo("No TASKS.yaml found. Run 'prg tasks' first.")
        return

    manifest = TaskManifest.from_yaml(manifest_path)
    matrix = TraceabilityMatrix(requirements=requirements, tasks=manifest.tasks)
    matrix.build()

    from rich.console import Console
    from rich.markdown import Markdown
    console = Console()
    
    click.echo("\nTraceability Matrix:")
    console.print(Markdown(matrix.format_table()))

    missing = matrix.get_gaps()
    if missing:
        click.echo(f"\nFound {len(missing)} missing requirements!")
        for m in missing:
            click.echo(f"  - [{m.id}] {m.description}")
    else:
        click.echo("\nRequirement Coverage: 100%")

@click.command(name="spec")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--generate", is_flag=True, help="Generate spec.md from inference")
@click.option("--provider", type=click.Choice(["gemini", "groq"]), default=None)
@click.option("--api-key", help="API Key")
def spec_cmd(project_path, generate, provider, api_key):
    """Manage project specifications."""
    if not generate:
        click.echo("Use --generate to create/update spec.md")
        return

    project_path = Path(project_path).resolve()
    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    click.echo("Inferring requirements for spec.md...")
    inferrer = RequirementsInferrer(provider=provider, api_key=api_key)
    requirements = inferrer.infer(project_path)

    spec_content = "# Project Specification\n\nGenerated from codebase inference.\n\n"
    for r in requirements:
        spec_content += f"ID: {r.id}\nDESC: {r.description}\nPRIORITY: {r.priority}\nSOURCE: {r.source}\n---\n"

    spec_path = project_path / "spec.md"
    spec_path.write_text(spec_content, encoding="utf-8")
    click.echo(f"Generated {len(requirements)} requirements in {spec_path.name}")
