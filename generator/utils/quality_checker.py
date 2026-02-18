"""
Quality Checker Utilities
=========================
Consolidated quality checking logic from:
- generator/skill_generator.py (_is_generic_stub)
- generator/skill_creator.py (QualityReport, _validate_quality)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# Markers that indicate a skill is a generic stub (not project-specific)
STUB_MARKERS = [
    "Follow project conventions",
    "Patterns and best practices for",
    "[One sentence: what problem does this solve]",
    "[When should agent activate this skill]",
    "[Step-by-step instructions]",
    "Working with general code",
    "Add tests for new functionality",
]


@dataclass
class QualityReport:
    """Quality assessment of a generated skill."""
    score: float
    passed: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


def is_stub(filepath: Path, project_path: Optional[Path] = None) -> bool:
    """
    Check if a skill file is a generic stub or contains hallucinations.

    Consolidated from SkillGenerator._is_generic_stub().

    Args:
        filepath: Path to the SKILL.md file
        project_path: Optional project root for hallucination detection

    Returns:
        True if the skill is a generic stub or contains hallucinations
    """
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False

    # 1. Generic stub markers
    if any(marker in content for marker in STUB_MARKERS):
        return True

    # 2. Hallucinated file path detection
    hallucinated_paths = re.findall(r"(?:File:\s*)?src/[\w/]+\.py(?::\d+)?", content)
    if hallucinated_paths and project_path:
        src_dir = project_path / "src"
        if not src_dir.exists():
            return True

    # 3. Detect fake file path patterns in code blocks
    file_refs = re.findall(r"#\s*File:\s*(\S+)", content)
    if file_refs and project_path:
        fake_count = sum(
            1 for ref in file_refs
            if not (project_path / ref.split(":")[0]).exists()
        )
        if fake_count > 0 and fake_count >= len(file_refs) / 2:
            return True

    return False


def is_stub_content(content: str) -> bool:
    """
    Check if skill content (as string) is a generic stub.
    Useful when you have content but no file path.
    """
    return any(marker in content for marker in STUB_MARKERS)


def validate_quality(
    content: str,
    metadata_triggers: List[str] = None,
    metadata_tools: List[str] = None,
) -> QualityReport:
    """
    Validate the quality of generated skill content.

    Consolidated from CoworkSkillCreator._validate_quality().

    Args:
        content: The skill markdown content
        metadata_triggers: List of auto-trigger phrases
        metadata_tools: List of tools

    Returns:
        QualityReport with score, issues, warnings, suggestions
    """
    score = 100.0
    issues = []
    warnings = []
    suggestions = []

    # Check required sections
    required_sections = ["## Purpose", "## Auto-Trigger", "## Process", "## Output"]
    for section in required_sections:
        if section not in content:
            score -= 15
            issues.append(f"Missing section: {section}")

    # Check for stub markers
    if is_stub_content(content):
        score -= 30
        issues.append("Content contains generic stub placeholders")

    # Check triggers
    triggers = metadata_triggers or []
    if len(triggers) < 2:
        score -= 10
        warnings.append("Too few auto-triggers (recommend 3+)")
    elif len(triggers) < 3:
        suggestions.append("Consider adding more trigger variations")

    # Check tools
    tools = metadata_tools or []
    if not tools:
        score -= 10
        warnings.append("No tools specified")

    # Check content length
    if len(content) < 200:
        score -= 20
        issues.append("Content too short (< 200 chars)")
    elif len(content) < 500:
        score -= 5
        warnings.append("Content is brief - consider expanding")

    # Check for actionable steps
    if "## Process" in content:
        process_section = content.split("## Process")[1].split("##")[0]
        step_count = len(re.findall(r"^\s*\d+\.", process_section, re.MULTILINE))
        if step_count < 2:
            score -= 10
            warnings.append("Process section has fewer than 2 numbered steps")

    score = max(0.0, score)
    passed = score >= 70.0

    return QualityReport(
        score=score,
        passed=passed,
        issues=issues,
        warnings=warnings,
        suggestions=suggestions,
    )
