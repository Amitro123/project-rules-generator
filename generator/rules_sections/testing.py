"""Test section builder."""

from __future__ import annotations

from typing import Dict, List, Optional


def _build_test_section(
    test_framework: str,
    test_files: int,
    test_info: Dict,
    python_deps: Optional[List[str]] = None,
    node_deps: Optional[List[str]] = None,
) -> str:
    """Build testing section from actual test analysis."""
    lines = []
    test_cases = test_info.get("test_cases", 0)

    # Dep-fallback: if analyzer missed the framework, infer from deps
    if not test_framework:
        all_deps = list(python_deps or []) + list(node_deps or [])
        if any("pytest" in d for d in all_deps):
            test_framework = "pytest"
        elif any("jest" in d or "vitest" in d for d in all_deps):
            test_framework = "jest"

    if test_framework:
        lines.append(f"- **Framework**: {test_framework}")
        counts = str(test_files)
        if test_cases:
            counts += f" ({test_cases} test cases)"
        lines.append(f"- **Test files**: {counts}")
        test_patterns = test_info.get("patterns", [])
        if test_patterns:
            lines.append(f"- **Test types**: {', '.join(test_patterns)}")
        if test_info.get("has_conftest"):
            lines.append("- **Fixtures**: shared via `conftest.py`")
        if test_info.get("has_fixtures"):
            lines.append("- **Test data**: `tests/fixtures/` directory")

        if test_framework == "pytest":
            lines.append("\n```bash")
            lines.append("# Run all tests")
            lines.append("pytest")
            lines.append("# Run with coverage")
            lines.append("pytest --cov")
            lines.append("# Run specific test file")
            lines.append("pytest tests/test_specific.py -v")
            lines.append("```")
        elif test_framework == "jest":
            lines.append("\n```bash")
            lines.append("npx jest")
            lines.append("npx jest --coverage")
            lines.append("```")
    else:
        lines.append("- No test framework detected")

    return "\n".join(lines)
