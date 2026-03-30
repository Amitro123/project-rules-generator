"""Analyzer module for project rules generator."""

import sys
from pathlib import Path

import click
import yaml
from pydantic import ValidationError

from cli._version import __version__
from cli.analyze_helpers import (  # noqa: E402
    _handle_skill_management,
    _run_create_rules,
    normalize_analyze_options,
    setup_orchestrator,
)
from cli.analyze_pipeline import run_generation_pipeline
from cli.analyze_quality import run_quality_check
from cli.analyze_readme import resolve_readme
from cli.utils import detect_provider, set_api_key_env
from generator.pack_manager import load_external_packs
from generator.skills_manager import SkillsManager
from prg_utils.config_schema import validate_config
from prg_utils.exceptions import InvalidREADMEError, ProjectRulesGeneratorError, READMENotFoundError
from prg_utils.git_ops import commit_files, is_git_repo
from prg_utils.logger import setup_logging


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
@click.option("--list-skills", is_flag=True, help="List all available skills from all sources")
@click.option("--create-skill", help="Create a new skill with the given name")
@click.option(
    "--scope",
    type=click.Choice(["learned", "builtin", "project"], case_sensitive=False),
    default="learned",
    show_default=True,
    help="Where to write the skill: learned (default, global reusable), builtin (universal patterns), project (this project only)",
)
@click.option("--from-readme", type=click.Path(exists=True, dir_okay=False), help="Use README as context for new skill")
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
@click.option("--add-skill", help="Add a skill (alias for create-skill)")
@click.option("--force", is_flag=True, default=False, help="Force overwrite if skill already exists")
@click.option("--remove-skill", help="Remove a learned skill")
@click.option("--quality-check", is_flag=True, help="Analyze quality of generated .clinerules files")
@click.option("--eval-opik", is_flag=True, help="Run Comet Opik evaluation (requires OPIK_API_KEY)")
@click.option("--auto-fix", is_flag=True, help="Automatically fix low-quality files (requires --quality-check)")
@click.option("--max-iterations", type=int, default=3, help="Max improvement iterations for auto-fix (default: 3)")
@click.option("--generate-index", is_flag=True, help="Auto-generate skills/index.md from available skills")
@click.option(
    "--create-rules",
    "create_rules_flag",
    is_flag=True,
    help="Generate Cowork-quality rules.md (overrides default rules generation)",
)
@click.option("--rules-quality-threshold", type=int, default=85, help="Minimum quality score for --create-rules")
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
    list_skills,
    create_skill,
    from_readme,
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
    add_skill,
    force,
    remove_skill,
    quality_check,
    eval_opik,
    auto_fix,
    max_iterations,
    generate_index,
    create_rules_flag,
    rules_quality_threshold,
    skills_dir,
    strategy,
    scope,
):
    """Analyze project and generate rules.md and skills.md from README.md"""
    project_path = Path(project_path).resolve()
    cleanup_awesome_skills()

    skills_manager = SkillsManager(project_path=project_path, skills_dir=skills_dir)

    # Early-exit: generate index only
    if generate_index:
        try:
            index_path = skills_manager.generate_perfect_index()
            click.echo(f"✅ Perfect index.md generated at: {index_path}")
            sys.exit(0)
        except Exception as e:
            click.echo(f"❌ Failed to generate index.md: {e}", err=True)
            sys.exit(1)

    # Resolve mode shortcuts and provider-implied flags
    auto_generate_skills, ai, constitution = normalize_analyze_options(mode, provider, auto_generate_skills, ai, constitution)

    # Create output directory
    output_dir = project_path / output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Skills structure setup
    try:
        skills_manager.setup_project_structure()
        if verbose:
            click.echo("✅ Skills structure initialized (Global -> Project)")
    except Exception as e:
        if verbose:
            click.echo(f"⚠️  Skills structure setup warning: {e}")

    # Incremental mode: check for changes before heavy work
    from generator.incremental_analyzer import IncrementalAnalyzer

    inc_analyzer = IncrementalAnalyzer(project_path, output_dir) if incremental else None
    if inc_analyzer:
        changed_sections = inc_analyzer.detect_changes()
        if not changed_sections:
            click.echo("No changes detected. Skipping regeneration. (use without --incremental to force)")
            sys.exit(0)
        if verbose:
            click.echo(f"Incremental: changed sections: {', '.join(sorted(changed_sections))}")

    if verbose:
        setup_logging(verbose=True)
        click.echo(f"Project Rules Generator v{__version__}")
        click.echo(f"Target: {project_path}")
    else:
        setup_logging(verbose=False)

    provider = detect_provider(provider, api_key)
    if verbose:
        click.echo(f"Auto-detected provider: {provider}")
    set_api_key_env(provider, api_key)
    if api_key and verbose:
        click.echo(f"Using API key from --api-key flag for {provider}")

    try:
        config = load_config()
        if save_learned:
            if "skill_sources" not in config:
                config["skill_sources"] = {}
            if "learned" not in config["skill_sources"]:
                config["skill_sources"]["learned"] = {}
            config["skill_sources"]["learned"]["auto_save"] = True

        _handle_skill_management(
            skills_manager=skills_manager,
            create_skill=create_skill,
            add_skill=add_skill,
            from_readme=from_readme,
            ai=ai,
            provider=provider,
            force=force,
            strategy=strategy,
            output_dir=output_dir,
            create_rules_flag=create_rules_flag,
            remove_skill=remove_skill,
            list_skills=list_skills,
            verbose=verbose,
            scope=scope,
        )

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
        if commit:
            if not is_git_repo(project_path):
                if not interactive:
                    click.echo("\nWARNING: Not a git repository, skipping commit")
            else:
                commit_msg = config.get("git", {}).get("commit_message", "Auto-generated rules and skills")
                user_name = config.get("git", {}).get("commit_user_name")
                user_email = config.get("git", {}).get("commit_user_email")
                try:
                    result = commit_files(generated_files, commit_msg, project_path, user_name, user_email)
                    click.echo("\nCommitted to git")
                    if "nothing to commit" in result.lower():
                        click.echo("   (or files already tracked)")
                except Exception as e:
                    click.echo(f"\nWARNING: Git commit failed: {e}")
                    click.echo("   Files were generated, you can commit manually")

        if inc_analyzer:
            inc_analyzer.save_hash(inc_analyzer.compute_project_hash())
            if verbose:
                click.echo("   Saved incremental cache")

        if quality_check or eval_opik:
            run_quality_check(
                output_dir=output_dir,
                project_path=project_path,
                provider=provider,
                api_key=api_key,
                eval_opik=eval_opik,
                auto_fix=auto_fix,
                verbose=verbose,
            )

        if create_rules_flag:
            _run_create_rules(
                project_path=project_path,
                readme_path=readme_path,
                project_name=project_name,
                project_data=project_data,
                enhanced_context=None,
                output_dir=output_dir,
                rules_quality_threshold=rules_quality_threshold,
                verbose=verbose,
                generated_files=generated_files,
            )

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

    except Exception as e:
        if verbose:
            import traceback

            traceback.print_exc()
        click.echo(f"❌ Unexpected Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    analyze()
