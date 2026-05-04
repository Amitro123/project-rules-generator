"""
README Bridge Utilities
=======================

Shared helpers used by both the skill and rules generation pipelines
when the project README is missing or too sparse to rely on.

Public API:
    find_readme(project_path) -> Optional[Path]
    is_readme_sufficient(readme_content, min_words=80) -> bool
    build_project_tree(project_path, max_depth=3, max_items=60) -> str
    bridge_missing_context(project_path, name, interactive=None) -> str
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

README_MIN_WORDS = 80  # Below this → README is too sparse

# Canonical ordered list of README filenames to check (most common first)
_README_CANDIDATES = ("README.md", "readme.md", "README.rst", "README.txt", "README")


def find_readme(project_path: Path) -> Optional[Path]:
    """Return the first README file found in project_path, or None.

    Checks filenames in a consistent priority order so all callers agree on
    which file is the README when multiple variants exist.
    """
    for name in _README_CANDIDATES:
        p = project_path / name
        if p.exists() and p.is_file():
            return p
    return None


_TREE_EXCLUDE = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".web",
    ".pytest_cache",
    "dist",
    "build",
    ".mypy_cache",
    ".ruff_cache",
    ".clinerules",
    ".claude",
    ".eggs",
    "eggs",
}


def is_readme_sufficient(readme_content: str, min_words: int = README_MIN_WORDS) -> bool:
    """Return True if README has enough words for meaningful generation."""
    if not readme_content or not readme_content.strip():
        return False
    return len(readme_content.split()) >= min_words


def build_project_tree(
    project_path: Path,
    max_depth: int = 3,
    max_items: int = 60,
) -> str:
    """Walk the project directory and return a structured tree string.

    Excludes noise (.git, __pycache__, venv, node_modules, etc.).
    Capped at max_items entries to stay within token budget.
    """
    lines: List[str] = [f"{project_path.name}/"]
    count = 0

    def _walk(path: Path, depth: int, prefix: str) -> None:
        nonlocal count
        if depth > max_depth or count >= max_items:
            return
        try:
            entries = sorted(
                path.iterdir(),
                key=lambda p: (p.is_file(), p.name.lower()),
            )
        except PermissionError:
            return

        visible = [e for e in entries if not e.name.startswith(".") and e.name not in _TREE_EXCLUDE]
        for i, item in enumerate(visible):
            if count >= max_items:
                lines.append(f"{prefix}... (truncated)")
                return
            connector = "└── " if i == len(visible) - 1 else "├── "
            child_prefix = prefix + ("    " if i == len(visible) - 1 else "│   ")
            if item.is_dir():
                lines.append(f"{prefix}{connector}{item.name}/")
                count += 1
                _walk(item, depth + 1, child_prefix)
            else:
                lines.append(f"{prefix}{connector}{item.name}")
                count += 1

    _walk(project_path, 1, "")
    return "\n".join(lines)


def parse_spec_file(project_path: Path) -> Dict[str, Any]:
    """Parse spec.yml or spec.yaml in the project root for structured project metadata.

    Returns a dict with keys (all optional / empty-default):
        project_name  (str)
        description   (str)
        python_version (str)
        dependencies  (list[str])  — package names only
        test_framework (str | None)
        architecture_components (list[str])
        extra_tech    (list[str])  — inferred from component descriptions
    """
    result: Dict[str, Any] = {
        "project_name": "",
        "description": "",
        "python_version": "",
        "dependencies": [],
        "test_framework": None,
        "architecture_components": [],
        "extra_tech": [],
    }

    # Try both extensions
    spec_path: Optional[Path] = None
    for name in ("spec.yml", "spec.yaml"):
        candidate = project_path / name
        if candidate.exists() and candidate.is_file():
            spec_path = candidate
            break

    if spec_path is None:
        return result

    try:
        import yaml  # PyYAML is a standard PRG dependency

        raw = yaml.safe_load(spec_path.read_text(encoding="utf-8", errors="replace")) or {}
    except Exception:  # noqa: BLE001 — spec parsing is best-effort
        logger.debug("Could not parse %s — skipping spec enrichment", spec_path)
        return result

    if not isinstance(raw, dict):
        return result

    # Project name + description
    proj = raw.get("project", {}) or {}
    if isinstance(proj, dict):
        result["project_name"] = str(proj.get("name", "")).strip()
        result["description"] = str(proj.get("description", "")).strip()

    # Python version
    env = raw.get("environment", {}) or {}
    if isinstance(env, dict):
        py_ver = env.get("python_version", "")
        if py_ver:
            result["python_version"] = str(py_ver)

        # Dependencies list from spec
        raw_deps = env.get("dependencies", []) or []
        dep_names: List[str] = []
        for dep in raw_deps:
            if isinstance(dep, str):
                # Strip version pins and comments: "fastapi==0.100" → "fastapi"
                name_part = dep.split("==")[0].split(">=")[0].split("<=")[0].strip()
                # Skip commented/future deps (lines starting with # in YAML scalars)
                if name_part and not name_part.startswith("#"):
                    dep_names.append(name_part.lower())
        result["dependencies"] = dep_names

    # Test framework from testing section
    testing = raw.get("testing", {}) or {}
    if isinstance(testing, dict):
        # Infer framework from key names: unit_tests → pytest, test_framework key
        if "test_framework" in testing:
            result["test_framework"] = str(testing["test_framework"]).lower()
        elif any(k in testing for k in ("unit_tests", "pytest", "conftest")):
            result["test_framework"] = "pytest"

    # Architecture component names
    arch = raw.get("architecture", {}) or {}
    components = arch.get("components", []) or []
    component_names: List[str] = []
    extra_tech: List[str] = []
    _tech_keywords = {
        "chroma": "chromadb",
        "chromadb": "chromadb",
        "qdrant": "qdrant",
        "vector": None,
        "openai": "openai",
        "vllm": "vllm",
        "docker": "docker",
        "lambda": "aws-lambda",
        "webhook": None,
        "telegram": "telegram",
        "langchain": "langchain",
        "langgraph": "langgraph",
        "opik": None,
        "cloudwatch": None,
    }
    for comp in components:
        if not isinstance(comp, dict):
            continue
        cname = str(comp.get("name", "")).strip()
        if cname:
            component_names.append(cname)
        # Mine description for extra tech hints
        desc = str(comp.get("description", "") or comp.get("storage", "") or "").lower()
        for kw, tech in _tech_keywords.items():
            if kw in desc and tech:
                extra_tech.append(tech)

    result["architecture_components"] = component_names
    result["extra_tech"] = list(dict.fromkeys(extra_tech))  # deduplicate, preserve order

    logger.debug(
        "Parsed %s: name=%r deps=%d components=%d extra_tech=%s",
        spec_path.name,
        result["project_name"],
        len(result["dependencies"]),
        len(result["architecture_components"]),
        result["extra_tech"],
    )
    return result


def bridge_missing_context(
    project_path: Path,
    name: str,
    interactive: Optional[bool] = None,
) -> str:
    """Build supplementary context when README is absent or sparse.

    Args:
        project_path: Root directory of the project.
        name: Skill or rule name being generated (used in the prompt).
        interactive: Override TTY detection. None = auto-detect via sys.stdin.

    Returns:
        A context string to prepend to readme_content before generation.

    Behavior:
        - Interactive (TTY / CLI): shows the project tree and asks the user
          for a 2-3 sentence description. Combines both into the context.
        - Non-interactive (IDE, pipe, CI): returns the project tree only;
          the AI model infers what it can from the file structure.
    """
    tree = build_project_tree(project_path)
    tree_block = f"[Project structure]\n{tree}"

    is_interactive = sys.stdin.isatty() if interactive is None else interactive

    if is_interactive:
        import click

        click.echo(f"\n⚠️  README is missing or too sparse to generate a good '{name}'.")
        click.echo("\n" + tree_block)
        click.echo("\n💬 In 2-3 sentences, describe what this project does (press Enter to skip):")
        try:
            description = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            description = ""

        if description:
            return f"[User description]: {description}\n\n{tree_block}"

    # Non-interactive: tree only, AI infers the rest
    logger.info("README sparse for '%s' — using project tree for context.", name)
    return tree_block
