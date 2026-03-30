"""README resolution for the analyze command.

Finds, optionally generates interactively, and parses the project README.
Extracted from analyze_cmd.py to keep each module focused.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import click


def resolve_readme(
    project_path: Path,
    interactive: bool,
    ai: bool,
    verbose: bool,
) -> Tuple[Optional[Path], Dict[str, Any], str]:
    """Find the README, optionally generate it interactively, and build project_data.

    Returns:
        (readme_path, project_data, project_name)
        readme_path may be None if no README exists and generation was skipped.
    """
    from generator.readme_generator import is_readme_minimal
    from generator.utils.readme_bridge import find_readme

    readme_path = find_readme(project_path)

    # Interactive README generation when missing or minimal
    if not readme_path or (readme_path and is_readme_minimal(readme_path)):
        if interactive:
            try:
                from generator.interactive import create_readme_interactive
                from generator.project_analyzer import ProjectAnalyzer
                from generator.readme_generator import generate_readme_template, generate_readme_with_llm

                user_input_data = create_readme_interactive(project_path)
                analyzer = ProjectAnalyzer(project_path)
                context = analyzer.analyze()

                if ai:
                    click.echo("🤖 Generating README with AI...\n")
                    content = generate_readme_with_llm(user_input_data, context)
                else:
                    content = generate_readme_template(user_input_data, context)

                if not readme_path:
                    readme_path = project_path / "README.md"

                readme_path.write_text(content, encoding="utf-8")
                click.echo(f"✅ README.md created/updated and saved to {readme_path}\n")

            except Exception as e:
                click.echo(f"⚠️  README generation failed: {e}")
        else:
            if not readme_path:
                click.echo("⚠️  No README found. Context will be limited.")
                click.echo("💡 Tip: Use --interactive to auto-generate a professional README.")
            else:
                click.echo(f"⚠️  README ({readme_path.name}) is minimal. Context may be limited.")
                click.echo("💡 Tip: Use --interactive to improve it.")

    # Normalise: treat missing/non-existent README as None
    if not readme_path or not readme_path.exists():
        readme_path = None

    # Build project_data
    if readme_path and readme_path.exists():
        from generator.analyzers.readme_parser import parse_readme

        if verbose:
            click.echo(f"README: {readme_path}")
        project_data = parse_readme(readme_path)
    else:
        click.echo("ℹ️  Proceeding with structure-only analysis...")
        from generator.project_analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(project_path)
        context = analyzer.analyze()
        project_data = {
            "name": project_path.name,
            "tech_stack": sorted(list(set(sum(context["tech_stack"].values(), [])))),
            "features": [],
            "description": "No README provided.",
            "raw_name": project_path.name,
            "readme_path": None,
        }

    project_name = project_data["name"]

    if verbose:
        click.echo("\nDetected:")
        click.echo(f"   Name: {project_name}")
        click.echo(
            f"   Tech: {', '.join(project_data['tech_stack']) if project_data['tech_stack'] else 'None detected'}"
        )
        click.echo(f"   Features: {len(project_data['features'])} found")

    return readme_path, project_data, project_name
