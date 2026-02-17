"""
CLI command for Cowork-powered skill creation.

Usage:
    prg create-skills .
    prg create-skills . --skill "fastapi-security-auditor"
    prg create-skills . --ai --quality-threshold 80
"""

import sys
from pathlib import Path

import click

from generator.skill_creator import CoworkSkillCreator, QualityReport
from refactor.config_cmd import load_config


@click.command("create-skills")
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
)
@click.option(
    "--skill",
    type=str,
    help="Specific skill name to create (e.g., 'fastapi-security-auditor')",
)
@click.option(
    "--ai",
    is_flag=True,
    help="Use AI for enhanced skill generation (requires GEMINI_API_KEY)",
)
@click.option(
    "--quality-threshold",
    type=int,
    default=70,
    help="Minimum quality score (0-100) to accept generated skill",
)
@click.option(
    "--output",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Output directory (default: .clinerules/skills/project)",
)
@click.option(
    "--auto-fix/--no-auto-fix",
    default=True,
    help="Automatically fix quality issues",
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
@click.option(
    "--provider",
    type=str,
    default=None,
    help="AI Provider (gemini, groq). Defaults to config or gemini.",
)
def create_skills(
    project_path: str,
    skill: str,
    ai: bool,
    quality_threshold: int,
    output: str,
    auto_fix: bool,
    export_report: bool,
    verbose: bool,
    provider: str,
):
    """
    Create Cowork-quality skills for your project.

    This command uses Cowork's intelligent skill creation logic to generate
    high-quality, project-specific skills with:

    - Smart auto-trigger optimization (multiple natural invocation patterns)
    - Intelligent tool selection based on tech stack
    - Quality gates ensuring actionability
    - Hallucination prevention (no fake file paths)
    - Specific, actionable steps

    Examples:

        \b
        # Auto-generate skills from README
        prg create-skills .

        \b
        # Create specific skill
        prg create-skills . --skill "fastapi-security-auditor"

        \b
        # High-quality mode with AI
        prg create-skills . --ai --quality-threshold 85
    """
    project_path_obj = Path(project_path).resolve()

    # Read README
    readme_path = project_path_obj / "README.md"
    if not readme_path.exists():
        click.echo("⚠️  No README.md found. Using project structure only.", err=True)
        readme_content = f"# {project_path_obj.name}\n\nProject analysis in progress..."
    else:
        readme_content = readme_path.read_text(encoding="utf-8", errors="replace")

    # Determine provider
    if not provider:
        config = load_config()
        provider = config.get("llm", {}).get("provider", "gemini")
    
    if verbose and ai:
        click.echo(f"🤖 AI Provider: {provider}")

    # Initialize creator
    creator = CoworkSkillCreator(project_path_obj)

    # Determine output directory
    if output:
        output_dir = Path(output)
    else:
        output_dir = project_path_obj / ".clinerules" / "skills" / "project"

    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo("🚀 Cowork-Powered Skill Creator\n")
    click.echo(f"📁 Project: {project_path_obj.name}")
    click.echo(f"📂 Output: {output_dir}\n")

    if skill:
        # Create single skill
        _create_single_skill(
            creator,
            skill,
            readme_content,
            output_dir,
            quality_threshold,
            auto_fix,
            verbose,
            export_report,
            provider,
            ai,
        )
    else:
        # Auto-generate skills from README
        _auto_generate_skills(
            creator,
            readme_content,
            project_path_obj,
            output_dir,
            quality_threshold,
            auto_fix,
            verbose,
            provider,
            ai,
        )

    click.echo("\n✅ Skill generation complete!")
    click.echo(f"\n💡 Skills saved to: {output_dir}")
    click.echo("\n🔍 To use skills, run: prg agent \"<your request>\"")


def _create_single_skill(
    creator: CoworkSkillCreator,
    skill_name: str,
    readme_content: str,
    output_dir: Path,
    quality_threshold: int,
    auto_fix: bool,
    verbose: bool,
    export_report: bool,
    provider: str,
    use_ai: bool,
):
    """Create a single skill with quality validation."""

    click.echo(f"Creating skill: {skill_name}...")

    try:
        content, metadata, quality = creator.create_skill(
            skill_name, readme_content, use_ai=use_ai, provider=provider
        )

        # Display quality report
        _display_quality_report(quality, verbose)

        if quality.score < quality_threshold:
            click.echo(
                f"\n⚠️  Quality score {quality.score:.1f} is below threshold {quality_threshold}",
                err=True,
            )
            if not auto_fix:
                click.echo("❌ Skill rejected. Use --auto-fix to attempt fixes.", err=True)
                sys.exit(1)
            else:
                click.echo("🔧 Applying auto-fixes...", err=True)

        # Export skill
        skill_file = creator.export_to_file(content, metadata, output_dir)
        click.echo(f"\n✅ Created: {skill_file.name}")

        # Display metadata summary
        click.echo(f"\n📊 Skill Metadata:")
        click.echo(f"   - Auto-triggers: {len(metadata.auto_triggers)}")
        click.echo(f"   - Tools: {len(metadata.tools)}")
        click.echo(f"   - Project signals: {len(metadata.project_signals)}")

        if verbose:
            click.echo(f"\n🎯 Auto-Triggers:")
            for trigger in metadata.auto_triggers[:5]:
                click.echo(f"   - \"{trigger}\"")

            click.echo(f"\n🛠️  Tools:")
            for tool in metadata.tools:
                click.echo(f"   - {tool}")

        # Export report if requested
        if export_report:
            report_path = output_dir / f"{skill_name}.quality.json"
            import json
            report_data = {
                "score": quality.score,
                "passed": quality.passed,
                "issues": quality.issues,
                "warnings": quality.warnings,
                "suggestions": quality.suggestions,
                "metadata": {
                    "triggers": metadata.auto_triggers,
                    "tools": metadata.tools,
                    "signals": metadata.project_signals,
                },
            }
            report_path.write_text(json.dumps(report_data, indent=2))
            click.echo(f"\n📄 Quality report: {report_path}")

    except Exception as e:
        click.echo(f"\n❌ Error creating skill: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _auto_generate_skills(
    creator: CoworkSkillCreator,
    readme_content: str,
    project_path: Path,
    output_dir: Path,
    quality_threshold: int,
    auto_fix: bool,
    verbose: bool,
    provider: str,
    use_ai: bool,
):
    """Auto-generate skills using the new flow (Global Learned Cache)."""
    click.echo("🔍 Analyzing project for learned skills...")
    
    # Use the new generate_all flow
    # This handles detection, global reuse, creation, and symlinking
    creator.generate_all(project_path, use_ai=use_ai, provider=provider)
    
    click.echo("\n✅ Learned skills generation complete!")
    click.echo(f"   - Verified Global Cache: {creator.discovery.global_learned}")
    click.echo(f"   - Linked to Project: {creator.discovery.project_skills_root}")


def _display_quality_report(quality: QualityReport, verbose: bool):
    """Display quality report with colors."""

    # Quality score with color
    if quality.score >= 90:
        score_color = "green"
    elif quality.score >= 70:
        score_color = "yellow"
    else:
        score_color = "red"

    click.echo(f"\n📈 Quality Score: ", nl=False)
    click.secho(f"{quality.score:.1f}/100", fg=score_color, bold=True)

    if quality.passed:
        click.secho("✅ PASSED", fg="green")
    else:
        click.secho("⚠️  NEEDS IMPROVEMENT", fg="yellow")

    # Show issues/warnings if any
    if quality.issues:
        click.echo(f"\n❌ Issues ({len(quality.issues)}):")
        for issue in quality.issues[:3]:  # Show top 3
            click.echo(f"   - {issue}")

    if quality.warnings and verbose:
        click.echo(f"\n⚠️  Warnings ({len(quality.warnings)}):")
        for warning in quality.warnings[:3]:
            click.echo(f"   - {warning}")

    if quality.suggestions and verbose:
        click.echo(f"\n💡 Suggestions ({len(quality.suggestions)}):")
        for suggestion in quality.suggestions[:3]:
            click.echo(f"   - {suggestion}")
