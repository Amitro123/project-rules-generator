"""Analyzer module for project rules generator."""

import sys
from pathlib import Path

import click
import yaml
from pydantic import ValidationError

from cli._version import __version__
from cli.analyze_helpers import (  # noqa: E402
    commit_generated_files,
    normalize_analyze_options,
    setup_incremental,
    setup_logging_and_provider,
    setup_orchestrator,
)
from cli.analyze_pipeline import run_generation_pipeline
from cli.analyze_readme import resolve_readme
from generator.pack_manager import load_external_packs
from generator.skills_manager import SkillsManager
from prg_utils.config_schema import validate_config
from prg_utils.exceptions import InvalidREADMEError, ProjectRulesGeneratorError, READMENotFoundError


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    raw_config = {}
    if config_path.exists():
        raw_config = yaml.safe_load(config_path.read_text()) or {}
    config_model = validate_config(raw_config)
    return config_model.model_dump()


def cleanup_awesome_skills():
    """Remove deprecated awesome-skills directory."""
    try:
        import shutil

        awesome_dir = Path.home() / ".project-rules-generator" / "awesome-skills"
        if awesome_dir.exists():
            shutil.rmtree(awesome_dir)
    except OSError:
        pass


def _register_ide_rules(ide: str, project_path: Path, project_name: str, output_dir: Path, verbose: bool):
    """Write generated rules to IDE-specific location. Returns the written Path or None."""
    ide = ide.lower().strip()
    if ide == "antigravity":
        rules_src = output_dir / "rules.md"
        if not rules_src.exists():
            if verbose:
                click.echo(f"⚠️  IDE registration skipped: {rules_src} not found")
            return None
        agents_dir = project_path / ".agents" / "rules"
        agents_dir.mkdir(parents=True, exist_ok=True)
        dest = agents_dir / f"{project_name}.md"
        dest.write_text(rules_src.read_text(encoding="utf-8"), encoding="utf-8")
        click.echo(f"   Antigravity rules → {dest.relative_to(project_path)}")
        return dest
    else:
        if verbose:
            click.echo(f"⚠️  IDE '{ide}' not yet supported (supported: antigravity)")
        return None


@click.command(name="analyze")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--commit/--no-commit", default=True, help="Auto-commit to git")
@click.option("--interactive", "-i", is_flag=True, help="Interactive prompts")
@click.option("--verbose/--quiet", default=False, help="Verbose output (version banner, provider info)")
@click.option("--export-json", is_flag=True, help="Export skills as JSON")
@click.option("--export-yaml", is_flag=True, help="Export skills as YAML")
@click.option("--save-learned", is_flag=True, help="Save newly generated skills to learned library")
@click.option("--include-pack", multiple=True, help="Include external skill pack (name or path)")
@click.option(
    "--external-packs-dir",
    type=click.Path(exists=True, file_okay=False),
    help="Directory containing external packs",
)
@click.option("--ai", is_flag=True, help="Use AI to generate skill content (requires an API key)")
@click.option(
    "--output",
    type=click.Path(file_okay=False),
    default=".clinerules",
    help="Output directory (default: .clinerules)",
)
@click.option("--with-skills", is_flag=True, default=True, help="Include skills in output")
@click.option("--auto-generate-skills", is_flag=True, help="Auto-detect and generate skills (requires --ai)")
@click.option("--api-key", help="API Key (overrides env var)")
@click.option("--constitution", is_flag=True, help="Generate constitution.md with project-specific coding principles")
@click.option("--merge", is_flag=True, help="Preserve existing skill files, only add new ones")
@click.option(
    "--mode",
    type=click.Choice(["manual", "ai", "constitution"]),
    default=None,
    help="Explicit mode (manual=no AI, ai=auto-generate+AI, constitution=adds constitution.md)",
)
@click.option("--incremental", is_flag=True, help="Only regenerate changed sections (skip if nothing changed)")
@click.option("--ide", help="Register rules with IDE (antigravity, cline, cursor, vscode)")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider. Auto-detected from env vars if omitted.",
)
@click.option(
    "--strategy",
    default="auto",
    show_default=True,
    help="Router strategy: auto (smart fallback), speed, quality, or provider:<name>",
)
@click.option("--skills-dir", type=click.Path(file_okay=False), help="Custom skills directory (default: ./skills)")
def analyze(
    project_path,
    commit,
    interactive,
    verbose,
    export_json,
    export_yaml,
    save_learned,
    include_pack,
    external_packs_dir,
    ai,
    output,
    with_skills,
    auto_generate_skills,
    api_key,
    constitution,
    merge,
    mode,
    incremental,
    ide,
    provider,
    skills_dir,
    strategy,
):
    """Analyze project and generate rules.md and skills.md from README.md

    For skill management use: prg skills create / remove / list / index
    For quality analysis use:  prg quality .
    For rules creation use:    prg create-rules .
    """
    project_path = Path(project_path).resolve()
    cleanup_awesome_skills()

    skills_manager = SkillsManager(project_path=project_path, skills_dir=skills_dir)

    # Resolve mode shortcuts and provider-implied flags
    auto_generate_skills, ai, constitution = normalize_analyze_options(
        mode, provider, auto_generate_skills, ai, constitution
    )

    # Create output directory
    output_dir = project_path / output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Skills structure setup
    try:
        skills_manager.setup_project_structure()
        if verbose:
            click.echo("✅ Skills structure initialized (Global -> Project)")
    except Exception as e:  # noqa: BLE001
        if verbose:
            click.echo(f"⚠️  Skills structure setup warning: {e}")

    # Incremental mode: check for changes before heavy work (exits if nothing changed)
    inc_analyzer = setup_incremental(incremental, project_path, output_dir)
    if inc_analyzer and verbose:
        # detect_changes() is cached — no re-read cost
        click.echo(f"Incremental: changed sections: {', '.join(sorted(inc_analyzer.detect_changes()))}")

    if verbose:
        click.echo(f"Target: {project_path}")
    provider = setup_logging_and_provider(verbose, provider, api_key, __version__)

    try:
        config = load_config()
        if save_learned:
            if "skill_sources" not in config:
                config["skill_sources"] = {}
            if "learned" not in config["skill_sources"]:
                config["skill_sources"]["learned"] = {}
            config["skill_sources"]["learned"]["auto_save"] = True

        if include_pack or (config.get("packs") and config["packs"].get("enabled")):
            load_external_packs(
                include_packs=include_pack,
                config_packs=config.get("packs"),
                external_packs_dir=external_packs_dir,
                verbose=verbose,
            )

        readme_path, project_data, project_name = resolve_readme(project_path, interactive, ai, verbose)

        # Interactive confirmation before generation
        if interactive:
            from rich.prompt import Confirm

            from generator.utils import flush_input

            flush_input()
            if not Confirm.ask(
                f"Continue generating .clinerules for [bold]{project_name}[/bold]?",
                default=True,
            ):
                click.echo("Aborted.")
                sys.exit(0)

        generated_files = run_generation_pipeline(
            project_path=project_path,
            project_name=project_name,
            project_data=project_data,
            readme_path=readme_path,
            config=config,
            provider=provider,
            skills_manager=skills_manager,
            output_dir=output_dir,
            verbose=verbose,
            ai=ai,
            auto_generate_skills=auto_generate_skills,
            constitution=constitution,
            with_skills=with_skills,
            merge=merge,
            save_learned=save_learned,
            export_json=export_json,
            export_yaml=export_yaml,
            inc_analyzer=inc_analyzer,
            strategy=strategy,
        )

        # IDE registration — write rules to IDE-specific location
        if ide:
            ide_file = _register_ide_rules(ide, project_path, project_name, output_dir, verbose)
            if ide_file:
                generated_files.append(str(ide_file))

        if interactive:
            from generator.interactive import show_generated_files

            skills_stats = {"learned": 0, "builtin": 0, "generated": 0}
            # skills list is inside orchestration; best-effort count from generated_files
            show_generated_files(generated_files, skills_stats)
        else:
            click.echo("\nGenerated files:")
            for f in generated_files:
                click.echo(f"   {f}")

        # Git commit
        commit_generated_files(commit, config, generated_files, project_path, interactive)

        if inc_analyzer:
            # Reuse the hash already computed by detect_changes(); avoids a second full re-read
            inc_analyzer.save_hash(inc_analyzer._current_hash or inc_analyzer.compute_project_hash())
            if verbose:
                click.echo("   Saved incremental cache")

        click.echo("\nDone!")

    except READMENotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        click.echo("💡 Tip: Make sure README.md exists in the project root.")
        sys.exit(1)

    except InvalidREADMEError as e:
        click.echo(f"❌ Error: {e}", err=True)
        click.echo("💡 Tip: README should have at least a title and description.")
        sys.exit(1)

    except ValidationError as e:
        click.echo(f"❌ Configuration Error: {e}", err=True)
        sys.exit(1)

    except ProjectRulesGeneratorError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

    except click.exceptions.Exit:
        raise

    except Exception as e:
        if verbose:
            import traceback

            traceback.print_exc()
        click.echo(f"❌ Unexpected Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    analyze()
