"""Generation pipeline for the analyze command.

Runs the main artifact generation loop: enhanced parsing, constitution,
rules, skills auto-generation, export, and skill copying.
Extracted from analyze_cmd.py to keep each module focused.
"""

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import click

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
    ai: bool,
    auto_generate_skills: bool,
    constitution: bool,
    with_skills: bool,
    merge: bool,
    save_learned: bool,
    export_json: bool,
    export_yaml: bool,
    inc_analyzer: Any,
    strategy: str,
) -> List[Path]:
    """Run the full artifact generation pipeline.

    Returns:
        List of generated file paths.
    """
    from generator.constitution_generator import generate_constitution
    from generator.extractors.code_extractor import CodeExampleExtractor
    from generator.outputs.clinerules_generator import generate_clinerules
    from generator.parsers.enhanced_parser import EnhancedProjectParser
    from generator.prompts.skill_generation import build_skill_prompt
    from generator.rules_generator import generate_rules, rules_to_json
    from generator.skills.enhanced_skill_matcher import EnhancedSkillMatcher
    from generator.storage.skill_paths import SkillPathManager
    from prg_utils.file_ops import save_markdown

    if verbose:
        click.echo("\nGenerating files...")

    generated_files: List[Path] = []

    # Determine which phases need to run (all True when not incremental)
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
        # --- Phase 1: Enhanced project parsing ---
        pbar.set_description("Analyzing Project")
        enhanced_context = None
        if _run_enhanced:
            try:
                enhanced_parser = EnhancedProjectParser(project_path)
                enhanced_context = enhanced_parser.extract_full_context()
            except Exception as e:
                if verbose:
                    click.echo(f"   Enhanced analysis unavailable: {e}")
        elif verbose:
            click.echo("   Incremental: skipped enhanced parse (source/structure unchanged)")

        # --- Phase 2: Constitution ---
        if constitution and _run_constitution and enhanced_context:
            pbar.set_description("Generating Constitution")
            constitution_content = generate_constitution(project_name, enhanced_context, project_path=project_path)
            constitution_path = output_dir / "constitution.md"
            constitution_path.write_text(constitution_content, encoding="utf-8")
            generated_files.append(constitution_path)
            if verbose:
                click.echo("   Generated constitution.md")
        elif constitution and not _run_constitution:
            if verbose:
                click.echo("   Incremental: skipped constitution (README unchanged)")
        elif constitution and not enhanced_context:
            if verbose:
                click.echo("   Skipping constitution (enhanced analysis unavailable)")

        # --- Phase 3: Rules ---
        pbar.set_description("Generating Rules")
        if _run_rules:
            rules_content = generate_rules(project_data, config, enhanced_context=enhanced_context)
        else:
            # Load existing rules.md as the base content to carry forward
            existing_rules_path = output_dir / "rules.md"
            if existing_rules_path.exists():
                rules_content = existing_rules_path.read_text(encoding="utf-8")
                if verbose:
                    click.echo("   Incremental: skipped rules regen (README/deps unchanged) — using cached rules.md")
            else:
                rules_content = generate_rules(project_data, config, enhanced_context=enhanced_context)
        pbar.update(1)

        # --- Phase 4: Skills auto-generation ---
        pbar.set_description("Processing Skills")
        enhanced_selected_skills: Set[str] = set()
        if auto_generate_skills and _run_skills_gen:
            enhanced_selected_skills = _auto_generate_skills(
                project_path=project_path,
                project_name=project_name,
                enhanced_context=enhanced_context,
                provider=provider,
                ai=ai,
                verbose=verbose,
                skills_manager=skills_manager,
                strategy=strategy,
            )
        elif auto_generate_skills and not _run_skills_gen and verbose:
            click.echo("   Incremental: skipped skills auto-gen (source/README unchanged)")

        # Extract triggers
        triggers_dict: Dict[str, Any] = {}
        if with_skills:
            triggers_dict = skills_manager.extract_project_triggers()
            skills_manager.save_triggers_json(output_dir)
        pbar.update(1)

        # --- Phase 5: Build unified content ---
        pbar.set_description("Unified Export (.clinerules/)")
        unified_content = _build_unified_content(
            rules_content=rules_content,
            triggers_dict=triggers_dict,
            skills_manager=skills_manager,
            enhanced_selected_skills=enhanced_selected_skills,
            project_name=project_name,
            project_data=project_data,
            readme_path=readme_path,
            output_dir=output_dir,
            merge=merge,
            verbose=verbose,
            generated_files=generated_files,
        )

        # --- Phase 6: Write rules.md ---
        rules_path = output_dir / "rules.md"
        if inc_analyzer and rules_path.exists():
            from generator.incremental_analyzer import IncrementalAnalyzer

            changed_sections = inc_analyzer.detect_changes()  # cached — no re-read
            existing_rules = rules_path.read_text(encoding="utf-8")
            unified_content = IncrementalAnalyzer.merge_rules(existing_rules, unified_content, changed_sections)
            if verbose:
                click.echo(f"   Incremental: merged changes from {', '.join(sorted(changed_sections))}")
        save_markdown(rules_path, unified_content)
        generated_files.append(rules_path)

        # Generate rules.json
        rules_json_path = output_dir / "rules.json"
        rules_json_path.write_text(rules_to_json(unified_content), encoding="utf-8")
        if verbose:
            click.echo("Generating auto-triggers...")
        skills_manager.save_triggers_json(output_dir)
        generated_files.append(rules_json_path)
        if verbose:
            click.echo("   Generated rules.json")
        pbar.update(1)

        # --- Phase 7: Skill orchestration ---
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
        pbar.update(1)

    return generated_files


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
) -> str:
    """Assemble the unified rules + skills content string."""
    from generator.outputs.clinerules_generator import generate_clinerules
    from generator.storage.skill_paths import SkillPathManager

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
            _get_enhanced_context(skills_manager, project_data),
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


def _get_enhanced_context(skills_manager: Any, project_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Best-effort re-extraction of enhanced context (used for clinerules generation)."""
    try:
        from generator.parsers.enhanced_parser import EnhancedProjectParser

        return EnhancedProjectParser(skills_manager.project_path).extract_full_context()
    except Exception:
        return None


# Backward-compat re-exports — import from skill_pipeline directly for new code
from cli.skill_pipeline import (  # noqa: F401, E402
    _auto_generate_skills,
    _copy_skill_files,
    _llm_generate_skills,
    _run_skill_orchestration,
    _write_skill_stub,
)
