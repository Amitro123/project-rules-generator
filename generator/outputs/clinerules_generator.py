"""Generate lightweight .clinerules that references global skills."""

import yaml
from pathlib import Path
from typing import Set, Dict, List, Any
import logging

from generator.storage.skill_paths import SkillPathManager

logger = logging.getLogger(__name__)


def generate_clinerules(
    project_name: str,
    selected_skills: Set[str],
    project_context: Dict[str, Any] = None,
) -> str:
    """
    Generate lightweight .clinerules YAML that links to skills in ~/.project-rules-generator/.

    Args:
        project_name: Name of the project
        selected_skills: Set of skill refs like {'builtin/code-review', 'learned/fastapi/async-patterns'}
        project_context: Optional context for additional metadata

    Returns:
        YAML string content for .clinerules file
    """
    builtin_skills = []
    learned_skills = []

    for skill in sorted(selected_skills):
        parts = skill.split('/')

        if skill.startswith('builtin/'):
            name = parts[-1]
            path = SkillPathManager.GLOBAL_BUILTIN / f"{name}.md"
            # Try alternative extensions
            if not path.exists():
                for ext in ('.yaml', '.yml'):
                    alt = SkillPathManager.GLOBAL_BUILTIN / f"{name}{ext}"
                    if alt.exists():
                        path = alt
                        break
            # Check directory style
            if not path.exists():
                dir_path = SkillPathManager.GLOBAL_BUILTIN / name / 'SKILL.md'
                if dir_path.exists():
                    path = dir_path

            builtin_skills.append({
                'name': name,
                'path': str(path),
            })

        elif skill.startswith('learned/'):
            if len(parts) >= 3:
                category = parts[1]
                name = parts[2]
            else:
                category = 'general'
                name = parts[-1]

            path = SkillPathManager.GLOBAL_LEARNED / category / f"{name}.md"
            if not path.exists():
                for ext in ('.yaml', '.yml'):
                    alt = SkillPathManager.GLOBAL_LEARNED / category / f"{name}{ext}"
                    if alt.exists():
                        path = alt
                        break

            learned_skills.append({
                'name': f"{category}/{name}",
                'path': str(path),
            })

    # Build the clinerules structure
    clinerules: Dict[str, Any] = {
        'project': project_name,
        'version': '2.0',
        'generated_by': 'project-rules-generator',
    }

    # Add tech stack summary if available
    if project_context:
        metadata = project_context.get('metadata', {})
        if metadata.get('tech_stack'):
            clinerules['tech_stack'] = metadata['tech_stack']
        if metadata.get('project_type'):
            clinerules['project_type'] = metadata['project_type']

    # Skills section
    skills_section: Dict[str, Any] = {}

    if builtin_skills:
        skills_section['builtin'] = [s['path'] for s in builtin_skills]

    if learned_skills:
        skills_section['learned'] = [s['path'] for s in learned_skills]

    clinerules['skills'] = skills_section

    # Summary counts
    clinerules['skills_count'] = {
        'builtin': len(builtin_skills),
        'learned': len(learned_skills),
        'total': len(builtin_skills) + len(learned_skills),
    }

    return yaml.dump(clinerules, default_flow_style=False, sort_keys=False, allow_unicode=True)


def generate_clinerules_with_inline(
    project_name: str,
    selected_skills: Set[str],
    rules_content: str = '',
    project_context: Dict[str, Any] = None,
) -> str:
    """
    Generate a .clinerules file with inline skill content (backward compatible).

    This produces the full unified format with rules + embedded skill definitions,
    while also including the lightweight skill references.

    Args:
        project_name: Name of the project
        selected_skills: Set of skill refs
        rules_content: Pre-generated rules markdown content
        project_context: Optional project context

    Returns:
        Markdown string with rules and embedded skills
    """
    content = rules_content or ''

    # Add lightweight YAML header as comment
    yaml_refs = generate_clinerules(project_name, selected_skills, project_context)
    content += f"\n\n<!-- Skill References (lightweight)\n{yaml_refs}-->\n"

    # Add skill section with loaded content
    content += "\n# Agent Skills\n\n"

    builtin_loaded = 0
    learned_loaded = 0

    for skill_ref in sorted(selected_skills):
        skill_path = SkillPathManager.get_skill_path(skill_ref)
        if skill_path and skill_path.exists():
            try:
                skill_content = skill_path.read_text(encoding='utf-8', errors='replace')
                name = skill_ref.split('/')[-1]
                content += f"\n## Skill: {name}\n\n{skill_content}\n\n---\n"

                if skill_ref.startswith('builtin/'):
                    builtin_loaded += 1
                else:
                    learned_loaded += 1
            except Exception as e:
                logger.warning(f"Failed to load skill {skill_ref}: {e}")
        else:
            logger.debug(f"Skill file not found for: {skill_ref}")

    content += f"\n<!-- Skills loaded: {builtin_loaded} builtin, {learned_loaded} learned -->\n"

    return content
