"""prg init — first-run wizard."""

import logging
import os
from pathlib import Path
from typing import Optional

import click

from cli._version import __version__
from cli.utils import detect_provider, set_api_key_env

logger = logging.getLogger(__name__)

_PROVIDER_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
}


def _key_available(provider: str, explicit_key: Optional[str]) -> bool:
    if explicit_key:
        return True
    if os.environ.get(_PROVIDER_ENV.get(provider, "")):
        return True
    if provider == "gemini" and os.environ.get("GOOGLE_API_KEY"):
        return True
    return False


@click.command(name="init")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompts")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider. Auto-detected if omitted.",
)
@click.option("--api-key", help="API Key (overrides env var)")
def init(project_path, yes, provider, api_key):
    """First-run wizard: detect stack, generate rules.md, print next steps."""
    from generator.analyzers.readme_parser import parse_readme
    from generator.rules_generator import generate_rules
    from generator.skills_manager import SkillsManager

    project_path = Path(project_path).resolve()

    click.echo(f"Project Rules Generator v{__version__} — Init")
    click.echo(f"Project: {project_path}")
    click.echo()

    # --- 1. Detect provider ---
    provider = detect_provider(provider, api_key)
    set_api_key_env(provider, api_key)
    key_set = _key_available(provider, api_key)

    # --- 2. Find README and parse project data ---
    click.echo("Scanning project...")
    from generator.utils.readme_bridge import find_readme

    readme_path = find_readme(project_path)

    if readme_path:
        project_data = parse_readme(readme_path)
        click.echo(f"  README   : {readme_path.name}")
    else:
        # Minimal fallback — structure-only
        try:
            from generator.project_analyzer import ProjectAnalyzer

            analyzer = ProjectAnalyzer(project_path)
            context = analyzer.analyze()
            tech = sorted(set(sum(context["tech_stack"].values(), [])))
        except Exception as exc:  # noqa: BLE001 — optional enrichment; fallback to empty tech stack
            logger.debug("Tech stack detection failed during init: %s", exc)
            tech = []
        project_data = {
            "name": project_path.name,
            "tech_stack": tech,
            "features": [],
            "description": "",
            "raw_name": project_path.name,
            "readme_path": None,
        }
        click.echo("  README   : (not found — using structure-only)")

    tech_stack = project_data.get("tech_stack") or []
    click.echo(f"  Tech     : {', '.join(tech_stack[:8]) if tech_stack else '(generic)'}")
    click.echo(f"  Provider : {provider} ({'key found' if key_set else 'no key — README-only mode'})")
    click.echo()

    # --- 3. Confirm if .clinerules already exists ---
    output_dir = project_path / ".clinerules"
    if output_dir.exists() and not yes:
        click.echo(f"Output directory already exists: {output_dir}")
        if not click.confirm("Re-generate rules.md?", default=True):
            click.echo("Aborted.")
            return

    # --- 4. Load config and generate rules.md ---
    click.echo("Generating rules.md...")
    try:
        import yaml

        from prg_utils.config_schema import validate_config

        config_path = Path(__file__).parent.parent / "config.yaml"
        raw_config = yaml.safe_load(config_path.read_text()) or {} if config_path.exists() else {}
        config = validate_config(raw_config).model_dump()

        output_dir.mkdir(parents=True, exist_ok=True)
        rules_content = generate_rules(project_data, config)
        rules_file = output_dir / "rules.md"
        rules_file.write_text(rules_content, encoding="utf-8")
        click.echo("  Written: .clinerules/rules.md")
    except Exception as exc:  # noqa: BLE001 — CLI boundary: catch all errors to show user-friendly message
        click.echo(f"  Error generating rules: {exc}", err=True)
        raise SystemExit(1)

    # --- 5. Set up skills structure ---
    click.echo("Setting up skills structure...")
    try:
        sm = SkillsManager(project_path=project_path)
        sm.ensure_global_structure()
        sm.setup_project_structure()
        click.echo("  Skills directories ready.")
    except Exception as exc:  # noqa: BLE001 — CLI boundary: skills setup is optional
        click.echo(f"  Warning: skills setup failed ({exc})")

    # --- 6. Print next steps ---
    click.echo()
    click.echo("Done! Next steps:")
    click.echo()
    if key_set:
        click.echo(f"  prg analyze . --ai --provider {provider}")
        click.echo("    → Deep analysis with AI-generated skills")
        click.echo()
        click.echo("  prg analyze . --create-skill <name> --ai")
        click.echo("    → Create a project-specific skill")
    else:
        click.echo("  prg analyze .")
        click.echo("    → Full analysis (README-only)")
        click.echo()
        click.echo("  export GROQ_API_KEY=gsk_...   # free at console.groq.com")
        click.echo("  prg analyze . --ai")
        click.echo("    → Re-run with AI for richer skills")
    click.echo()
    click.echo("  prg skills list    → see available skills")
    click.echo("  prg --help         → full command reference")
