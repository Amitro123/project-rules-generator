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
from typing import Any, Dict, List, Optional, Tuple

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

    spec_path = _find_spec_file(project_path)
    if spec_path is None:
        return result

    raw = _load_spec_yaml(spec_path)
    if not isinstance(raw, dict):
        return result

    result["project_name"], result["description"] = _parse_spec_project(raw)
    result["python_version"], result["dependencies"] = _parse_spec_environment(raw)
    result["test_framework"] = _parse_spec_testing(raw)
    result["architecture_components"], result["extra_tech"] = _parse_spec_architecture(raw)

    logger.debug(
        "Parsed %s: name=%r deps=%d components=%d extra_tech=%s",
        spec_path.name,
        result["project_name"],
        len(result["dependencies"]),
        len(result["architecture_components"]),
        result["extra_tech"],
    )
    return result


# Component-description keyword -> canonical tech name (None = recognized but not a tagged tech).
_SPEC_TECH_KEYWORDS: Dict[str, Optional[str]] = {
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


def _find_spec_file(project_path: Path) -> Optional[Path]:
    """Locate spec.yml / spec.yaml in the project root (first match wins)."""
    for name in ("spec.yml", "spec.yaml"):
        candidate = project_path / name
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _load_spec_yaml(spec_path: Path) -> Any:
    """Best-effort YAML load; returns an empty dict on any parse failure."""
    try:
        import yaml  # PyYAML is a standard PRG dependency

        return yaml.safe_load(spec_path.read_text(encoding="utf-8", errors="replace")) or {}
    except Exception:  # noqa: BLE001 — spec parsing is best-effort
        logger.debug("Could not parse %s - skipping spec enrichment", spec_path)
        return {}


def _parse_spec_project(raw: Dict[str, Any]) -> Tuple[str, str]:
    """Extract (project_name, description) from the spec's ``project`` section."""
    proj = raw.get("project", {}) or {}
    if isinstance(proj, dict):
        return str(proj.get("name", "")).strip(), str(proj.get("description", "")).strip()
    return "", ""


def _parse_spec_environment(raw: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Extract (python_version, dependency_names) from the spec's ``environment`` section."""
    env = raw.get("environment", {}) or {}
    if not isinstance(env, dict):
        return "", []

    python_version = ""
    py_ver = env.get("python_version", "")
    if py_ver:
        python_version = str(py_ver)

    dep_names: List[str] = []
    for dep in env.get("dependencies", []) or []:
        if isinstance(dep, str):
            # Strip version pins: "fastapi==0.100" -> "fastapi"
            name_part = dep.split("==")[0].split(">=")[0].split("<=")[0].strip()
            # Skip commented/future deps (lines starting with # in YAML scalars)
            if name_part and not name_part.startswith("#"):
                dep_names.append(name_part.lower())
    return python_version, dep_names


def _parse_spec_testing(raw: Dict[str, Any]) -> Optional[str]:
    """Infer the test framework from the spec's ``testing`` section."""
    testing = raw.get("testing", {}) or {}
    if not isinstance(testing, dict):
        return None
    if "test_framework" in testing:
        return str(testing["test_framework"]).lower()
    if any(k in testing for k in ("unit_tests", "pytest", "conftest")):
        return "pytest"
    return None


def _parse_spec_architecture(raw: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Extract (component_names, extra_tech) from the spec's ``architecture`` section."""
    arch = raw.get("architecture", {}) or {}
    components = arch.get("components", []) or []
    component_names: List[str] = []
    extra_tech: List[str] = []
    for comp in components:
        if not isinstance(comp, dict):
            continue
        cname = str(comp.get("name", "")).strip()
        if cname:
            component_names.append(cname)
        # Mine description for extra tech hints
        desc = str(comp.get("description", "") or comp.get("storage", "") or "").lower()
        for kw, tech in _SPEC_TECH_KEYWORDS.items():
            if kw in desc and tech:
                extra_tech.append(tech)
    return component_names, list(dict.fromkeys(extra_tech))  # deduplicate, preserve order


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
