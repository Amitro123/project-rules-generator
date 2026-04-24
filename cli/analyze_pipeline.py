"""Generation pipeline for the analyze command.

Runs the main artifact generation loop: enhanced parsing, constitution,
rules, skills auto-generation, export, and skill copying.
Extracted from analyze_cmd.py to keep each module focused.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import click

from generator.constitution_generator import generate_constitution
from generator.incremental_analyzer import IncrementalAnalyzer
from generator.outputs.clinerules_generator import generate_clinerules
from generator.parsers.enhanced_parser import EnhancedProjectParser
from generator.rules_generator import generate_rules, rules_to_json
from generator.skills.enhanced_skill_matcher import EnhancedSkillMatcher
from generator.storage.skill_paths import SkillPathManager
from prg_utils.file_ops import save_markdown


@dataclass
class PipelineConfig:
    """Boolean/string flags that control pipeline behaviour.

    Grouping these reduces run_generation_pipeline's parameter count from 17 to 11
    and gives callers a single object to inspect/override in tests.
    """

    ai: bool = False
    auto_generate_skills: bool = False
    constitution: bool = False
    with_skills: bool = True
    merge: bool = False
    save_learned: bool = False
    export_json: bool = False
    export_yaml: bool = False
    strategy: str = "auto"


try:
    from tqdm import tqdm
except ImportError:

    class tqdm:  # type: ignore[no-redef]
        def __init__(self, iterable=None, *args, **kwargs):
            self.iterable = iterable or []

        def __iter__(self):
            return iter(self.iterable)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def update(self, *args):
            pass

        def set_description(self, *args):
            pass


def run_generation_pipeline(
    project_path: Path,
    project_name: str,
    project_data: Dict[str, Any],
    readme_path: Optional[Path],
    config: Dict[str, Any],
    provider: str,
    skills_manager: Any,
    output_dir: Path,
    verbose: bool,
    inc_analyzer: Any,
    # Flat kwargs kept for backward-compat; prefer passing pipeline_cfg instead.
    pipeline_cfg: Optional[PipelineConfig] = None,
    ai: bool = False,
    auto_generate_skills: bool = False,
    constitution: bool = False,
    with_skills: bool = True,
    merge: bool = False,
    save_learned: bool = False,
    export_json: bool = False,
    export_yaml: bool = False,
    strategy: str = "auto",
) -> List[Path]:
    """Run the full artifact generation pipeline.

    Accepts either a PipelineConfig object (preferred) or the individual boolean/string
    kwargs (kept for backward-compat). When both are supplied, pipeline_cfg wins.

    Returns:
        List of generated file paths.
    """
    if pipeline_cfg is not None:
        ai = pipeline_cfg.ai
        auto_generate_skills = pipeline_cfg.auto_generate_skills
        constitution = pipeline_cfg.constitution
        with_skills = pipeline_cfg.with_skills
        merge = pipeline_cfg.merge
        save_learned = pipeline_cfg.save_learned
        export_json = pipeline_cfg.export_json
        export_yaml = pipeline_cfg.export_yaml
        strategy = pipeline_cfg.strategy

    if verbose:
        click.echo("\nGenerating files...")

    generated_files: List[Path] = []

    # Resolve which phases need to run (all True when not incremental)
    _run_enhanced = _run_rules = _run_constitution = _run_skills_gen = True
    if inc_analyzer:
        _run_enhanced, _run_rules, _run_constitution, _run_skills_gen = inc_analyzer.phases_to_run()
        if verbose:
            skipped = [
                n
                for n, flag in [
                    ("enhanced-parse", _run_enhanced),
                    ("rules", _run_rules),
                    ("constitution", _run_constitution),
                    ("skills-gen", _run_skills_gen),
                ]
                if not flag
            ]
            if skipped:
                click.echo(f"   Incremental: skipping unchanged phases: {', '.join(skipped)}")

    with tqdm(total=4, disable=not verbose, desc="Build") as pbar:
        pbar.set_description("Analyzing Project")
        enhanced_context = _phase_enhanced_parse(project_path, _run_enhanced, verbose)
        pbar.update(1)

        _phase_constitution(
            project_name,
            enhanced_context,
            output_dir,
            project_path,
            verbose,
            constitution,
            _run_constitution,
            generated_files,
        )

        pbar.set_description("Generating Rules")
        rules_content = _phase_rules(
            project_data,
            config,
            enhanced_context,
            output_dir,
            verbose,
            _run_rules,
        )
        pbar.update(1)

        pbar.set_description("Processing Skills")
        enhanced_selected_skills = _phase_skills(
            project_path,
            project_name,
            enhanced_context,
            provider,
            ai,
            verbose,
            skills_manager,
            strategy,
            auto_generate_skills,
            _run_skills_gen,
            output_dir,
        )
        pbar.update(1)

        pbar.set_description("Unified Export (.clinerules/)")
        unified_content = _build_unified_content(
            rules_content=rules_content,
            triggers_dict=skills_manager.extract_project_triggers(
                include_only=enhanced_selected_skills
            )
            if with_skills
            else {},
            skills_manager=skills_manager,
            enhanced_selected_skills=enhanced_selected_skills,
            project_name=project_name,
            project_data=project_data,
            readme_path=readme_path,
            output_dir=output_dir,
            merge=merge,
            verbose=verbose,
            generated_files=generated_files,
            enhanced_context=enhanced_context,
            use_ai=ai,
            provider=provider,
        )

        _phase_write_rules(unified_content, output_dir, inc_analyzer, verbose, generated_files, skills_manager)
        pbar.update(1)

        pbar.set_description("Saving Skill Artifacts")
        _run_skill_orchestration(
            config=config,
            project_data=project_data,
            project_name=project_name,
            project_path=project_path,
            save_learned=save_learned,
            export_json=export_json,
            export_yaml=export_yaml,
            output_dir=output_dir,
            generated_files=generated_files,
        )

    return generated_files


# ---------------------------------------------------------------------------
# Phase helpers — each does exactly one pipeline phase
# ---------------------------------------------------------------------------


def _phase_enhanced_parse(
    project_path: Path,
    run_enhanced: bool,
    verbose: bool,
) -> Optional[Dict[str, Any]]:
    """Phase 1: parse the project with EnhancedProjectParser.

    Returns the context dict on success, None if skipped (incremental) or if
    parsing fails on bad input.  Programming errors (AttributeError, TypeError)
    are intentionally *not* caught here — they should surface so they get fixed.
    """
    if not run_enhanced:
        if verbose:
            click.echo("   Incremental: skipped enhanced parse (source/structure unchanged)")
        return None
    try:
        return EnhancedProjectParser(project_path).extract_full_context()
    except (OSError, ValueError, RuntimeError) as e:
        click.echo(f"⚠️  Enhanced analysis failed (generation will continue with reduced context): {e}", err=True)
        return None


def _phase_constitution(
    project_name: str,
    enhanced_context: Optional[Dict[str, Any]],
    output_dir: Path,
    project_path: Path,
    verbose: bool,
    constitution: bool,
    run_constitution: bool,
    generated_files: List[Path],
) -> None:
    """Phase 2: optionally generate constitution.md.

    Appends to generated_files if written.
    """
    if not constitution:
        return
    if not run_constitution:
        if verbose:
            click.echo("   Incremental: skipped constitution (README unchanged)")
        return
    if not enhanced_context:
        if verbose:
            click.echo("   Skipping constitution (enhanced analysis unavailable)")
        return
    content = generate_constitution(project_name, enhanced_context, project_path=project_path)
    path = output_dir / "constitution.md"
    path.write_text(content, encoding="utf-8")
    generated_files.append(path)
    if verbose:
        click.echo("   Generated constitution.md")


def _phase_rules(
    project_data: Dict[str, Any],
    config: Dict[str, Any],
    enhanced_context: Optional[Dict[str, Any]],
    output_dir: Path,
    verbose: bool,
    run_rules: bool,
) -> str:
    """Phase 3: produce rules content string.

    When skipped, returns cached rules.md content (or regenerates if no cache exists).
    """
    if run_rules:
        return generate_rules(project_data, config, enhanced_context=enhanced_context)
    existing = output_dir / "rules.md"
    if existing.exists():
        if verbose:
            click.echo("   Incremental: skipped rules regen (README/deps unchanged) — using cached rules.md")
        return existing.read_text(encoding="utf-8")
    return generate_rules(project_data, config, enhanced_context=enhanced_context)


def _phase_skills(
    project_path: Path,
    project_name: str,
    enhanced_context: Optional[Dict[str, Any]],
    provider: str,
    ai: bool,
    verbose: bool,
    skills_manager: Any,
    strategy: str,
    auto_generate_skills: bool,
    run_skills_gen: bool,
    output_dir: Optional[Path] = None,
) -> Set[str]:
    """Phase 4: optionally auto-generate skills.

    Returns the set of selected skill names (empty when skipped or disabled).
    Trigger JSON is written by _phase_write_rules (once, after content is assembled).
    """
    if not auto_generate_skills:
        return set()
    if not run_skills_gen:
        if verbose:
            click.echo("   Incremental: skipped skills auto-gen (source/README unchanged)")
        return set()
    return _auto_generate_skills(
        project_path=project_path,
        project_name=project_name,
        enhanced_context=enhanced_context,
        provider=provider,
        ai=ai,
        verbose=verbose,
        skills_manager=skills_manager,
        strategy=strategy,
        output_dir=output_dir,
    )


def _phase_write_rules(
    unified_content: str,
    output_dir: Path,
    inc_analyzer: Any,
    verbose: bool,
    generated_files: List[Path],
    skills_manager: Any,
) -> None:
    """Phase 6: write rules.md and rules.json; merge incrementally when appropriate.

    Appends both files to generated_files.
    """
    rules_path = output_dir / "rules.md"
    if inc_analyzer and rules_path.exists():
        changed_sections = inc_analyzer.detect_changes()  # cached — no re-read
        existing_rules = rules_path.read_text(encoding="utf-8")
        unified_content = IncrementalAnalyzer.merge_rules(existing_rules, unified_content, changed_sections)
        if verbose:
            click.echo(f"   Incremental: merged changes from {', '.join(sorted(changed_sections))}")
    save_markdown(rules_path, unified_content, backup=True)
    generated_files.append(rules_path)

    rules_json_path = output_dir / "rules.json"
    from prg_utils.file_ops import atomic_write_text

    atomic_write_text(rules_json_path, rules_to_json(unified_content), backup=True)
    if verbose:
        click.echo("Generating auto-triggers...")
    skills_manager.save_triggers_json(output_dir)
    generated_files.append(rules_json_path)
    if verbose:
        click.echo("   Generated rules.json")


def _build_unified_content(
    rules_content: str,
    triggers_dict: Dict[str, Any],
    skills_manager: Any,
    enhanced_selected_skills: Set[str],
    project_name: str,
    project_data: Dict[str, Any],
    readme_path: Optional[Path],
    output_dir: Path,
    merge: bool,
    verbose: bool,
    generated_files: List[Path],
    enhanced_context: Optional[Dict[str, Any]] = None,
    use_ai: bool = False,
    provider: str = "groq",
) -> str:
    """Assemble the unified rules + skills content string."""
    unified_content = rules_content + "\n\n# 🧠 Agent Skills\n\n"

    if triggers_dict:
        unified_content += "## Active Skill Triggers\n"
        for skill, phrases in triggers_dict.items():
            unified_content += f"- **{skill}**: {', '.join(phrases)}\n"
        unified_content += "\n"

    if enhanced_selected_skills:
        lightweight_yaml = generate_clinerules(
            project_name,
            enhanced_selected_skills,
            enhanced_context,
            output_dir=output_dir,
        )
        unified_content += f"\n\n<!-- Lightweight Skill References\n{lightweight_yaml}-->\n"

        lightweight_path = output_dir / "clinerules.yaml"
        lightweight_path.write_text(lightweight_yaml, encoding="utf-8")
        generated_files.append(lightweight_path)
        if verbose:
            click.echo(f"   Generated clinerules.yaml ({len(enhanced_selected_skills)} skills)")

        # Generate project-specific skills from README
        if readme_path and readme_path.exists():
            readme_text = readme_path.read_text(encoding="utf-8", errors="replace")
            project_tech = project_data.get("tech_stack", [])

            if verbose:
                reuse_map = skills_manager.check_global_skill_reuse(project_tech)
                if reuse_map:
                    click.echo("\n   Global skill reuse check:")
                    for skill_name, action in sorted(reuse_map.items()):
                        icon = {"reuse": "♻️ ", "adapt": "🔧", "create": "✨"}.get(action, "  ")
                        click.echo(f"     {icon} {skill_name}: {action}")

            generated_skills = skills_manager.generate_from_readme(
                readme_content=readme_text,
                tech_stack=project_tech,
                output_dir=output_dir,
                project_name=project_name,
                project_path=skills_manager.project_path,
                use_ai=use_ai,
                provider=provider,
            )
            if generated_skills and verbose:
                click.echo(f"   Generated {len(generated_skills)} project-specific skills:")
                for s in generated_skills:
                    click.echo(f"     - {s}")

        # Copy skill files into output_dir/skills/
        _copy_skill_files(
            enhanced_selected_skills=enhanced_selected_skills,
            output_dir=output_dir,
            merge=merge,
            readme_path=readme_path,
            project_name=project_name,
            skills_manager=skills_manager,
            verbose=verbose,
        )

    return unified_content


# Backward-compat re-exports — import from skill_pipeline directly for new code
from cli.skill_pipeline import (  # noqa: F401, E402
    _auto_generate_skills,
    _copy_skill_files,
    _llm_generate_skills,
    _run_skill_orchestration,
    _write_skill_stub,
)
