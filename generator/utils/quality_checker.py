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
from typing import List, NamedTuple, Optional, Tuple

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


class _CheckResult(NamedTuple):
    """Return type for every private checker function."""

    penalty: float
    issues: List[str]
    warnings: List[str]
    suggestions: List[str]


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
    bold = re.findall(r'\*\*["\'"]?([^"\'*\n]+)["\'"]?\*\*', section)
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


def _strategic_depth_purpose_opening(purpose_section: str) -> _CheckResult:
    """Sub-check: does the Purpose section open with a feature description
    rather than the reader's pain? Skill writers default to
    'This skill generates X' — agents need 'Without X, you suffer Y' to
    know whether to activate."""
    first_sentence = purpose_section.split(".")[0].strip()
    if not _SHALLOW_PURPOSE_STARTS.match(first_sentence):
        return _CheckResult(0.0, [], [], [])
    return _CheckResult(
        15.0,
        [
            "Purpose opens with a feature description, not the reader's pain. "
            "Start with what the developer suffers WITHOUT this skill "
            "(e.g. 'Without X...', 'Every time you...', 'The common mistake is...')."
        ],
        [],
        [],
    )


def _strategic_depth_pain_indicators(purpose_section: str) -> _CheckResult:
    """Sub-check: pain-indicator language in the Purpose section. Even if
    the opening sentence is fine, the body should name a specific
    mistake/gap so agents have something to match against."""
    purpose_lower = purpose_section.lower()
    if any(indicator in purpose_lower for indicator in _PAIN_INDICATORS):
        return _CheckResult(0.0, [], [], [])
    return _CheckResult(
        10.0,
        [],
        [
            "Purpose lacks pain-oriented language. "
            "Name the specific mistake or gap the reader has WITHOUT this skill."
        ],
        [],
    )


def _strategic_depth_process_reasoning(content: str) -> _CheckResult:
    """Sub-check: do Process steps include a 'why' sentence before
    commands? A skill that jumps to `pytest -v` without explaining
    what failure it prevents is hard for agents to use correctly."""
    if "## Process" not in content:
        return _CheckResult(0.0, [], [], [])
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
    if total_steps == 0 or steps_with_reasoning > 0:
        return _CheckResult(0.0, [], [], [])
    return _CheckResult(
        5.0,
        [],
        [],
        [
            "Process steps jump straight to commands with no reasoning. "
            "Add one 'why' sentence per step explaining what failure it prevents."
        ],
    )


def _check_strategic_depth(content: str) -> Tuple[List[str], List[str], List[str], float]:
    """Check for strategic depth: pain identification and why-before-how reasoning.

    Returns (issues, warnings, suggestions, penalty).

    Thin orchestrator over three sub-checks; the 4-tuple return shape is
    preserved for callers that don't yet use _CheckResult.
    """
    if "## Purpose" not in content:
        return [], [], [], 0.0  # already caught by required-sections check

    purpose_section = re.split(r"\n## ", content.split("## Purpose", 1)[1])[0].strip()

    sub_results = [
        _strategic_depth_purpose_opening(purpose_section),
        _strategic_depth_pain_indicators(purpose_section),
        _strategic_depth_process_reasoning(content),
    ]

    return (
        [i for r in sub_results for i in r.issues],
        [w for r in sub_results for w in r.warnings],
        [s for r in sub_results for s in r.suggestions],
        sum(r.penalty for r in sub_results),
    )


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


# ---------------------------------------------------------------------------
# Private checker functions — each returns a _CheckResult(penalty, issues,
# warnings, suggestions).  validate_quality() calls them in sequence and
# accumulates the results.
# ---------------------------------------------------------------------------


def _parse_and_extract_metadata(
    content: str,
    metadata_triggers: Optional[List[str]],
    metadata_tools: Optional[List[str]],
) -> Tuple[dict, List[str], List[str]]:
    """Auto-parse frontmatter when callers don't provide triggers/tools.

    Returns (meta, resolved_triggers, resolved_tools).
    """
    meta: dict = {}
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

    return meta, metadata_triggers, metadata_tools


def _check_required_sections(content: str) -> _CheckResult:
    """Deduct 15 points per missing required section."""
    issues: List[str] = []
    penalty = 0.0
    for section in SKILL_REQUIRED_SECTIONS:
        if section not in content:
            penalty += 15
            issues.append(f"Missing section: {section}")
    return _CheckResult(penalty, issues, [], [])


def _check_stub_markers(content: str) -> _CheckResult:
    """Deduct 30 points if generic stub placeholders are detected."""
    if is_stub_content(content):
        return _CheckResult(30.0, ["Content contains generic stub placeholders"], [], [])
    return _CheckResult(0.0, [], [], [])


def _check_triggers(triggers: List[str]) -> _CheckResult:
    """Deduct 10 points for < 2 triggers; suggest adding more for < 3."""
    if len(triggers) < 2:
        return _CheckResult(
            10.0,
            [],
            [f"Only {len(triggers)} auto-triggers (recommend 3+)"],
            [],
        )
    if len(triggers) < 3:
        return _CheckResult(0.0, [], [], ["Consider adding more trigger variations"])
    return _CheckResult(0.0, [], [], [])


def _check_tools(content: str, tools: List[str]) -> _CheckResult:
    """Deduct for missing tools list or tools specified as a string instead of YAML list."""
    issues: List[str] = []
    warnings: List[str] = []
    penalty = 0.0

    if not tools:
        penalty += 10
        warnings.append("No tools specified")

    # Check allowed-tools is a YAML list, not a quoted string.
    # A quoted string still works (we split() it) but diverges from the documented
    # contract and will propagate the bad pattern to generated skills.
    meta_for_tools, _ = _parse_frontmatter(content)
    raw_tools_value = meta_for_tools.get("tools") or meta_for_tools.get("allowed-tools")
    if isinstance(raw_tools_value, str) and raw_tools_value.strip():
        penalty += 5
        warnings.append(
            "allowed-tools is a quoted string, not a YAML list. "
            "Use a YAML list (- Bash\\n  - Read ...) so the schema is consistent."
        )

    return _CheckResult(penalty, issues, warnings, [])


def _check_description_when_trigger(desc_lines: List[str]) -> _CheckResult:
    """Sub-check: every skill needs at least one 'When ...' trigger line so
    agents know when to activate. Without it, the matcher has no signal."""
    has_when_trigger = any(ln.lower().startswith("when") for ln in desc_lines)
    if has_when_trigger:
        return _CheckResult(0.0, [], [], [])
    return _CheckResult(
        10.0,
        [
            "description frontmatter lacks 'When ...' trigger phrases. "
            "Each line should start with 'When the user ...' so agents know when to activate."
        ],
        [],
        [],
    )


def _check_description_primary_length(desc_lines: List[str]) -> _CheckResult:
    """Sub-check: the 'real' description (first non-trigger line) should be
    a full sentence, not a label fragment. Skills with a 20-char description
    are unhelpful to agents."""
    non_when_lines = [
        ln for ln in desc_lines if not ln.lower().startswith("when") and not ln.lower().startswith("do not")
    ]
    primary_desc = non_when_lines[0] if non_when_lines else (desc_lines[0] if desc_lines else "")
    if not primary_desc or len(primary_desc) >= 40:
        return _CheckResult(0.0, [], [], [])
    return _CheckResult(
        5.0,
        [],
        [
            f"description is too terse ('{primary_desc[:60]}'). "
            "Expand to a full sentence explaining what the skill does and why it matters."
        ],
        [],
    )


def _check_description_whitespace_leak(desc_value: object) -> _CheckResult:
    """Sub-check: leading/trailing whitespace like '  workflow for this project'
    is almost always a generator-template fill bug — the placeholder didn't
    get stripped."""
    if not isinstance(desc_value, str) or desc_value == desc_value.strip():
        return _CheckResult(0.0, [], [], [])
    return _CheckResult(
        3.0,
        [],
        ["description has leading/trailing whitespace — template-fill bug"],
        [],
    )


def _check_description(content: str, meta: dict) -> _CheckResult:
    """Check description frontmatter for When-trigger lines, length, and whitespace.

    Thin orchestrator: prepares the parsed inputs once, then composes three
    independent sub-checks. Each sub-check is small (CC ≤ 4) and unit-
    testable on its own; this function stays in radon's A band.
    """
    if not meta:
        meta, _ = _parse_frontmatter(content)

    desc_value = meta.get("description", "")
    if not desc_value:
        return _CheckResult(0.0, [], [], [])

    desc_str = str(desc_value).strip()
    desc_lines = [ln.strip() for ln in desc_str.splitlines() if ln.strip()]

    sub_results = [
        _check_description_when_trigger(desc_lines),
        _check_description_primary_length(desc_lines),
        _check_description_whitespace_leak(desc_value),
    ]

    return _CheckResult(
        penalty=sum(r.penalty for r in sub_results),
        issues=[i for r in sub_results for i in r.issues],
        warnings=[w for r in sub_results for w in r.warnings],
        suggestions=[s for r in sub_results for s in r.suggestions],
    )


def _check_content_length(content: str) -> _CheckResult:
    """Deduct for content that is too short."""
    if len(content) < 200:
        return _CheckResult(20.0, ["Content too short (< 200 chars)"], [], [])
    if len(content) < 500:
        return _CheckResult(5.0, [], ["Content is brief - consider expanding"], [])
    return _CheckResult(0.0, [], [], [])


def _check_process_steps(content: str) -> _CheckResult:
    """Deduct 10 points if ## Process has fewer than 2 numbered steps."""
    if "## Process" not in content:
        return _CheckResult(0.0, [], [], [])
    # Use regex split on "\n## " to avoid splitting on "### " sub-section headers
    process_section = re.split(r"\n## ", content.split("## Process", 1)[1])[0]
    step_count = len(re.findall(r"(?:^\s*\d+\.|^#{2,3}\s+\d+\.)", process_section, re.MULTILINE))
    if step_count < 2:
        return _CheckResult(10.0, [], ["Process section has fewer than 2 numbered steps"], [])
    return _CheckResult(0.0, [], [], [])


def _check_placeholders(content: str) -> _CheckResult:
    """Deduct for bracket placeholders, sentinels, and generic path placeholders."""
    issues: List[str] = []
    penalty = 0.0

    # Check for placeholder text.
    # Bracket-style markers use substring match — they can't appear legitimately
    # in real skill content.
    # Sentinel tokens (TODO, FIXME, XXX) use strict word-boundary + uppercase-only
    # match so that tool names like "TodoWrite" or "fixme-up" don't trigger false
    # positives.
    bracket_placeholders = ["[describe", "[example", "[your", "[add", "[insert"]
    for placeholder in bracket_placeholders:
        if placeholder.lower() in content.lower():
            issues.append(f"Contains placeholder: {placeholder}")
            penalty += 10

    sentinel_placeholders = ["TODO", "FIXME", "XXX"]
    for sentinel in sentinel_placeholders:
        if re.search(rf"\b{sentinel}\b", content):  # case-sensitive, word boundary
            issues.append(f"Contains placeholder: {sentinel}")
            penalty += 10

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
        penalty += min(len(_unique_placeholders) * 5, 25)
        issues.append(
            f"Contains {len(_unique_placeholders)} unfilled bracket placeholder(s) "
            f'(e.g. "{_unique_placeholders[0]}") — fill in or remove before using'
        )

    # Check for generic path placeholders
    if "cd project_name" in content or "cd /path/to" in content:
        issues.append("Contains generic path placeholders")
        penalty += 15

    return _CheckResult(penalty, issues, [], [])


def _check_code_and_antipatterns(content: str) -> _CheckResult:
    """Check for code examples and anti-patterns section."""
    warnings: List[str] = []
    suggestions: List[str] = []
    penalty = 0.0

    if "```" not in content and "bash" not in content.lower():
        warnings.append("No code examples found (skill may not be actionable)")
        penalty += 10

    if "## Anti-Patterns" not in content:
        suggestions.append("Add anti-patterns section")
        penalty += 5

    return _CheckResult(penalty, [], warnings, suggestions)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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
    meta, triggers, tools = _parse_and_extract_metadata(content, metadata_triggers, metadata_tools)

    checkers = [
        _check_required_sections(content),
        _check_stub_markers(content),
        _check_triggers(triggers),
        _check_tools(content, tools),
        _check_description(content, meta),
        _check_content_length(content),
        _check_process_steps(content),
        _check_placeholders(content),
        _check_code_and_antipatterns(content),
    ]

    score = 100.0
    issues: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []

    for result in checkers:
        score -= result.penalty
        issues.extend(result.issues)
        warnings.extend(result.warnings)
        suggestions.extend(result.suggestions)

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
