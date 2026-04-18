"""
CLI command for Cowork-powered rules creation.

Usage:
    prg create-rules .
    prg create-rules . --tech fastapi,pytest,docker
    prg create-rules . --quality-threshold 90 --verbose
"""

import json
import sys
from pathlib import Path

import click

from generator.rules_creator import CoworkRulesCreator


@click.command("create-rules")
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
)
@click.option(
    "--tech",
    type=str,
    help="Tech stack (comma-separated, e.g., 'fastapi,pytest,docker')",
)
@click.option(
    "--quality-threshold",
    type=int,
    default=85,
    help="Minimum quality score (0-100) to accept generated rules",
)
@click.option(
    "--output",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Output directory (default: .clinerules)",
)
@click.option(
    "--export-report",
    is_flag=True,
    help="Export quality report to JSON",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output with quality details",
)
def create_rules(
    project_path: str,
    tech: str,
    quality_threshold: int,
    output: str,
    export_report: bool,
    verbose: bool,
):
    """
    Create Cowork-quality coding rules for your project.

    This command uses Cowork's intelligent rules creation logic to generate
    high-quality, project-specific rules with:

    - Tech-specific patterns (FastAPI -> REST best practices)
    - Priority scoring (High/Medium/Low)
    - Anti-pattern extraction from git history
    - Quality validation with conflict detection

    Examples:

        \b
        # Auto-generate rules from README and project structure
        prg create-rules .

        \b
        # Specify tech stack manually
        prg create-rules . --tech "fastapi,pytest,docker"

        \b
        # High-quality mode with detailed report
        prg create-rules . --quality-threshold 90 --verbose
    """
    project_path_obj = Path(project_path).resolve()

    # Read README
    readme_path = project_path_obj / "README.md"
    if not readme_path.exists():
        click.echo("Warning: No README.md found. Using project structure only.", err=True)
        readme_content = f"# {project_path_obj.name}\n\nProject analysis in progress..."
    else:
        readme_content = readme_path.read_text(encoding="utf-8", errors="replace")

    # Parse tech stack
    tech_stack = None
    if tech:
        tech_stack = [t.strip() for t in tech.split(",")]

    # Initialize creator
    creator = CoworkRulesCreator(project_path_obj)

    # Determine output directory
    if output:
        output_dir = Path(output)
    else:
        output_dir = project_path_obj / ".clinerules"

    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo("Cowork-Powered Rules Creator\n")
    click.echo(f"Project: {project_path_obj.name}")
    click.echo(f"Output:  {output_dir}\n")

    try:
        # Generate rules
        click.echo("Analyzing project...")

        content, metadata, quality = creator.create_rules(readme_content, tech_stack=tech_stack)

        # Display metadata
        click.echo(f"\nDetected Tech Stack: {', '.join(metadata.tech_stack) or 'none'}")
        click.echo(f"Project Type: {metadata.project_type}")
        click.echo(f"Priority Areas: {', '.join(metadata.priority_areas) or 'none'}")

        # Display quality report
        _display_quality_report(quality, verbose)

        if quality.score < quality_threshold:
            click.echo(
                f"\nWarning: Quality score {quality.score:.1f} is below threshold {quality_threshold}",
                err=True,
            )
            if quality.issues:
                click.echo("\nIssues that need fixing:", err=True)
                for issue in quality.issues:
                    click.echo(f"   - {issue}", err=True)

            if not click.confirm("\nProceed anyway?"):
                click.echo("Rules generation cancelled.", err=True)
                sys.exit(1)

        # Export rules
        rules_file = creator.export_to_file(content, metadata, output_dir)
        click.echo(f"\nRules generated: {rules_file.name}")

        # Emit machine-readable rules.json for parity with `prg analyze`.
        # Downstream commands (prg agent / prg plan / preflight) read rules.json
        # to decide whether a project has been analyzed — omitting it here
        # silently broke those commands when users chose `prg create-rules`.
        try:
            from generator.rules_generator import rules_to_json
            from prg_utils.file_ops import atomic_write_text

            rules_json_path = output_dir / "rules.json"
            atomic_write_text(rules_json_path, rules_to_json(content), backup=True)
            click.echo(f"JSON export:     {rules_json_path.name}")
        except Exception as exc:  # noqa: BLE001 — non-fatal; rules.md already written
            click.echo(f"Warning: could not write rules.json: {exc}", err=True)

        # Display rule count
        click.echo("\nRules Summary:")
        click.echo(f"   - Tech-specific rules: {sum(1 for t in metadata.tech_stack if t in content.lower())}")
        click.echo(f"   - Priority areas: {len(metadata.priority_areas)}")
        click.echo(f"   - Quality score: {quality.score:.1f}/100")

        # Export report if requested
        if export_report:
            report_path = output_dir / "rules.quality.json"
            report_data = {
                "score": quality.score,
                "passed": quality.passed,
                "completeness": quality.completeness,
                "issues": quality.issues,
                "warnings": quality.warnings,
                "conflicts": quality.conflicts,
                "metadata": {
                    "tech_stack": metadata.tech_stack,
                    "project_type": metadata.project_type,
                    "priority_areas": metadata.priority_areas,
                },
            }
            report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
            click.echo(f"\nQuality report: {report_path}")

        click.echo("\n[OK] Cowork-quality rules generation complete!")
        click.echo(f"\nRules saved to: {rules_file}")

    except Exception as e:  # noqa: BLE001 — CLI boundary: catch all errors to show user-friendly message
        click.echo(f"\nError generating rules: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def _display_quality_report(quality, verbose: bool):
    """Display quality report with colors."""

    # Quality score with color
    if quality.score >= 90:
        score_color = "green"
    elif quality.score >= 85:
        score_color = "yellow"
    else:
        score_color = "red"

    click.echo("\nQuality Assessment:")
    click.echo("   Score: ", nl=False)
    click.secho(f"{quality.score:.1f}/100", fg=score_color, bold=True)
    click.echo(f"   Completeness: {quality.completeness * 100:.0f}%")

    if quality.passed:
        click.secho("   [PASSED]", fg="green")
    else:
        click.secho("   [NEEDS IMPROVEMENT]", fg="yellow")

    # Show issues/warnings if any
    if quality.issues:
        click.echo(f"\nIssues ({len(quality.issues)}):")
        for issue in quality.issues:
            click.echo(f"   - {issue}")

    if quality.conflicts:
        click.echo(f"\nRule Conflicts ({len(quality.conflicts)}):")
        for conflict in quality.conflicts:
            click.echo(f"   - {conflict}")

    if quality.warnings and verbose:
        click.echo(f"\nWarnings ({len(quality.warnings)}):")
        for warning in quality.warnings:
            click.echo(f"   - {warning}")
