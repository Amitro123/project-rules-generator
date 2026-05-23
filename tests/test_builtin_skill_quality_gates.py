"""End-to-end quality gate over every shipped builtin skill.

Addresses recommendation #4 from the Manus code review (`manus CR.md`):
*"It would be beneficial to integrate this quality check directly into
the CI pipeline to ensure all new or modified skills meet defined
quality gates automatically."*

The pre-existing `tests/test_quality_checker_triggers.py` covers the
*flattening / robustness* of the validator on synthetic inputs. This
file does the opposite end: parametrizes ``validate_quality()`` over
**every actual `.md` file under ``generator/skills/builtin/``** and
asserts each one currently meets the PASS threshold (70/100).

Snapshot baseline (when this test was added): 12 skills at 100/100,
1 at 97/100. All pass. Test fails only when a contributor edits a
shipped builtin in a way that drops its score below 70.

Distinct from
``tests/test_remaining_cr_fixes.py::test_builtin_skill_frontmatter_has_when_trigger``
which checks a stricter frontmatter rule (every skill must have a
"When the user…" trigger line). That test pins one specific
frontmatter pattern; this test gates the FULL quality score.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from generator.utils.quality_checker import validate_quality

BUILTINS_DIR = Path(__file__).parent.parent / "generator" / "skills" / "builtin"


def _shipped_builtin_skill_files() -> List[Path]:
    """Every .md under generator/skills/builtin/ — both flat files and
    subdir SKILL.md files. Sorted so test IDs are deterministic across
    runs and platforms."""
    if not BUILTINS_DIR.exists():
        return []
    return sorted(p for p in BUILTINS_DIR.rglob("*.md") if p.is_file())


_SKILL_FILES = _shipped_builtin_skill_files()


@pytest.mark.parametrize(
    "skill_path",
    _SKILL_FILES,
    ids=lambda p: str(p.relative_to(BUILTINS_DIR)) if _SKILL_FILES else "no-skills",
)
def test_shipped_builtin_skill_passes_quality_gate(skill_path: Path):
    """Every shipped builtin must score ≥ 70 on ``validate_quality()``.

    If this test goes red, a recently-edited builtin skill dropped below
    the quality threshold. Either restore the missing structure
    (Purpose / Auto-Trigger / Process / Output sections, strategic-depth
    language) or — if the threshold is the wrong policy — adjust it
    centrally rather than carving an exception here."""
    content = skill_path.read_text(encoding="utf-8", errors="replace")
    report = validate_quality(content)
    rel = skill_path.relative_to(BUILTINS_DIR)
    assert report.passed, (
        f"Builtin skill {rel} scored {report.score:.0f}/100 (need ≥ 70).\n"
        f"Issues: {report.issues}\n"
        f"Warnings: {report.warnings}\n"
        f"Suggestions: {report.suggestions}"
    )


def test_at_least_one_builtin_skill_discovered():
    """Sanity guard: if generator/skills/builtin/ is empty or the rglob
    pattern breaks, the parametrize collects zero cases and the harness
    silently does nothing. Fail loudly in that scenario."""
    assert _SKILL_FILES, (
        f"No builtin skills found under {BUILTINS_DIR}. Either the "
        "directory was deleted or the discovery logic is broken."
    )
