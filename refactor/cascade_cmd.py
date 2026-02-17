"""
CLI command for CASCADE generation.

Usage:
    prg cascade . "Add Redis caching layer"
    prg cascade . "Create user authentication API"
"""

import sys
from pathlib import Path

import click

from generator.cascade_orchestrator import CascadeOrchestrator


@click.command("cascade")
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
)
@click.argument("goal", type=str)
@click.option(
    "--output",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Output directory (default: project root)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output",
)
def cascade(
    project_path: str,
    goal: str,
    output: str,
    verbose: bool,
):
    """
    Generate CASCADE: PLAN → DESIGN → TASKS

    Creates Cowork-quality project plans with:
    - PLAN.md (MASTER) with specific files, time estimates, AC
    - DESIGN.md (feeds from PLAN) with API contracts
    - tasks.yaml (feeds from PLAN) with precise breakdown

    Examples:

        \b
        # Add Redis caching
        prg cascade . "Add Redis caching layer"

        \b
        # Create API
        prg cascade . "Create user authentication API" --verbose
    """
    project_path_obj = Path(project_path).resolve()

    # Read README
    readme_path = project_path_obj / "README.md"
    if not readme_path.exists():
        click.echo("⚠️  No README.md found", err=True)
        readme_content = f"# {project_path_obj.name}"
    else:
        readme_content = readme_path.read_text(encoding="utf-8", errors="replace")

    # Output directory
    if output:
        output_dir = Path(output)
    else:
        output_dir = project_path_obj

    click.echo("🚀 CASCADE Orchestrator (Cowork-Powered)\n")
    click.echo(f"📁 Project: {project_path_obj.name}")
    click.echo(f"🎯 Goal: {goal}")
    click.echo(f"📂 Output: {output_dir}\n")

    try:
        # Create orchestrator
        orchestrator = CascadeOrchestrator(project_path_obj)

        click.echo("🔍 Scanning project files...")

        # Generate CASCADE
        plan_content, design_content, tasks_yaml = orchestrator.create_cascade(
            goal,
            readme_content
        )

        if verbose:
            click.echo(f"\n📋 Generated {plan_content.count('###')} tasks")
            click.echo(f"🎨 Extracted {design_content.count('###')} components")

        # Export files
        plan_file, design_file, tasks_file = orchestrator.export_cascade(
            plan_content,
            design_content,
            tasks_yaml,
            output_dir
        )

        click.echo("\n✅ CASCADE generated successfully!\n")
        click.secho(f"📄 PLAN.md (MASTER):", fg="green", bold=True)
        click.echo(f"   {plan_file}")
        click.echo(f"   - Specific files per task")
        click.echo(f"   - Time estimates & dependencies")
        click.echo(f"   - Measurable acceptance criteria")

        click.secho(f"\n🎨 DESIGN.md:", fg="blue", bold=True)
        click.echo(f"   {design_file}")
        click.echo(f"   - API contracts & interfaces")
        click.echo(f"   - Component architecture")

        click.secho(f"\n📋 tasks.yaml:", fg="yellow", bold=True)
        click.echo(f"   {tasks_file}")
        click.echo(f"   - Precise task breakdown")
        click.echo(f"   - Status tracking ready")

        click.echo("\n💡 Next steps:")
        click.echo(f"   1. Review {plan_file.name}")
        click.echo(f"   2. Refine task estimates if needed")
        click.echo(f"   3. Start execution with task #1")

    except Exception as e:
        click.echo(f"\n❌ Error generating CASCADE: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
