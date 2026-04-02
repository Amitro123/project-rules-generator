"""plan command — Break down a task into subtasks and generate PLAN.md."""

import sys
from pathlib import Path

import click

from cli._version import __version__
from cli.agent_plan_helpers import (
    handle_plan_from_readme,
    handle_plan_status,
    run_interactive_mode,
    write_tasks_manifest,
)
from cli.utils import detect_provider as _detect_provider
from cli.utils import has_api_key as _has_api_key
from cli.utils import set_api_key_env as _set_api_key


@click.command(name="plan")
@click.argument("task_description", required=False, default=None)
@click.option(
    "--from-design",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Generate plan from a DESIGN.md file",
)
@click.option(
    "--from-readme",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Generate roadmap from README.md",
)
@click.option("--status", is_flag=True, help="Show progress on existing plans")
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
    default=None,
    help="Output file for the plan (default: auto-generated)",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider (gemini, groq, anthropic, openai). Auto-detected if omitted.",
)
@click.option("--interactive", is_flag=True, help="Open files in IDE as tasks are listed")
@click.option("--auto-execute", is_flag=True, help="Agent executes tasks automatically (requires --interactive)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "mermaid"]),
    default="markdown",
    help="Output format: markdown (default) or mermaid (diagram)",
)
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def plan(
    task_description,
    from_design,
    from_readme,
    status,
    project_path,
    output,
    api_key,
    provider,
    interactive,
    auto_execute,
    output_format,
    verbose,
):
    """Break down a task into subtasks and generate PLAN.md."""
    project_path = Path(project_path).resolve()

    # Auto-detect: if task_description is a directory, treat as project + README
    if task_description and not from_readme and not from_design and not status:
        candidate = Path(task_description)
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        if candidate.is_dir():
            project_path = candidate.resolve()
            readme_candidate = project_path / "README.md"
            if readme_candidate.exists():
                from_readme = str(readme_candidate)
                task_description = None
                if verbose:
                    click.echo(f"Auto-detected project directory: {project_path}")
                    click.echo(f"Using README: {readme_candidate}")

    if status:
        handle_plan_status(project_path)

    if from_readme:
        provider = _detect_provider(provider, api_key)
        _set_api_key(provider, api_key)
        handle_plan_from_readme(
            from_readme=from_readme,
            project_path=project_path,
            provider=provider,
            api_key=api_key,
            output=output,
            output_format=output_format,
            verbose=verbose,
            version=__version__,
        )

    if not task_description and not from_design:
        click.echo(
            "Error: Provide a TASK_DESCRIPTION, --from-readme, --from-design, or --status.",
            err=True,
        )
        sys.exit(1)

    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    if provider and not _has_api_key(provider, api_key) and verbose:
        click.echo(
            f"Warning: provider '{provider}' selected but no API key found — "
            "using template-based generation.",
            err=True,
        )

    if verbose:
        click.echo(f"Project Rules Generator v{__version__} — Task Planner")
        if from_design:
            click.echo(f"From design: {from_design}")
        else:
            click.echo(f"Task: {task_description}")
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

    from generator.task_decomposer import TaskDecomposer

    decomposer = TaskDecomposer(provider=provider, api_key=api_key)
    if verbose:
        click.echo("Decomposing task...")

    if from_design:
        subtasks = decomposer.from_design(Path(from_design), project_context=enhanced_context)
        from generator.design_generator import Design

        design_obj = Design.from_markdown(Path(from_design).read_text(encoding="utf-8"))
        user_task_label = design_obj.title
    else:
        subtasks = decomposer.decompose(task_description, project_context=enhanced_context, project_path=project_path)
        user_task_label = task_description

    plan_md = decomposer.generate_plan_md(subtasks, user_task=user_task_label)

    output_file = output or "PLAN.md"
    output_path = Path(output_file)
    if not output_path.is_absolute():
        output_path = project_path / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(plan_md, encoding="utf-8")

    tasks_path = write_tasks_manifest(output_path, user_task_label, subtasks)

    click.echo(f"\nGenerated {len(subtasks)} subtasks")
    click.echo(f"Plan written to: {output_path}")
    click.echo(f"Tasks manifest: {tasks_path}")
    click.echo(f"Estimated time: {sum(t.estimated_minutes for t in subtasks)} minutes")

    if interactive:
        run_interactive_mode(subtasks, project_path, auto_execute)
