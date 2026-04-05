"""Skill pipeline helpers for the analyze command.

Separated from analyze_pipeline.py to keep each module focused.
Functions here handle auto-detection, LLM generation, file copying,
stub creation, and orchestration of the skill layer.
"""

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import click


def _auto_generate_skills(
    project_path: Path,
    project_name: str,
    enhanced_context: Optional[Dict[str, Any]],
    provider: str,
    ai: bool,
    verbose: bool,
    skills_manager: Any,
    strategy: str,
) -> Set[str]:
    """Auto-detect and optionally LLM-generate matched skills. Returns selected skill refs."""
    from generator.skills.enhanced_skill_matcher import EnhancedSkillMatcher
    from generator.storage.skill_paths import SkillPathManager

    try:
        if enhanced_context is None:
            from generator.parsers.enhanced_parser import EnhancedProjectParser

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
            )

        return enhanced_selected_skills

    except Exception as e:
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
) -> None:
    """Call the LLM to generate content for each matched learned skill."""
    from generator.extractors.code_extractor import CodeExampleExtractor
    from generator.prompts.skill_generation import build_skill_prompt
    from generator.storage.skill_paths import SkillPathManager

    extractor = CodeExampleExtractor()
    llm_auth_failed = False

    for skill_ref in sorted(enhanced_selected_skills):
        if not skill_ref.startswith("learned/"):
            continue
        if llm_auth_failed:
            continue

        existing_path = SkillPathManager.get_skill_path(skill_ref)
        if existing_path and existing_path.exists():
            continue

        skill_topic = skill_ref.split("/")[-1]
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
            from generator.llm_skill_generator import LLMSkillGenerator

            llm_gen = LLMSkillGenerator(provider=provider)
            skill_content = llm_gen.generate_content(prompt, max_tokens=2000)

            parts = skill_ref.split("/")
            category = parts[1] if len(parts) >= 3 else "general"
            SkillPathManager.save_learned_skill({"name": skill_topic, "content": skill_content}, category)
            skills_manager.discovery.invalidate_cache()
            click.echo(f"   💾 Generated: {skill_ref}")
        except Exception as e:
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
    from generator.storage.skill_paths import SkillPathManager

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
        stub = (
            f"# {title}\n\n"
            f"**Project:** {project_name}\n"
            f"**Category:** {category}\n\n"
            f"## Purpose\n\n{purpose}\n\n"
            f"## Auto-Trigger\n\n"
            f"- Working with {category} integration code\n"
            f"- Editing files that import or configure {category}\n\n"
            f"## Guidelines\n\n{guidelines}\n\n"
            f"## Project Context (from README)\n\n"
        )
        for ctx_line in stub_context_lines[:5]:
            stub += f"> {ctx_line}\n"
    else:
        stub = (
            f"# {title}\n\n"
            f"**Project:** {project_name}\n"
            f"**Category:** {category}\n\n"
            f"## Purpose\n\n"
            f"Integration patterns for {ref_name.replace('-', ' ')} in {project_name}.\n\n"
            f"## Auto-Trigger\n\n"
            f"- Working with {category} code\n\n"
            f"## Guidelines\n\n"
            f"- Refer to project README for {category} usage patterns\n"
            f"- Handle errors with proper retries and fallbacks\n"
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
    from cli.analyze_helpers import setup_orchestrator
    from generator.analyzers.project_type_detector import detect_project_type_from_data
    from generator.renderers import get_renderer
    from generator.sources.learned import LearnedSkillsSource
    from generator.types import SkillFile
    from prg_utils.file_ops import save_markdown

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

    from generator.skill_generator import SkillGenerator

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
