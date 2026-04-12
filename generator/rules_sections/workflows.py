"""Workflow and README section builders."""

from __future__ import annotations

from typing import List


def _sanitize_readme_section(text: str, max_len: int = 500) -> str:
    """Trim README section content and ensure code blocks are balanced."""
    text = text[:max_len].strip()
    fence_count = text.count("```")
    if fence_count % 2 != 0:
        text += "\n```"
    return text


def _build_workflow_section(
    installation: str,
    usage: str,
    troubleshooting: str,
    test_framework: str,
    tech_stack: List[str],
) -> str:
    """Build workflow section from README content."""
    sections = []

    if installation:
        sections.append(f"### Setup\n{_sanitize_readme_section(installation)}")

    if usage:
        sections.append(f"### Usage\n{_sanitize_readme_section(usage)}")

    if troubleshooting:
        sections.append(f"### Troubleshooting\n{_sanitize_readme_section(troubleshooting, 300)}")

    dev_lines = ["### Development"]
    dev_lines.append("```bash")
    dev_lines.append("git checkout -b feat/descriptive-name")
    if test_framework == "pytest":
        dev_lines.append("# Write code + tests, then run:")
        dev_lines.append("pytest")
    elif test_framework == "jest":
        dev_lines.append("# Write code + tests, then run:")
        dev_lines.append("npx jest")
    else:
        dev_lines.append("# Write code + tests")
    dev_lines.append("git add .")
    dev_lines.append('git commit -m "feat: descriptive message"')
    dev_lines.append("```")
    sections.append("\n".join(dev_lines))

    return "\n\n".join(sections)
