"""
Tech Stack Detection Utilities
==============================
Consolidated tech detection logic from:
- generator/skill_creator.py (_detect_tech_stack, _detect_from_dependencies)
- generator/skill_parser.py (extract_tech_context)
"""

import json
from pathlib import Path
from typing import List, Set

from generator.tech_registry import PKG_MAP, TECH_README_KEYWORDS

# Alias map for tech name variations
TECH_ALIASES = {
    "fastapi": {"fastapi", "fast api"},
    "websocket": {"websocket", "websockets", "web socket"},
    "perplexity": {"perplexity", "sonar"},
    "openai": {"openai", "gpt-4", "gpt-3", "chatgpt"},
    "pytorch": {"pytorch", "torch"},
    "chrome": {"chrome", "chrome extension", "manifest.json", "background.js", "content script"},
    "gitpython": {"gitpython", "git diff", "git operations", "repo.git"},
    "mcp": {"mcp", "model context protocol", "mcp server", "mcp tool"},
}


def extract_context(tech: str, readme_content: str) -> List[str]:
    """
    Extract lines from README that mention a specific technology.

    Consolidated from SkillParser.extract_tech_context().
    """
    lines = readme_content.split("\n")
    context = []
    tech_lower = tech.lower()

    aliases = TECH_ALIASES.get(tech_lower, {tech_lower})

    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(alias in line_lower for alias in aliases):
            stripped = line.strip()
            if not stripped or stripped.startswith("```") or stripped.startswith("|--"):
                continue
            if stripped not in context:
                context.append(stripped)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if (
                        next_line
                        and not next_line.startswith("#")
                        and not next_line.startswith("```")
                        and next_line not in context
                    ):
                        context.append(next_line)

    return context[:10]


def detect_from_readme(readme_content: str) -> Set[str]:
    """
    Detect tech stack from README content (keyword-based).
    Less reliable than detect_from_dependencies - use as confirmation only.
    """
    detected = set()
    content_lower = readme_content.lower()

    for tech, keywords in TECH_README_KEYWORDS.items():
        if any(kw in content_lower for kw in keywords):
            detected.add(tech)

    return detected


def detect_from_dependencies(project_path: Path) -> Set[str]:
    """
    Detect tech stack from actual dependency files.
    Most reliable method - checks requirements.txt, package.json, Dockerfile.

    Consolidated from CoworkSkillCreator._detect_from_dependencies().
    """
    detected = set()

    # Python: requirements.txt
    requirements_file = project_path / "requirements.txt"
    if requirements_file.exists():
        try:
            content = requirements_file.read_text(encoding="utf-8", errors="ignore").lower()
            for pkg, tech in PKG_MAP.items():
                if pkg in content:
                    detected.add(tech)
            detected.add("python")  # Has requirements.txt = Python project
        except OSError:
            pass

    # Python: pyproject.toml
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
            if "fastapi" in content:
                detected.add("fastapi")
            if "pytest" in content:
                detected.add("pytest")
            detected.add("python")
        except OSError:
            pass

    # Node: package.json
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            pkg_data = json.loads(package_json.read_text(encoding="utf-8"))
            deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
            node_map = {
                "react": "react",
                "vue": "vue",
                "express": "express",
                "jest": "jest",
                "typescript": "typescript",
                "@types/react": "react",
                "konva": "konva",
                "react-konva": "konva",
                "three": "threejs",
                "babylonjs": "babylon",
            }
            for pkg, tech in node_map.items():
                if pkg in deps:
                    detected.add(tech)
            if "typescript" not in detected:
                detected.add("javascript")
        except (OSError, ValueError):
            pass

    # Docker
    if (project_path / "Dockerfile").exists() or (project_path / "docker-compose.yml").exists():
        detected.add("docker")

    return detected


def detect_tech_stack(project_path: Path, readme_content: str = "") -> List[str]:
    """
    Full tech stack detection: dependencies + files + README confirmation.

    This is the primary entry point for tech detection.
    Consolidated from CoworkSkillCreator._detect_tech_stack().
    """
    detected = set()

    # 1. Most reliable: actual dependency files
    detected.update(detect_from_dependencies(project_path))

    # 2. Check for tech-specific files
    detected.update(_detect_from_files(project_path))

    # 3. README - confirmation for common techs, primary source for canvas/DXF/specialized techs
    if readme_content:
        readme_detected = detect_from_readme(readme_content)
        # These techs rarely appear in dependency files (CDN, inline, or specialized)
        # so README is the primary source for them
        readme_primary_techs = {
            "konva",
            "canvas",
            "dxf",
            "threejs",
            "babylon",
            "supabase",
            "reportlab",
            "pdf",
        }
        # Infrastructure/ops techs (docker, telegram, linux, yaml, vite, …) also
        # belong here — they live in docs/README for ops-heavy projects that have
        # no Python/Node dependency files at all.
        try:
            from generator.tech.lookups import TECH_CATEGORIES

            readme_primary_techs.update(
                name for name, cat in TECH_CATEGORIES.items() if cat == "infrastructure"
            )
        except Exception:  # noqa: BLE001 — guard against import issues at startup
            readme_primary_techs.update({"docker", "docker-compose", "telegram", "yaml", "linux", "vite"})

        # If no dep files were found at all, treat README as the primary source
        # for everything (docs-only / agent-skills projects).
        allow_all_from_readme = len(detected) == 0

        for tech in readme_detected:
            if (
                allow_all_from_readme
                or tech in detected
                or tech in {"python", "typescript", "javascript"}
                or tech in readme_primary_techs
            ):
                detected.add(tech)

    return list(detected)


def _detect_from_files(project_path: Path) -> Set[str]:
    """Detect tech from actual project files."""
    detected = set()

    if any(project_path.rglob("*.py")):
        detected.add("python")
    if any(project_path.rglob("*.ts")) or any(project_path.rglob("*.tsx")):
        detected.add("typescript")
    if any(project_path.rglob("*.jsx")):
        detected.add("react")
    if (project_path / "Dockerfile").exists():
        detected.add("docker")

    return detected
