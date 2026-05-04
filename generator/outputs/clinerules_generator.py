"""Generate lightweight .clinerules that references global skills."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Set

import yaml

from generator.prompts.skill_generation import detect_project_tools
from generator.storage.skill_paths import SkillPathManager

logger = logging.getLogger(__name__)


def generate_clinerules(
    project_name: str,
    selected_skills: Set[str],
    project_context: Optional[Dict[str, Any]] = None,
    output_dir: "Path | None" = None,
) -> str:
    """
    Generate lightweight .clinerules YAML that links to skills.

    When output_dir is provided, paths are relative (e.g. skills/builtin/code-review.md)
    pointing to copied skill files inside the output directory. Otherwise falls back to
    absolute global paths in ~/.project-rules-generator/.

    Args:
        project_name: Name of the project
        selected_skills: Set of skill refs like {'builtin/code-review', 'learned/fastapi/async-patterns'}
        project_context: Optional context for additional metadata
        output_dir: Optional output directory for relative path generation

    Returns:
        YAML string content for .clinerules file
    """
    builtin_skills = []
    learned_skills = []
    project_skills = []

    # Track emitted names per tier to prevent duplicate entries when multiple
    # category-prefixed refs (e.g. learned/fastapi/async-patterns and
    # learned/pytest/async-patterns) resolve to the same terminal skill name.
    seen_builtin: set = set()
    seen_learned: set = set()
    seen_project: set = set()

    for skill in sorted(selected_skills):
        parts = skill.split("/")

        if skill.startswith("builtin/"):
            name = parts[-1]
            if name in seen_builtin:
                continue
            seen_builtin.add(name)

            if output_dir:
                rel_path = f"skills/builtin/{name}/SKILL.md"
            else:
                global_path = SkillPathManager.GLOBAL_BUILTIN / f"{name}.md"
                if not global_path.exists():
                    for ext in (".yaml", ".yml"):
                        alt = SkillPathManager.GLOBAL_BUILTIN / f"{name}{ext}"
                        if alt.exists():
                            global_path = alt
                            break
                if not global_path.exists():
                    dir_path = SkillPathManager.GLOBAL_BUILTIN / name / "SKILL.md"
                    if dir_path.exists():
                        global_path = dir_path
                rel_path = str(global_path)

            builtin_skills.append(
                {
                    "name": name,
                    "path": rel_path,
                }
            )

        elif skill.startswith("learned/"):
            if len(parts) >= 3:
                category = parts[1]
                name = parts[2]
            else:
                category = "general"
                name = parts[-1]

            if name in seen_learned:
                continue
            seen_learned.add(name)

            if output_dir:
                rel_path = f"skills/learned/{name}/SKILL.md"
            else:
                global_path = SkillPathManager.GLOBAL_LEARNED / category / f"{name}.md"
                if not global_path.exists():
                    for ext in (".yaml", ".yml"):
                        alt = SkillPathManager.GLOBAL_LEARNED / category / f"{name}{ext}"
                        if alt.exists():
                            global_path = alt
                            break
                rel_path = str(global_path)

            learned_skills.append(
                {
                    "name": f"{category}/{name}",
                    "path": rel_path,
                }
            )

        elif skill.startswith("project/"):
            # Project-local skills live under .clinerules/skills/project/<name>/SKILL.md
            name = "/".join(parts[1:])  # preserve sub-path, e.g. "gemini-api"
            if name in seen_project:
                continue
            seen_project.add(name)
            if output_dir:
                rel_path = f"skills/project/{name}/SKILL.md"
            else:
                rel_path = f"skills/project/{name}/SKILL.md"

            project_skills.append(
                {
                    "name": name,
                    "path": rel_path,
                }
            )

    # Build the clinerules structure
    clinerules: Dict[str, Any] = {
        "project": project_name,
        "version": "2.0",
        "generated_by": "project-rules-generator",
    }

    # Add tech stack summary if available
    if project_context:
        metadata = project_context.get("metadata", {})
        if metadata.get("tech_stack"):
            clinerules["tech_stack"] = metadata["tech_stack"]
        if metadata.get("project_type"):
            clinerules["project_type"] = metadata["project_type"]

    # Tools section: runnable commands for the project
    if project_context:
        metadata = project_context.get("metadata", {})
        project_path_str = project_context.get("readme", {}).get("readme_path", "")
        project_path = Path(project_path_str).parent if project_path_str else None
        tools = detect_project_tools(project_path, metadata.get("tech_stack", []))
        if tools:
            clinerules["tools"] = tools

    # Skills section
    skills_section: Dict[str, Any] = {}

    if project_skills:
        skills_section["project"] = [s["path"] for s in project_skills]

    if builtin_skills:
        skills_section["builtin"] = [s["path"] for s in builtin_skills]

    if learned_skills:
        skills_section["learned"] = [s["path"] for s in learned_skills]

    clinerules["skills"] = skills_section

    # Summary counts
    clinerules["skills_count"] = {
        "project": len(project_skills),
        "builtin": len(builtin_skills),
        "learned": len(learned_skills),
        "total": len(project_skills) + len(builtin_skills) + len(learned_skills),
    }

    # Context configuration
    clinerules["context"] = _build_context_config(project_context)

    return yaml.dump(clinerules, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _build_context_config(project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build context configuration for .clinerules.yaml.

    Returns dict with exclude patterns, max_file_size, and load_on_demand hints.
    """
    exclude = [
        "**/*.pyc",
        "**/__pycache__/**",
        "**/.venv/**",
        "**/node_modules/**",
        "**/.web/**",
        "**/*-skills.md",
        "**/*-skills.json",
        "**/.clinerules*",
    ]

    load_on_demand = [
        "tests/",
        "docs/",
    ]

    if project_context:
        metadata = project_context.get("metadata", {})
        project_type = metadata.get("project_type", "")

        # Add project-type specific excludes
        if project_type == "django-app":
            exclude.append("**/migrations/**")
        if "docker" in metadata.get("tech_stack", []):
            exclude.append("**/docker-compose.override.yml")

        # Add project-type specific load_on_demand
        structure = project_context.get("structure", {})
        patterns = structure.get("patterns", [])
        if any("api" in p for p in patterns) or "fastapi" in project_type:
            load_on_demand.append("migrations/")
        if structure.get("entry_points"):
            # Config/spec directories are usually load-on-demand
            for ep in structure["entry_points"]:
                if "/" in ep:
                    top_dir = ep.split("/")[0] + "/"
                    if top_dir not in load_on_demand:
                        load_on_demand.append(top_dir)

    return {
        "exclude": exclude,
        "max_file_size": 50000,
        "load_on_demand": load_on_demand,
    }
