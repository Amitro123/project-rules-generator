"""
Tech Stack Detection Utilities
==============================
Consolidated tech detection logic from:
- generator/skill_creator.py (_detect_tech_stack, _detect_from_dependencies)
- generator/skill_parser.py (extract_tech_context)
"""

import json
import re
from pathlib import Path
from typing import List, Set


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

    tech_keywords = {
        "fastapi": ["fastapi", "fast api"],
        "flask": ["flask"],
        "django": ["django"],
        "react": ["react", "reactjs", "react.js"],
        "vue": ["vue", "vuejs", "vue.js"],
        "express": ["express", "expressjs"],
        "pytest": ["pytest"],
        "docker": ["docker", "dockerfile", "docker-compose"],
        "python": ["python"],
        "typescript": ["typescript"],
        "javascript": ["javascript", "node.js", "nodejs"],
        "sqlalchemy": ["sqlalchemy"],
        "pydantic": ["pydantic"],
        "celery": ["celery"],
        "redis": ["redis"],
        "openai": ["openai", "gpt-4", "gpt-3"],
        "langchain": ["langchain"],
        # 2D/3D canvas and DXF editing
        "konva": ["konva", "konvajs", "konva.js"],
        "canvas": ["canvas", "svg canvas", "html canvas"],
        "dxf": ["dxf", "ezdxf", "dxf editor", "dxf upload", "dxf viewer"],
        "threejs": ["three.js", "threejs", "three js", "webgl", "3d extrusion"],
        "babylon": ["babylon", "babylonjs", "babylon.js"],
        "supabase": ["supabase"],
        "reportlab": ["reportlab"],
        "pdf": ["pdf", "pdf generation", "pdf export"],
    }

    for tech, keywords in tech_keywords.items():
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
            pkg_map = {
                "fastapi": "fastapi",
                "flask": "flask",
                "django": "django",
                "pytest": "pytest",
                "sqlalchemy": "sqlalchemy",
                "pydantic": "pydantic",
                "celery": "celery",
                "redis": "redis",
                "openai": "openai",
                "anthropic": "anthropic",
                "langchain": "langchain",
                "ezdxf": "dxf",
                "reportlab": "reportlab",
                "supabase": "supabase",
                "konva": "konva",
            }
            for pkg, tech in pkg_map.items():
                if pkg in content:
                    detected.add(tech)
            detected.add("python")  # Has requirements.txt = Python project
        except Exception:
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
        except Exception:
            pass

    # Node: package.json
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            content = json.loads(package_json.read_text(encoding="utf-8"))
            deps = {**content.get("dependencies", {}), **content.get("devDependencies", {})}
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
        except Exception:
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
            "konva", "canvas", "dxf", "threejs", "babylon", "supabase",
            "reportlab", "pdf",
        }
        for tech in readme_detected:
            if (
                tech in detected
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
