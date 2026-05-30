"""Analyzer module for project rules generator."""

import sys
from contextlib import contextmanager
from pathlib import Path

import click
import yaml
from pydantic import ValidationError

from cli._version import __version__
from cli.analyze_helpers import (  # noqa: E402
    _handle_skill_management,
    commit_generated_files,
    normalize_analyze_options,
    setup_incremental,
    setup_logging_and_provider,
    setup_orchestrator,
)
from cli.analyze_pipeline import run_generation_pipeline
from cli.analyze_readme import resolve_readme
from generator.pack_manager import load_external_packs
from generator.skills.manager import SkillsManager
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


@contextmanager
def _analyze_error_boundary(verbose: bool):
    """Centralised exception dispatch for the ``analyze`` command.

    Catches the well-known user-facing error classes with friendly
    messages + remediation tips, lets ``click.exceptions.Exit``
    propagate (a Click-internal flow-control signal, not a real error),
    and surfaces unexpected errors with a traceback ONLY in verbose
    mode. Every handler translates to ``sys.exit(1)`` so the CLI returns
    a non-zero status without dumping a Python stack to ordinary users.

    Moving the six handlers here drops the cyclomatic complexity of
    ``analyze`` itself by ~6 points; each except is +1 CC. Now ``analyze``
    only sees one ``with`` block.
    """
    try:
        yield
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
    except Exception as e:  # noqa: BLE001 — CLI boundary: friendly catch-all
        if verbose:
            import traceback

            traceback.print_exc()
        click.echo(f"❌ Unexpected Error: {e}", err=True)
        sys.exit(1)


def _apply_save_learned(config: dict, save_learned: bool) -> dict:
    """Toggle ``skill_sources.learned.auto_save`` in the config when
    --save-learned is set. Pure function; mutates and returns config so
    callers can chain or ignore."""
    if not save_learned:
        return config
    if "skill_sources" not in config:
        config["skill_sources"] = {}
    if "learned" not in config["skill_sources"]:
        config["skill_sources"]["learned"] = {}
    config["skill_sources"]["learned"]["auto_save"] = True
    return config


def _maybe_load_external_packs(config: dict, include_pack, external_packs_dir, verbose: bool) -> None:
    """Load external skill packs if either --include-pack was given OR
    config opts into pack loading. No-op otherwise."""
    if not (include_pack or (config.get("packs") and config["packs"].get("enabled"))):
        return
    load_external_packs(
        include_packs=include_pack,
        config_packs=config.get("packs"),
        external_packs_dir=external_packs_dir,
        verbose=verbose,
    )


def _confirm_interactive_or_exit(project_name: str) -> None:
    """When running interactively, prompt before generation and exit 0
    if the user says no. Pure UX helper; isolated so the body function
    doesn't have to import rich at top level."""
    from rich.prompt import Confirm

    from generator.utils import flush_input

    flush_input()
    if not Confirm.ask(
        f"Continue generating .clinerules for [bold]{project_name}[/bold]?",
        default=True,
    ):
        click.echo("Aborted.")
        sys.exit(0)


def _present_generated_files(
    generated_files: list,
    project_path: Path,
    interactive: bool,
) -> None:
    """Show the list of generated files. Interactive mode delegates to the
    rich-backed rendering; otherwise we print one path per line, relative
    to the project root when possible (Bug G)."""
    if interactive:
        from generator.interactive import show_generated_files

        skills_stats = {"learned": 0, "builtin": 0, "generated": 0}
        show_generated_files(generated_files, skills_stats)
        return

    click.echo("\nGenerated files:")
    for f in generated_files:
        try:
            display = Path(f).resolve().relative_to(Path(project_path).resolve()).as_posix()
        except (ValueError, OSError):
            display = str(f)
        click.echo(f"   {display}")


def _save_incremental_hash(inc_analyzer, verbose: bool) -> None:
    """Persist the cached project hash so the next run can skip work.
    Reuses the hash already computed by detect_changes() to avoid a
    second full re-read."""
    if not inc_analyzer:
        return
    inc_analyzer.save_hash(inc_analyzer._current_hash or inc_analyzer.compute_project_hash())
    if verbose:
        click.echo("   Saved incremental cache")


def _run_analysis_body(
    *,
    project_path: Path,
    output_dir: Path,
    skills_manager,
    inc_analyzer,
    commit: bool,
    interactive: bool,
    verbose: bool,
    export_json: bool,
    export_yaml: bool,
    save_learned: bool,
    include_pack,
    external_packs_dir,
    ai: bool,
    with_skills: bool,
    auto_generate_skills: bool,
    constitution: bool,
    merge: bool,
    ide: str,
    provider: str,
    strategy: str,
) -> None:
    """Body of the ``analyze`` command, extracted so the click entrypoint
    stays small and the radon grade for ``analyze`` drops out of the
    danger zone.

    Sequential phases — config, pipeline call, IDE register, output
    presentation, git commit, incremental save. Exceptions propagate to
    the caller; the ``analyze`` orchestrator owns the user-facing
    except-handler dispatch."""
    config = _apply_save_learned(load_config(), save_learned)
    _maybe_load_external_packs(config, include_pack, external_packs_dir, verbose)

    readme_path, project_data, project_name = resolve_readme(project_path, interactive, ai, verbose)

    if interactive:
        _confirm_interactive_or_exit(project_name)

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

    if ide:
        ide_file = _register_ide_rules(ide, project_path, project_name, output_dir, verbose)
        if ide_file:
            generated_files.append(ide_file)

    _present_generated_files(generated_files, project_path, interactive)
    commit_generated_files(commit, config, generated_files, project_path, interactive)
    _save_incremental_hash(inc_analyzer, verbose)
    click.echo("\nDone!")


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
@click.option("--ide", help="Register rules with IDE (antigravity)")
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
@click.option("--create-skill", default=None, help="Create a new skill by name (writes to learned/ by default)")
@click.option("--add-skill", default=None, help="Alias for --create-skill")
@click.option("--remove-skill", default=None, help="Remove a learned skill by name")
@click.option("--list-skills", is_flag=True, help="List all available skills and exit")
@click.option(
    "--from-readme",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Use README as context for --create-skill",
)
@click.option("--force", is_flag=True, default=False, help="Overwrite existing skill when using --create-skill")
@click.option(
    "--scope",
    type=click.Choice(["learned", "builtin", "project"], case_sensitive=False),
    default="learned",
    show_default=True,
    help="Destination for --create-skill (learned=global reusable, builtin=universal, project=local)",
)
@click.option(
    "--create-rules",
    "create_rules_flag",
    is_flag=True,
    default=False,
    help="When used with --create-skill, continue on to rules generation instead of exiting",
)
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
    create_skill,
    add_skill,
    remove_skill,
    list_skills,
    from_readme,
    force,
    scope,
    create_rules_flag,
):
    """Analyze project and generate rules.md and skills.md from README.md

    Supports inline skill management via --create-skill / --remove-skill /
    --list-skills (equivalent to the `prg skills create / remove / list`
    sub-commands). Use --create-rules alongside --create-skill to continue
    on to full rules generation after the skill is created.

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

    # Handle skill management early-exit actions (--create-skill / --remove-skill / --list-skills).
    # Raises click.exceptions.Exit when the action completes and --create-rules was not set.
    if create_skill or add_skill or remove_skill or list_skills:
        _handle_skill_management(
            skills_manager,
            create_skill,
            add_skill,
            from_readme,
            ai,
            provider,
            force,
            strategy,
            output_dir,
            create_rules_flag,
            remove_skill,
            list_skills,
            verbose,
            scope,
        )

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

    with _analyze_error_boundary(verbose):
        _run_analysis_body(
            project_path=project_path,
            output_dir=output_dir,
            skills_manager=skills_manager,
            inc_analyzer=inc_analyzer,
            commit=commit,
            interactive=interactive,
            verbose=verbose,
            export_json=export_json,
            export_yaml=export_yaml,
            save_learned=save_learned,
            include_pack=include_pack,
            external_packs_dir=external_packs_dir,
            ai=ai,
            with_skills=with_skills,
            auto_generate_skills=auto_generate_skills,
            constitution=constitution,
            merge=merge,
            ide=ide,
            provider=provider,
            strategy=strategy,
        )


if __name__ == "__main__":
    analyze()
