"""
README Bridge Utilities
=======================

Shared helpers used by both the skill and rules generation pipelines
when the project README is missing or too sparse to rely on.

Public API:
    is_readme_sufficient(readme_content, min_words=80) -> bool
    build_project_tree(project_path, max_depth=3, max_items=60) -> str
    bridge_missing_context(project_path, name, interactive=None) -> str
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

README_MIN_WORDS = 80  # Below this → README is too sparse

_TREE_EXCLUDE = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
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
        print(f"\n⚠️  README is missing or too sparse to generate a good '{name}'.")
        print("\n" + tree_block)
        print("\n💬 In 2-3 sentences, describe what this project does (press Enter to skip):")
        try:
            description = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            description = ""

        if description:
            return f"[User description]: {description}\n\n{tree_block}"

    # Non-interactive: tree only, AI infers the rest
    print(f"ℹ️  README sparse for '{name}' — using project tree for context.")
    return tree_block
