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
from typing import List, Optional, Tuple

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
    except OSError:
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
        fake_count = sum(1 for ref in file_refs if not (project_path / ref.split(":")[0]).exists())
        if fake_count > 0 and fake_count >= len(file_refs) / 2:
            return True

    return False


def is_stub_content(content: str) -> bool:
    """
    Check if skill content (as string) is a generic stub.
    Useful when you have content but no file path.
    """
    return any(marker in content for marker in STUB_MARKERS)


def _parse_frontmatter(content: str):
    """Extract YAML frontmatter dict and markdown body from skill content.

    Returns (meta_dict, body_str). If no frontmatter, meta_dict is {}.
    """
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    yaml_block = content[3:end].strip()
    body = content[end + 4:]
    try:
        import yaml

        meta = yaml.safe_load(yaml_block) or {}
    except Exception:
        meta = {}
    return meta if isinstance(meta, dict) else {}, body


def _extract_body_triggers(content: str) -> List[str]:
    """Extract trigger phrases from the ## Auto-Trigger markdown section.

    Tries bold phrases first (**"phrase"** or **phrase**); falls back to plain
    bullet-list items so skills that don't use bold formatting still count.
    """
    if "## Auto-Trigger" not in content:
        return []
    section = re.split(r"\n## ", content.split("## Auto-Trigger", 1)[1])[0]
    # Prefer bold phrases: **"phrase"** or **phrase**
    bold = re.findall(r'\*\*["\']?([^"\'*\n]+)["\']?\*\*', section)
    if bold:
        return bold
    # Fall back to plain bullet items: "- phrase" or "* phrase"
    bullets = re.findall(r"^[-*]\s+(.+)", section, re.MULTILINE)
    return [b.strip() for b in bullets if b.strip()]


# Patterns that signal a Purpose section is describing the skill's features
# instead of the reader's pain.  Any match → shallow purpose penalty.
_SHALLOW_PURPOSE_STARTS = re.compile(
    r"^(this skill|this command|this generates|this provides|this tool|automatically)",
    re.IGNORECASE,
)

# Words that signal the Purpose identifies a pain point or broken state.
# At least one must appear somewhere in the Purpose section.
_PAIN_INDICATORS = [
    "without",
    "instead of",
    "every time you",
    "the problem",
    "common mistake",
    "developers often",
    "when you don't",
    "stops you",
    "prevents",
    "avoids",
    "before you",
    "if you don't",
    "wrong way",
    "inconsistent",
    "broken",
    "forgotten",
    "missed",
    "skip",
    "missing",
    "difficult to",
    "hard to",
    "easy to forget",
]


def _check_strategic_depth(content: str) -> Tuple[List[str], List[str], List[str], float]:
    """Check for strategic depth: pain identification and why-before-how reasoning.

    Returns (issues, warnings, suggestions, penalty).
    """
    issues: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []
    penalty = 0.0

    if "## Purpose" not in content:
        return issues, warnings, suggestions, penalty  # already caught by required-sections check

    purpose_section = re.split(r"\n## ", content.split("## Purpose", 1)[1])[0].strip()
    first_sentence = purpose_section.split(".")[0].strip()

    # Check: does Purpose open with a feature description rather than reader's pain?
    if _SHALLOW_PURPOSE_STARTS.match(first_sentence):
        issues.append(
            "Purpose opens with a feature description, not the reader's pain. "
            "Start with what the developer suffers WITHOUT this skill "
            "(e.g. 'Without X...', 'Every time you...', 'The common mistake is...')."
        )
        penalty += 15.0

    # Check: does Purpose contain any pain-indicator language?
    purpose_lower = purpose_section.lower()
    if not any(indicator in purpose_lower for indicator in _PAIN_INDICATORS):
        warnings.append(
            "Purpose lacks pain-oriented language. "
            "Name the specific mistake or gap the reader has WITHOUT this skill."
        )
        penalty += 10.0

    # Check: do Process steps include a 'why' sentence before commands?
    if "## Process" in content:
        process_section = re.split(r"\n## ", content.split("## Process", 1)[1])[0]
        step_blocks = re.split(r"(?:^|\n)#{2,3}\s+\d+\.", process_section)
        steps_with_reasoning = 0
        for block in step_blocks[1:]:  # skip leading empty segment
            prose_before_code = block.split("```")[0].strip()
            prose_lines = [
                ln for ln in prose_before_code.splitlines()
                if ln.strip() and not ln.strip().startswith(("-", "*", "#", "|"))
            ]
            if prose_lines:
                steps_with_reasoning += 1
        total_steps = len(step_blocks) - 1
        if total_steps > 0 and steps_with_reasoning == 0:
            suggestions.append(
                "Process steps jump straight to commands with no reasoning. "
                "Add one 'why' sentence per step explaining what failure it prevents."
            )
            penalty += 5.0

    return issues, warnings, suggestions, penalty


def validate_quality(
    content: str,
    metadata_triggers: Optional[List[str]] = None,
    metadata_tools: Optional[List[str]] = None,
) -> QualityReport:
    """
    Validate the quality of generated skill content.

    Consolidated from CoworkSkillCreator._validate_quality().

    Args:
        content: The skill markdown content
        metadata_triggers: List of auto-trigger phrases (auto-parsed if omitted)
        metadata_tools: List of tools (auto-parsed if omitted)

    Returns:
        QualityReport with score, issues, warnings, suggestions
    """
    score = 100.0
    issues = []
    warnings = []
    suggestions = []

    # Auto-parse frontmatter when callers don't provide metadata
    if metadata_triggers is None or metadata_tools is None:
        meta, _ = _parse_frontmatter(content)
        if metadata_triggers is None:
            # Prefer explicit YAML triggers list; fall back to body parsing
            yaml_triggers = meta.get("triggers") or meta.get("auto_triggers") or []
            if isinstance(yaml_triggers, list):
                # Flatten list-of-dicts (auto_triggers: [{keywords: [...]}]) or plain list
                flat: List[str] = []
                for item in yaml_triggers:
                    if isinstance(item, dict):
                        flat.extend(item.get("keywords") or [])
                    elif isinstance(item, str):
                        flat.append(item)
                yaml_triggers = flat
            body_triggers = _extract_body_triggers(content)
            # Merge both sources; yaml takes precedence for deduplication ordering
            metadata_triggers = list(dict.fromkeys(yaml_triggers + body_triggers))
        if metadata_tools is None:
            raw_tools = meta.get("tools") or meta.get("allowed-tools") or []
            if isinstance(raw_tools, str):
                # "Bash Read Write Edit Glob Grep" → list
                raw_tools = raw_tools.split()
            metadata_tools = raw_tools if isinstance(raw_tools, list) else []

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
        warnings.append(f"Only {len(triggers)} auto-triggers (recommend 3+)")
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

    # Check for actionable steps — match "1. foo" OR "### 1. Foo" (Jinja2 template format)
    # Use regex split on "\n## " to avoid splitting on "### " sub-section headers
    if "## Process" in content:
        process_section = re.split(r"\n## ", content.split("## Process", 1)[1])[0]
        step_count = len(re.findall(r"(?:^\s*\d+\.|^#{2,3}\s+\d+\.)", process_section, re.MULTILINE))
        if step_count < 2:
            score -= 10
            warnings.append("Process section has fewer than 2 numbered steps")

    # Check for placeholder text.
    # Bracket-style markers ("[describe", "[your", …) use substring match — they can't
    # appear legitimately in real skill content.
    # Sentinel tokens (TODO, FIXME, XXX) use strict word-boundary + uppercase-only match
    # so that tool names like "TodoWrite" or "fixme-up" don't trigger false positives.
    bracket_placeholders = ["[describe", "[example", "[your", "[add", "[insert"]
    for placeholder in bracket_placeholders:
        if placeholder.lower() in content.lower():
            issues.append(f"Contains placeholder: {placeholder}")
            score -= 10

    sentinel_placeholders = ["TODO", "FIXME", "XXX"]
    for sentinel in sentinel_placeholders:
        if re.search(rf"\b{sentinel}\b", content):  # case-sensitive, word boundary
            issues.append(f"Contains placeholder: {sentinel}")
            score -= 10

    # General bracket-placeholder detection — catches patterns not covered by the
    # specific list above (e.g. StubStrategy output: "[First step]", "[description]",
    # "[One sentence: what problem does this solve and for whom.]").
    # Strip frontmatter and code blocks first to avoid flagging YAML arrays or
    # code syntax like Dict[str, int].
    _, _body = _parse_frontmatter(content)
    _body_no_code = re.sub(r"```.*?```", "", _body, flags=re.DOTALL)
    _specific_prefixes = {p.lstrip("[").lower() for p in bracket_placeholders}
    _general_placeholders = [
        m for m in re.findall(r"\[([^\]]{5,})\](?!\()", _body_no_code)
        if not any(m.lower().startswith(sp) for sp in _specific_prefixes)
    ]
    if _general_placeholders:
        _unique_placeholders = list(dict.fromkeys(_general_placeholders))
        score -= min(len(_unique_placeholders) * 5, 25)
        issues.append(
            f"Contains {len(_unique_placeholders)} unfilled bracket placeholder(s) "
            f"(e.g. \"{_unique_placeholders[0]}\") — fill in or remove before using"
        )

    # Check for generic path placeholders
    if "cd project_name" in content or "cd /path/to" in content:
        issues.append("Contains generic path placeholders")
        score -= 15

    # Check for code examples
    if "```" not in content and "bash" not in content.lower():
        warnings.append("No code examples found (skill may not be actionable)")
        score -= 10

    # Check for anti-patterns section
    if "## Anti-Patterns" not in content:
        suggestions.append("Add anti-patterns section")
        score -= 5

    # Strategic depth: pain-first purpose + why-before-how reasoning
    depth_issues, depth_warnings, depth_suggestions, depth_penalty = _check_strategic_depth(content)
    issues.extend(depth_issues)
    warnings.extend(depth_warnings)
    suggestions.extend(depth_suggestions)
    score -= depth_penalty

    score = max(0.0, score)
    passed = score >= 70.0

    return QualityReport(
        score=score,
        passed=passed,
        issues=issues,
        warnings=warnings,
        suggestions=suggestions,
    )
