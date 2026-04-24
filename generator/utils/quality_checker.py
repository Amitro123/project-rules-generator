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

from generator.types import SKILL_REQUIRED_SECTIONS

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

    # 1a. Bug H guard: distinctive-placeholder-phrase check catches stale
    # files that carry variants of the stub markers (e.g. "[One sentence:
    # … and for whom.]" vs the canonical STUB_MARKERS entry). Strip fenced
    # code blocks first so the meta writing-skills builtin, which
    # legitimately demonstrates the skill template inside a ```markdown```
    # block, is not false-flagged, and real skills that embed Python/JS
    # code with dict-access (`['key']`) or tag arrays (`[a, b, c]`) are
    # not flagged either.
    without_code_blocks = re.sub(r"```[\s\S]*?```", "", content)
    if _count_placeholder_phrases(without_code_blocks) >= 2:
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
    if any(marker in content for marker in STUB_MARKERS):
        return True
    # Bug H: distinctive-placeholder-phrase check (see is_stub() for rationale).
    without_code_blocks = re.sub(r"```[\s\S]*?```", "", content)
    return _count_placeholder_phrases(without_code_blocks) >= 2


# Distinctive phrases that only appear in the unfilled PRG skill template.
# Matching two or more indicates the file was never filled in — dict access
# (`['contents']`) and tag arrays (`[tag1, tag2, tag3]`) cannot match any
# of these patterns.
_PLACEHOLDER_PATTERNS = (
    r"\[One sentence:",
    r"\[First step\]",
    r"\[Second step\]",
    r"\[Third step\]",
    r"\[What NOT to do\]",
    r"\[What to do instead\]",
    r"\[What artifact",
    r"\[list false-positive",
    r"\[description\]",
    r"\[log data here\]",
    r"\[Insert ",
    r"\[Replace with",
    r"\[Your project",
    r"\[Describe (?:what|how|why)",
)
_PLACEHOLDER_RE = re.compile("|".join(_PLACEHOLDER_PATTERNS))


def _count_placeholder_phrases(text: str) -> int:
    """Count distinctive unfilled-template phrases in text."""
    return len(_PLACEHOLDER_RE.findall(text))


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
    body = content[end + 4 :]
    try:
        import yaml

        meta = yaml.safe_load(yaml_block) or {}
    except (ValueError, TypeError):
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
    "prevent",
    "avoids",
    "avoid",
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
    # Added (Batch D / Fix 4): real pain-oriented phrasing that the narrow
    # original list was rejecting. Empirically 69% of generated skills were
    # penalised for "lack of pain language" despite having legitimate pain
    # framing via these phrases.
    "ensure consistent",
    "ensure correct",
    "tedious",
    "error-prone",
    "error prone",
    "bug-prone",
    "bug prone",
    "brittle",
    "regression",
    "risk of",
    "at risk",
    "stale",
    "outdated",
    "out of sync",
    "out-of-sync",
    "drift",
    "silently",
    "ship broken",
    "break production",
    "breaks production",
    "catch bugs",
    "catches bugs",
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
                ln
                for ln in prose_before_code.splitlines()
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


# Keys of a dict-shaped `auto_triggers:` block whose values are themselves
# lists of trigger phrases. `project_signals` is included because real skills
# (see .clinerules/skills/learned/deadcode) put signal names like
# `has_tests` there and the scorer has historically treated them as triggers.
_TRIGGER_DICT_LIST_KEYS = ("keywords", "phrases", "project_signals")


def _flatten_trigger_spec(spec) -> List[str]:
    """Normalise a frontmatter `auto_triggers`/`triggers` value to a flat list of strings.

    Handles three shapes found in real skills:
      * list of strings — returned as-is
      * list of dicts with `keywords:` sub-lists — flattened
      * dict with `keywords:` / `phrases:` / `project_signals:` sub-lists —
        flattened (this is the shape the generator emits for most skills)

    Any other shape returns [].
    """
    if isinstance(spec, list):
        flat: List[str] = []
        for item in spec:
            if isinstance(item, dict):
                for key in _TRIGGER_DICT_LIST_KEYS:
                    values = item.get(key)
                    if isinstance(values, list):
                        flat.extend(str(v) for v in values if v)
            elif isinstance(item, str):
                flat.append(item)
        return flat
    if isinstance(spec, dict):
        flat = []
        for key in _TRIGGER_DICT_LIST_KEYS:
            values = spec.get(key)
            if isinstance(values, list):
                flat.extend(str(v) for v in values if v)
        return flat
    return []


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
            # Prefer explicit YAML triggers list; fall back to body parsing.
            # Three shapes are valid in the wild:
            #   1) auto_triggers: [foo, bar]                     — plain list
            #   2) auto_triggers: [{keywords: [foo, bar]}, ...]  — list of dicts
            #   3) auto_triggers: {keywords: [foo], project_signals: [has_tests]}
            #      — dict with keyword + signal sub-lists (generator-template shape)
            # Previously shape (3) raised TypeError on `dict + list` concat, which
            # silently made 9 real skills unscoreable. Normalise all three here.
            yaml_triggers = meta.get("triggers") or meta.get("auto_triggers") or []
            yaml_triggers = _flatten_trigger_spec(yaml_triggers)
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
    for section in SKILL_REQUIRED_SECTIONS:
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

    # Check allowed-tools is a YAML list, not a quoted string
    # A quoted string still works (we split() it) but diverges from the documented
    # contract and will propagate the bad pattern to generated skills.
    meta_for_tools, _ = _parse_frontmatter(content)
    raw_tools_value = meta_for_tools.get("tools") or meta_for_tools.get("allowed-tools")
    if isinstance(raw_tools_value, str) and raw_tools_value.strip():
        score -= 5
        warnings.append(
            "allowed-tools is a quoted string, not a YAML list. "
            "Use a YAML list (- Bash\\n  - Read ...) so the schema is consistent."
        )

    # Check description frontmatter contains When … trigger phrases
    # The description field is the machine-readable trigger source for agents.
    # It must contain at least one line starting with "When" so agents know when to activate.
    desc_value = meta_for_tools.get("description", "")
    if desc_value:
        desc_str = str(desc_value).strip()
        desc_lines = [ln.strip() for ln in desc_str.splitlines() if ln.strip()]
        has_when_trigger = any(ln.lower().startswith("when") for ln in desc_lines)
        if not has_when_trigger:
            score -= 10
            issues.append(
                "description frontmatter lacks 'When ...' trigger phrases. "
                "Each line should start with 'When the user ...' so agents know when to activate."
            )

        # Skills with a single terse description line (e.g. "QA finder for this project",
        # "cleanup workflow for this project", or the literal "# Requires GEMINI_API_KEY"
        # caught in the OSS audit) are unhelpful to agents and embarrassing to ship.
        # Require at least ~40 characters of substantive description before the trigger
        # lines. Penalise leading/trailing whitespace artefacts too.
        # Prefer the first non-"when" line as the "real" description.
        non_when_lines = [
            ln for ln in desc_lines if not ln.lower().startswith("when") and not ln.lower().startswith("do not")
        ]
        primary_desc = non_when_lines[0] if non_when_lines else (desc_lines[0] if desc_lines else "")
        if primary_desc and len(primary_desc) < 40:
            score -= 5
            warnings.append(
                f"description is too terse ('{primary_desc[:60]}'). "
                "Expand to a full sentence explaining what the skill does and why it matters."
            )
        if isinstance(desc_value, str) and desc_value != desc_value.strip():
            # Leading/trailing whitespace like "  workflow for this project" is a
            # generator-template leak. Flag it so the bug gets noticed.
            score -= 3
            warnings.append("description has leading/trailing whitespace — template-fill bug")

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
        m
        for m in re.findall(r"\[([^\]]{5,})\](?!\()", _body_no_code)
        if not any(m.lower().startswith(sp) for sp in _specific_prefixes)
    ]
    if _general_placeholders:
        _unique_placeholders = list(dict.fromkeys(_general_placeholders))
        score -= min(len(_unique_placeholders) * 5, 25)
        issues.append(
            f"Contains {len(_unique_placeholders)} unfilled bracket placeholder(s) "
            f'(e.g. "{_unique_placeholders[0]}") — fill in or remove before using'
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
