"""Skill pipeline helpers for the analyze command.

Separated from analyze_pipeline.py to keep each module focused.
Functions here handle auto-detection, LLM generation, file copying,
stub creation, and orchestration of the skill layer.
"""

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import click

from generator.analyzers.project_type_detector import detect_project_type_from_data
from generator.extractors.code_extractor import CodeExampleExtractor
from generator.parsers.enhanced_parser import EnhancedProjectParser
from generator.prompts.skill_generation import build_skill_prompt
from generator.renderers import get_renderer
from generator.skill_generator import SkillGenerator
from generator.skills.enhanced_skill_matcher import EnhancedSkillMatcher
from generator.sources.learned import LearnedSkillsSource
from generator.storage.skill_paths import SkillPathManager
from generator.types import SkillFile
from prg_utils.file_ops import save_markdown


def _auto_generate_skills(
    project_path: Path,
    project_name: str,
    enhanced_context: Optional[Dict[str, Any]],
    provider: str,
    ai: bool,
    verbose: bool,
    skills_manager: Any,
    strategy: str,
    output_dir: Optional[Path] = None,
) -> Set[str]:
    """Auto-detect and optionally LLM-generate matched skills. Returns selected skill refs."""
    try:
        if enhanced_context is None:
            enhanced_context = EnhancedProjectParser(project_path).extract_full_context()

        detected_tech = enhanced_context.get("metadata", {}).get("tech_stack", [])
        project_type = enhanced_context.get("metadata", {}).get("project_type", "unknown")

        if verbose:
            click.echo("\n   Enhanced Analysis:")
            click.echo(f"   Project Type: {project_type}")
            click.echo(f"   Tech Stack: {', '.join(detected_tech)}")
            dep_count = len(enhanced_context.get("dependencies", {}).get("python", []))
            dep_count += len(enhanced_context.get("dependencies", {}).get("node", []))
            click.echo(f"   Dependencies: {dep_count} parsed")
            test_info = enhanced_context.get("test_patterns", {})
            if test_info.get("framework"):
                click.echo(f"   Tests: {test_info['framework']} ({test_info.get('test_files', 0)} files)")

        enhanced_selected_skills = EnhancedSkillMatcher().match_skills(
            detected_tech=detected_tech,
            project_context=enhanced_context,
        )

        if verbose:
            click.echo(f"   Matched Skills: {len(enhanced_selected_skills)}")
            for s in sorted(enhanced_selected_skills):
                click.echo(f"     - {s}")

        SkillPathManager.ensure_setup()

        if ai:
            _llm_generate_skills(
                project_path=project_path,
                project_name=project_name,
                enhanced_context=enhanced_context,
                detected_tech=detected_tech,
                enhanced_selected_skills=enhanced_selected_skills,
                provider=provider,
                verbose=verbose,
                skills_manager=skills_manager,
                output_dir=output_dir,
            )

        return enhanced_selected_skills

    except Exception as e:  # noqa: BLE001 — CLI boundary: enhanced generation is optional
        click.echo(f"Warning: Enhanced auto-generation failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return set()


def _llm_generate_skills(
    project_path: Path,
    project_name: str,
    enhanced_context: Dict[str, Any],
    detected_tech: List[str],
    enhanced_selected_skills: Set[str],
    provider: str,
    verbose: bool,
    skills_manager: Any,
    output_dir: Optional[Path] = None,
) -> None:
    """Call the LLM to generate content for each matched learned skill.

    Bug B fix: writes the LLM output to the project-local
    ``<output_dir>/skills/learned/<ref_name>/SKILL.md`` instead of the global
    ``~/.project-rules-generator/learned/`` cache. Previously every
    ``prg analyze`` run poured fresh per-project LLM content into the global
    dir, causing those skills to leak into unrelated projects as ghost
    triggers. Global writes are now reserved for explicit
    ``prg skills save`` / ``prg skills create --scope learned`` commands.
    """
    extractor = CodeExampleExtractor()
    llm_auth_failed = False

    # Default output_dir to <project>/.clinerules when the caller hasn't
    # threaded it through (keeps backward-compat for older callers).
    if output_dir is None:
        output_dir = project_path / ".clinerules"

    # Bug F fix: instantiate the LLM client ONCE and reuse it across every
    # skill generation. Previously we created a new LLMSkillGenerator inside
    # the loop, which re-ran `genai.Client()` — and the google-genai SDK
    # prints "Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using
    # GOOGLE_API_KEY." on every client construction when both env vars are
    # present. Hoisting the instantiation makes that warning fire at most
    # once per run (at true provider-init time), matching what users expect.
    llm_gen = None  # lazy: stays None until the first skill that needs it

    for skill_ref in sorted(enhanced_selected_skills):
        if not skill_ref.startswith("learned/"):
            continue
        if llm_auth_failed:
            continue

        skill_topic = skill_ref.split("/")[-1]

        # Skip if the project-local skill already exists (idempotent reruns).
        project_skill_path = output_dir / "skills" / "learned" / skill_topic / "SKILL.md"
        if project_skill_path.exists():
            continue
        # Skip if the user already has this skill in their global learned cache —
        # reuse it instead of regenerating (and _copy_skill_files will pick it up).
        existing_path = SkillPathManager.get_skill_path(skill_ref)
        if existing_path and existing_path.exists():
            continue

        examples = extractor.extract_examples_for_skill(project_path, skill_topic, detected_tech)
        prompt = build_skill_prompt(
            skill_topic=skill_topic,
            project_name=project_name,
            context=enhanced_context,
            code_examples=examples,
            detected_patterns=enhanced_context.get("structure", {}).get("patterns", []),
            project_path=project_path,
        )

        try:
            if llm_gen is None:
                # Lazy init on the first skill that needs generation. Keeps
                # runs that skip every learned skill (all cached) zero-cost
                # and emits the provider warning at most once.
                from generator.llm_skill_generator import LLMSkillGenerator

                llm_gen = LLMSkillGenerator(provider=provider)
            skill_content = llm_gen.generate_content(prompt, max_tokens=2000)

            # Write directly to the project-local learned dir — never pollute
            # the user's global ~/.project-rules-generator/learned/.
            project_skill_path.parent.mkdir(parents=True, exist_ok=True)
            project_skill_path.write_text(skill_content, encoding="utf-8")
            skills_manager.discovery.invalidate_cache()
            click.echo(f"   💾 Generated: skills/learned/{skill_topic} (project-local)")
        except Exception as e:  # noqa: BLE001 — one item failure must not abort the batch
            err_str = str(e)
            click.echo(f"   ⚠️  Failed to generate {skill_ref}: {e}")
            if "invalid_api_key" in err_str or "401" in err_str or "authentication" in err_str.lower():
                click.echo("   ❌ API key invalid — skipping remaining LLM generations")
                llm_auth_failed = True


def _copy_skill_files(
    enhanced_selected_skills: Set[str],
    output_dir: Path,
    merge: bool,
    readme_path: Optional[Path],
    project_name: str,
    skills_manager: Any,
    verbose: bool,
) -> None:
    """Copy or stub skill files into output_dir/skills/ using subfolder layout."""
    for skill_ref in sorted(enhanced_selected_skills):
        skill_path = SkillPathManager.get_skill_path(skill_ref)
        ref_name = skill_ref.split("/")[-1]
        # Strip stale .md suffix so the directory name is clean
        ref_name = ref_name[:-3] if ref_name.endswith(".md") else ref_name

        # Always use subfolder layout: skills/{tier}/{name}/SKILL.md
        # This matches the paths generated by clinerules_generator.py
        if skill_ref.startswith("builtin/"):
            dest = output_dir / "skills" / "builtin" / ref_name / "SKILL.md"
        elif skill_ref.startswith("learned/"):
            dest = output_dir / "skills" / "learned" / ref_name / "SKILL.md"
        else:
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)

        if skill_path and skill_path.exists():
            # Guard against SameFileError when output_dir/skills/ is symlinked
            # to the global skill library (common on Linux/Mac).
            try:
                if skill_path.resolve() == dest.resolve():
                    continue
            except OSError:
                pass
            if not merge or not dest.exists():
                shutil.copy2(skill_path, dest)
        elif not dest.exists():
            _write_skill_stub(
                dest=dest,
                ref_name=ref_name,
                dest_name="SKILL.md",
                skill_ref=skill_ref,
                readme_path=readme_path,
                project_name=project_name,
                skills_manager=skills_manager,
                verbose=verbose,
            )


def _write_skill_stub(
    dest: Path,
    ref_name: str,
    dest_name: str,
    skill_ref: str,
    readme_path: Optional[Path],
    project_name: str,
    skills_manager: Any,
    verbose: bool,
) -> None:
    """Materialise a context-aware stub for a skill that has no file yet."""
    parts = skill_ref.split("/")
    category = parts[1] if len(parts) >= 3 else "general"
    title = ref_name.replace("-", " ").title()

    stub_context_lines: List[str] = []
    if readme_path and readme_path.exists():
        stub_context_lines = skills_manager._extract_tech_context(
            category,
            readme_path.read_text(encoding="utf-8", errors="replace"),
        )

    if stub_context_lines:
        purpose = skills_manager._summarize_purpose(category, stub_context_lines, project_name)
        guidelines = skills_manager._build_guidelines(category, stub_context_lines)
        context_block = "".join(f"> {line}\n" for line in stub_context_lines[:5])
        stub = (
            f"# {title}\n\n"
            f"**Project:** {project_name}\n"
            f"**Category:** {category}\n\n"
            f"## Purpose\n\n{purpose}\n\n"
            f"## Auto-Trigger\n\n"
            f"- Working with {category} integration code\n"
            f"- Editing files that import or configure {category}\n\n"
            f"## Process\n\n{guidelines}\n\n"
            f"## Output\n\n"
            f"Updated {category} implementation following project conventions.\n\n"
            f"## Project Context (from README)\n\n"
            f"{context_block}"
        )
    else:
        stub = (
            f"# {title}\n\n"
            f"**Project:** {project_name}\n"
            f"**Category:** {category}\n\n"
            f"## Purpose\n\n"
            f"Integration patterns for {ref_name.replace('-', ' ')} in {project_name}.\n\n"
            f"## Auto-Trigger\n\n"
            f"- Working with {category} code\n\n"
            f"## Process\n\n"
            f"- Refer to project README for {category} usage patterns\n"
            f"- Handle errors with proper retries and fallbacks\n\n"
            f"## Output\n\n"
            f"Updated {category} implementation following project conventions.\n"
        )

    dest.write_text(stub, encoding="utf-8")
    if verbose:
        label = "📝 Stub+" if stub_context_lines else "📄 Stub"
        click.echo(f"   {label}: {dest_name}")


def _run_skill_orchestration(
    config: Dict[str, Any],
    project_data: Dict[str, Any],
    project_name: str,
    project_path: Path,
    save_learned: bool,
    export_json: bool,
    export_yaml: bool,
    output_dir: Path,
    generated_files: List[Path],
) -> None:
    """Run skill orchestrator and write skills index + optional exports."""
    from cli.analyze_helpers import setup_orchestrator  # lazy: avoids circular cli imports

    orchestrator = setup_orchestrator(config)
    skills = orchestrator.orchestrate(project_data, str(project_path))

    if save_learned:
        learned_source = next(
            (s for s in orchestrator.sources if isinstance(s, LearnedSkillsSource)),
            None,
        )
        if learned_source:
            for skill in skills:
                learned_source.save_skill(skill)

    type_info = detect_project_type_from_data(project_data, str(project_path))
    primary_type = type_info["primary_type"]

    excluded = SkillGenerator.PROJECT_TYPE_SKILL_EXCLUSIONS.get(primary_type, frozenset())
    if excluded:
        skills = [s for s in skills if s.name not in excluded]

    skill_file = SkillFile(
        project_name=project_name,
        project_type=primary_type,
        skills=skills,
        confidence=type_info["confidence"],
        tech_stack=project_data.get("tech_stack", []),
        description=project_data.get("description", ""),
    )

    skills_content = get_renderer("markdown").render(skill_file)
    skills_index_path = output_dir / "skills" / "index.md"
    save_markdown(skills_index_path, skills_content)
    generated_files.append(skills_index_path)

    if export_json:
        json_content = get_renderer("json").render(skill_file)
        json_path = output_dir / "skills" / "index.json"
        json_path.write_text(json_content, encoding="utf-8")
        generated_files.append(json_path)

    if export_yaml:
        yaml_content = get_renderer("yaml").render(skill_file)
        yaml_path = output_dir / "skills" / "index.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")
        generated_files.append(yaml_path)
