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
from generator.skill_constants import SKILL_FILENAME, SkillScope
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

        # Sync project_data tech_stack with the enhanced parser result.
        # resolve_readme() uses a README-only detector that can include noisy tokens
        # (e.g. "gpt" from prose, "jest" from Python test files).  The enhanced
        # parser runs a richer, filtered pipeline and is the authoritative source;
        # overwriting here ensures rules.md and clinerules.yaml stay consistent.
        if enhanced_context:
            _meta = enhanced_context.get("metadata", {})
            _meta_tech = _meta.get("tech_stack", [])
            if _meta_tech:
                project_data["tech_stack"] = _meta_tech
            _meta_type = _meta.get("project_type", "")
            if _meta_type:
                project_data["project_type"] = _meta_type

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
            triggers_dict=(
                skills_manager.extract_project_triggers(include_only=enhanced_selected_skills) if with_skills else {}
            ),
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

        _phase_write_rules(
            unified_content,
            output_dir,
            inc_analyzer,
            verbose,
            generated_files,
            skills_manager,
            include_only=enhanced_selected_skills if with_skills else None,
        )
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

        # H4 fix: overwrite skills/index.md with generate_perfect_index so it
        # lists exactly the same skills as clinerules.yaml.  The legacy
        # _run_skill_orchestration above uses its own skill-selection logic
        # (independent of enhanced_selected_skills) causing the two files to
        # diverge.  generate_perfect_index with include_only= fixes that.
        project_type_label = (enhanced_context or {}).get("metadata", {}).get("project_type", "")
        index_path = skills_manager.generate_perfect_index(
            project_type=project_type_label,
            include_only=enhanced_selected_skills if with_skills else None,
        )
        # Replace the stale path already appended by _run_skill_orchestration
        stale = output_dir / "skills" / "index.md"
        if stale in generated_files and index_path and index_path != stale:
            generated_files[generated_files.index(stale)] = index_path

        # M3: ensure .clinerules/.gitignore suppresses .bak and .tmp files
        _ensure_clinerules_gitignore(output_dir)

    return generated_files


def _ensure_clinerules_gitignore(output_dir: Path) -> None:
    """Create or update .clinerules/.gitignore to suppress generated backup files.

    atomic_write_text(..., backup=True) and save_markdown(..., backup=True) leave
    *.bak files in .clinerules/ after every run.  Without a .gitignore those files
    show up in `git status` and pollute commits.  This function idempotently writes
    (or extends) a minimal .gitignore so users never have to think about it.
    """
    gitignore_path = output_dir / ".gitignore"
    required_lines = {"*.bak", "*.tmp"}

    existing: set[str] = set()
    header_present = False
    if gitignore_path.exists():
        for raw in gitignore_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line:
                existing.add(line)
            if "project-rules-generator" in line:
                header_present = True

    missing = required_lines - existing
    if not missing:
        return  # already up-to-date

    parts: list[str] = []
    if gitignore_path.exists():
        parts.append(gitignore_path.read_text(encoding="utf-8").rstrip())
        parts.append("")  # blank line separator
    if not header_present:
        parts.append("# Generated by project-rules-generator")
    for entry in sorted(missing):
        parts.append(entry)
    parts.append("")  # trailing newline

    gitignore_path.write_text("\n".join(parts), encoding="utf-8")


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
    include_only: Optional[Set[str]] = None,
) -> None:
    """Phase 6: write rules.md and rules.json; merge incrementally when appropriate.

    Appends both files to generated_files.

    Args:
        include_only: Forwarded to save_triggers_json — limits auto-triggers.json to
                      the project's selected skill refs, preventing global-cache leakage.
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
    skills_manager.save_triggers_json(output_dir, include_only=include_only)
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
        # Bug 1 fix: generate README-based project skills FIRST so they are counted in
        # clinerules.yaml. Previously generate_clinerules() was called before
        # generate_from_readme(), so the 9 generated project skills never appeared in
        # enhanced_selected_skills when the YAML was written → project: 0.
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

            # Register generated project skills so clinerules.yaml counts them.
            # Strip display suffixes like " (reused)" and " (adapted)".
            for raw in generated_skills:
                skill_name = raw.split(" (")[0]
                enhanced_selected_skills.add(f"project/{skill_name}")

        # Bug 4 fix: drop learned refs (2-part OR 3-part) whose terminal name matches
        # a project ref of the same name. The matcher emits 3-part refs like
        # "learned/fastapi/pydantic-validation", so matching on f"learned/{n}" (2-part)
        # silently missed them. We now compare by ref.split("/")[-1] instead.
        project_names = {ref.split("/")[-1] for ref in enhanced_selected_skills if ref.startswith("project/")}
        enhanced_selected_skills -= {
            ref
            for ref in set(enhanced_selected_skills)
            if ref.startswith("learned/") and ref.split("/")[-1] in project_names
        }

        lightweight_yaml = generate_clinerules(
            project_name,
            enhanced_selected_skills,
            enhanced_context,
            output_dir=output_dir,
        )

        # Bug 2 fix: add a visible skill listing so agents can read active skills
        # without having to parse the hidden YAML comment below.
        project_refs = sorted(r for r in enhanced_selected_skills if r.startswith(f"{SkillScope.PROJECT}/"))
        learned_refs = sorted(r for r in enhanced_selected_skills if r.startswith(f"{SkillScope.LEARNED}/"))
        builtin_refs = sorted(r for r in enhanced_selected_skills if r.startswith(f"{SkillScope.BUILTIN}/"))
        if project_refs or learned_refs or builtin_refs:
            unified_content += "## Active Skills\n"
            for ref in project_refs + learned_refs + builtin_refs:
                name = ref.split("/")[-1]
                tier = ref.split("/")[0]
                unified_content += f"- **{name}** ({tier}): `skills/{tier}/{name}/{SKILL_FILENAME}`\n"
            unified_content += "\n"

        unified_content += f"\n\n<!-- Lightweight Skill References\n{lightweight_yaml}-->\n"

        lightweight_path = output_dir / "clinerules.yaml"
        lightweight_path.write_text(lightweight_yaml, encoding="utf-8")
        generated_files.append(lightweight_path)
        if verbose:
            click.echo(f"   Generated clinerules.yaml ({len(enhanced_selected_skills)} skills)")

        # Copy skill files into output_dir/skills/ (builtin and learned only;
        # project skills are already written by generate_from_readme above).
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
