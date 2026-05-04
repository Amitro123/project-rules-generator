"""Dependency, file-structure, and context-strategy builders."""

from __future__ import annotations

from typing import Dict, List, Optional


def _build_dep_section(python_deps: List[str], node_deps: List[str], missing_files: Optional[List[str]] = None) -> str:
    """Build dependency section from parsed deps."""
    lines = []
    if python_deps:
        lines.append(f"**Python** ({len(python_deps)} packages): {', '.join(python_deps[:15])}")
        if len(python_deps) > 15:
            lines.append(f"  ... and {len(python_deps) - 15} more")

    if node_deps:
        lines.append(f"**Node** ({len(node_deps)} packages): {', '.join(node_deps[:15])}")
        if len(node_deps) > 15:
            lines.append(f"  ... and {len(node_deps) - 15} more")

    if missing_files:
        lines.append(
            f"\n> [!WARNING]\n> **Missing Files (referenced in README)**: {', '.join(f'`{f}`' for f in missing_files)}"
        )

    if not lines:
        lines.append("No dependency files found.")
    return "\n".join(lines)


def _build_file_structure(structure: Dict, entry_points: List[str], patterns: List[str]) -> str:
    """Build file structure section."""
    lines = []
    if entry_points:
        lines.append("**Entry points:**")
        for ep in entry_points:
            lines.append(f"- `{ep}`")
    if patterns:
        lines.append("\n**Detected patterns:**")
        for p in patterns:
            lines.append(f"- {p}")
    if not lines:
        lines.append("Standard project layout.")
    return "\n".join(lines)


def _build_context_strategy(structure: Dict, entry_points: List[str], project_type: str, test_info: Dict) -> str:
    """Build context strategy section with file loading hints per task type."""
    lines: List[str] = []

    lines.append("### File Loading by Task Type")
    lines.append("")
    lines.append("| Task | Load first | Then load |")
    lines.append("|------|-----------|-----------|")

    bug_first = "relevant module source"
    bug_then = "corresponding `test_*.py` file" if test_info.get("framework") == "pytest" else "corresponding test file"
    lines.append(f"| Bug fix | {bug_first} | {bug_then} |")

    feat_first = f"`{entry_points[0]}`" if entry_points else "architecture overview"
    lines.append(f"| New feature | {feat_first} | related modules |")
    lines.append("| Refactor | module + its dependents | test suite |")

    test_first = "`conftest.py` + test directory" if test_info.get("has_conftest") else "test directory"
    lines.append(f"| Writing tests | {test_first} | source module under test |")
    lines.append("")

    if entry_points:
        lines.append("### Module Groupings")
        lines.append("")
        for ep in entry_points:
            ep_stem = ep.replace(".py", "").replace("/", ".").replace("\\", ".")
            lines.append(f"- **{ep_stem}**: `{ep}` and its imports")
        lines.append("")

    lines.append("### Exclude from Context")
    lines.append("")
    exclude_patterns = [
        "`**/*.pyc`",
        "`**/__pycache__/**`",
        "`**/.venv/**`",
        "`**/node_modules/**`",
        "`**/.web/**`",
        "`**/*-skills.md`",
        "`**/*-skills.json`",
        "`**/.clinerules*`",
    ]
    if project_type in ("django-app",):
        exclude_patterns.append("`**/migrations/**`")
    if "docker" in project_type or any("docker" in p for p in structure.get("patterns", [])):
        exclude_patterns.append("`**/docker-compose.override.yml`")

    for pat in exclude_patterns:
        lines.append(f"- {pat}")

    return "\n".join(lines)
