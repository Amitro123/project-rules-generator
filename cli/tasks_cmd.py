"""Tasks command for comprehensive task generation."""

from pathlib import Path

import click

from cli.agent import _detect_provider, _set_api_key
from generator.planning.task_creator import TaskCreator
from generator.requirements import RequirementsInferrer
from generator.task_decomposer import TaskDecomposer


@click.command(name="tasks")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--infer-spec", is_flag=True, help="Auto-create requirements if spec.md is missing")
@click.option("--provider", type=click.Choice(["gemini", "groq"]), default=None)
@click.option("--api-key", help="API Key")
@click.option("--verbose/--quiet", default=True)
def tasks_cmd(project_path, infer_spec, provider, api_key, verbose):
    """Comprehensive task generation from multiple sources."""
    project_path = Path(project_path).resolve()
    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    # 1. Gather requirements
    spec_path = project_path / "spec.md"
    requirements = []

    if infer_spec or not spec_path.exists():
        if verbose:
            click.echo("Inferring requirements...")
        try:
            inferrer = RequirementsInferrer(provider=provider, api_key=api_key)
            requirements = inferrer.infer(project_path)
        except ValueError as e:
            click.echo(f"⚠️  Cannot infer requirements: {e}")
            click.echo("Set GROQ_API_KEY or GEMINI_API_KEY, or create a spec.md file.")
            return
    else:
        # Load from spec.md
        content = spec_path.read_text(encoding="utf-8")
        import re

        matches = re.finditer(r"ID:\s*(.+)\nDESC:\s*(.+)", content)
        for m in matches:
            requirements.append(m.group(2).strip())

    if not requirements:
        click.echo("No requirements found. Add a spec.md or use --infer-spec.")
        return

    # 2. Decompose to tasks
    if verbose:
        click.echo(f"Decomposing {len(requirements)} requirements into tasks...")
    decomposer = TaskDecomposer(api_key=api_key)

    # Simple consolidation: feed all requirements as context
    req_context = "\n".join([f"- {r if isinstance(r, str) else r.description}" for r in requirements])
    subtasks = decomposer.decompose(
        user_task="Fully implement all project requirements",
        project_context={"metadata": {"requirements": req_context}},
        project_path=project_path,
    )

    # 3. Create manifest and files
    creator = TaskCreator()
    output_dir = project_path / "tasks"
    creator.create_from_subtasks(
        subtasks,
        plan_file="requirements-inference",
        task_description="Generated from comprehensive requirement inference",
        output_dir=output_dir,
    )

    click.echo(f"Generated {len(subtasks)} tasks in {output_dir}")
