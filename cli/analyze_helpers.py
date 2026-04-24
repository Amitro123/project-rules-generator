"""Extracted helper functions for analyze_cmd.py to reduce module complexity."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import click


def normalize_analyze_options(
    mode: Optional[str],
    provider: Optional[str],
    auto_generate_skills: bool,
    ai: bool,
    constitution: bool,
) -> Tuple[bool, bool, bool]:
    """Resolve --mode shortcuts and provider-implied feature flags.

    Returns:
        (auto_generate_skills, ai, constitution) after applying mode and provider rules.
    """
    if mode == "ai":
        auto_generate_skills = True
        ai = True
    elif mode == "constitution":
        constitution = True
    # mode == 'manual' changes nothing (no AI)

    # Explicit --provider implies AI intent unless mode is manual
    if provider is not None and mode != "manual":
        auto_generate_skills = True
        ai = True
        constitution = True

    # Bug A fix: `--ai` (from any source — explicit flag, --mode ai, or --provider)
    # must trigger project skill generation. Previously `auto_generate_skills`
    # stayed False when `--ai` was passed without an explicit `--provider`,
    # causing the project skills dir to remain empty after analysis.
    if ai and mode != "manual":
        auto_generate_skills = True

    return auto_generate_skills, ai, constitution


def _handle_skill_management(
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
):
    """Handle create-skill / remove-skill / list-skills early-exit actions.

    Raises click.exceptions.Exit on completion or error — never calls sys.exit() directly.
    """
    import shutil

    if create_skill or add_skill:
        skill_name = create_skill or add_skill
        try:
            path = skills_manager.create_skill(
                skill_name,
                from_readme=from_readme,
                project_path=str(skills_manager.project_path),
                use_ai=ai,
                provider=provider or "groq",
                force=force,
                strategy=strategy if ai else None,
                scope=scope,
            )
            click.echo(f"\u2728 Created new skill '{path.name}' in {path}")
            click.echo("\U0001f504 Updating agent cache...")
            skills_manager.save_triggers_json(output_dir)
            click.echo("\u2705 auto-triggers.json refreshed!")
        except Exception as e:  # noqa: BLE001 — CLI boundary: catch all errors to show user-friendly message
            click.echo(f"\u274c Failed to create skill: {e}", err=True)
            raise click.exceptions.Exit(1)
        if not create_rules_flag:
            raise click.exceptions.Exit(0)

    if remove_skill:
        target = (skills_manager.learned_path / remove_skill).resolve()
        try:
            target.relative_to(skills_manager.learned_path.resolve())
        except ValueError:
            click.echo(f"\u274c Invalid skill path: {remove_skill}", err=True)
            raise click.exceptions.Exit(1)
        if not target.exists():
            click.echo(f"\u274c Skill '{remove_skill}' not found in learned skills.", err=True)
            raise click.exceptions.Exit(1)
        shutil.rmtree(target)
        click.echo(f"\U0001f5d1\ufe0f Removed skill '{remove_skill}'")
        # Refresh derived artifacts so removed skill doesn't linger in index/triggers.
        try:
            skills_manager.generate_perfect_index()
            click.echo("\U0001f504 index.md refreshed")
        except Exception as exc:  # noqa: BLE001 — non-fatal
            click.echo(f"\u26a0\ufe0f  Could not refresh index.md: {exc}", err=True)
        try:
            skills_manager.save_triggers_json(output_dir)
            click.echo("\u2705 auto-triggers.json refreshed")
        except Exception as exc:  # noqa: BLE001 — non-fatal
            click.echo(f"\u26a0\ufe0f  Could not refresh auto-triggers.json: {exc}", err=True)
        raise click.exceptions.Exit(0)

    if list_skills:
        skills = skills_manager.list_skills()
        display_groups = {"project": [], "learned": [], "builtin": []}
        for name, data in skills.items():
            stype = data["type"]
            if stype in display_groups:
                display_groups[stype].append(name)
        total = len(skills)
        click.echo(f"\nAvailable Skills ({total}):")
        if display_groups["project"]:
            click.echo(f"\n\U0001f4c1 Project Overrides ({len(display_groups['project'])}):")
            for s in sorted(display_groups["project"]):
                click.echo(f"  - {s} (Local)")
        if display_groups["learned"]:
            click.echo(f"\n\U0001f9e0 Learned Skills (Global & Local) ({len(display_groups['learned'])}):")
            for s in sorted(display_groups["learned"]):
                click.echo(f"  - {s}")
        if display_groups["builtin"]:
            click.echo(f"\n\U0001f6e0\ufe0f  Global Builtin ({len(display_groups['builtin'])}):")
            for s in sorted(display_groups["builtin"]):
                click.echo(f"  - {s}")
        if not total:
            click.echo("  No skills found.")
        raise click.exceptions.Exit(0)


def _run_create_rules(
    project_path,
    readme_path,
    project_name,
    project_data,
    enhanced_context,
    output_dir,
    rules_quality_threshold,
    verbose,
    generated_files,
):
    """Run the --create-rules CoworkRulesCreator block."""
    try:
        from generator.rules_creator import CoworkRulesCreator

        if verbose:
            click.echo("\n\U0001f3af Cowork Rules Creator...")

        if readme_path and readme_path.exists():
            readme_text = readme_path.read_text(encoding="utf-8", errors="replace")
        else:
            readme_text = f"# {project_name}\n\nProject analysis in progress..."

        tech_stack_arg = project_data.get("tech_stack") or None
        creator = CoworkRulesCreator(project_path)
        content, metadata, quality = creator.create_rules(
            readme_text,
            tech_stack=tech_stack_arg,
            enhanced_context=enhanced_context,
        )

        if verbose:
            click.echo(f"   Tech Stack: {', '.join(metadata.tech_stack) or 'none'}")
            click.echo(f"   Project Type: {metadata.project_type}")
            click.echo(f"   Quality Score: {quality.score:.1f}/100")

        if quality.score < rules_quality_threshold:
            click.echo(
                f"   \u26a0\ufe0f  Quality score {quality.score:.1f} below threshold {rules_quality_threshold}",
                err=True,
            )

        cowork_rules_file = creator.export_to_file(content, metadata, output_dir)
        generated_files.append(cowork_rules_file)
        if verbose:
            click.echo(f"   \u2705 Cowork rules.md saved: {cowork_rules_file}")
    except Exception as e:  # noqa: BLE001 — CLI boundary: catch all errors to show user-friendly message
        click.echo(f"   \u26a0\ufe0f  Cowork rules generation failed: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()


def setup_orchestrator(config):
    """Initialize and configure SkillOrchestrator."""
    from generator.orchestrator import SkillOrchestrator
    from generator.sources.builtin import BuiltinSkillsSource
    from generator.sources.learned import LearnedSkillsSource

    orchestrator = SkillOrchestrator(config)
    orchestrator.register_source(BuiltinSkillsSource(config))
    orchestrator.register_source(LearnedSkillsSource(config))
    return orchestrator


def setup_logging_and_provider(verbose: bool, provider: Optional[str], api_key: Optional[str], version: str) -> str:
    """Configure logging, print version banner, detect and configure provider.

    Returns the resolved provider name.
    """
    from cli.utils import detect_provider, set_api_key_env
    from prg_utils.logger import setup_logging

    if verbose:
        setup_logging(verbose=True)
        click.echo(f"Project Rules Generator v{version}")
    else:
        setup_logging(verbose=False)

    resolved: str = detect_provider(provider, api_key) or ""
    if verbose:
        click.echo(f"Auto-detected provider: {resolved}")
    set_api_key_env(resolved, api_key)
    if api_key and verbose:
        click.echo(f"Using API key from --api-key flag for {resolved}")
    return resolved


def setup_incremental(incremental: bool, project_path: Path, output_dir: Path) -> Any:
    """Create IncrementalAnalyzer and perform early-exit if nothing changed.

    Returns the analyzer instance (or None when --incremental is not set).
    Calls sys.exit(0) when no changes are detected.
    """
    from generator.incremental_analyzer import IncrementalAnalyzer

    if not incremental:
        return None

    inc_analyzer = IncrementalAnalyzer(project_path, output_dir)
    changed_sections = inc_analyzer.detect_changes()
    if not changed_sections:
        click.echo("No changes detected. Skipping regeneration. (use without --incremental to force)")
        sys.exit(0)
    return inc_analyzer


def commit_generated_files(
    commit: bool,
    config: Dict[str, Any],
    generated_files: Sequence[Union[str, Path]],
    project_path: Path,
    interactive: bool,
) -> None:
    """Commit generated files to git when --commit is set and repo exists."""
    from prg_utils.git_ops import commit_files, is_git_repo

    if not commit:
        return
    if not is_git_repo(project_path):
        if not interactive:
            click.echo("\nWARNING: Not a git repository, skipping commit")
        return

    commit_msg = config.get("git", {}).get("commit_message", "Auto-generated rules and skills")
    user_name = config.get("git", {}).get("commit_user_name")
    user_email = config.get("git", {}).get("commit_user_email")
    try:
        result = commit_files(generated_files, commit_msg, project_path, user_name, user_email)
        click.echo("\nCommitted to git")
        if "nothing to commit" in result.lower():
            click.echo("   (or files already tracked)")
    except Exception as e:  # noqa: BLE001 — CLI boundary: git commit can fail in many ways
        click.echo(f"\nWARNING: Git commit failed: {e}")
        click.echo("   Files were generated, you can commit manually")
