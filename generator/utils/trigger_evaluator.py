"""
Trigger Evaluator
=================
Behavioral precision testing for skill triggers (GAP 6).

Tests whether a skill's trigger phrases correctly fire on relevant queries
and stay silent on unrelated ones. Target: >= 90% precision per Anthropic spec.
"""

import re
from dataclasses import dataclass, field
from typing import List

import yaml


@dataclass
class TriggerTestCase:
    """A single trigger precision test."""

    query: str
    should_fire: bool
    label: str = ""  # optional human-readable description


@dataclass
class TriggerReport:
    """Result of trigger precision evaluation."""

    precision: float  # 0.0 – 1.0
    passed: bool  # True when precision >= threshold
    total: int
    hits: int
    misses: List[str] = field(default_factory=list)
    triggers_found: List[str] = field(default_factory=list)


class TriggerEvaluator:
    """Test trigger precision: should-fire vs should-not-fire queries.

    Extracts trigger phrases embedded in the YAML frontmatter description
    (Anthropic spec format) and evaluates them against test cases.
    """

    PRECISION_THRESHOLD = 0.9

    def evaluate(
        self,
        skill_md: str,
        test_cases: List[TriggerTestCase],
        threshold: float = PRECISION_THRESHOLD,
    ) -> TriggerReport:
        """Evaluate trigger precision against a list of test cases.

        Args:
            skill_md: Full SKILL.md content (including frontmatter)
            test_cases: Queries with expected fire/no-fire behaviour
            threshold: Minimum precision to pass (default 0.9)

        Returns:
            TriggerReport with precision score and miss details
        """
        triggers = self.extract_triggers(skill_md)
        misses: List[str] = []
        hits = 0

        for tc in test_cases:
            fired = self._matches_any(tc.query, triggers)
            if fired == tc.should_fire:
                hits += 1
            else:
                label = tc.label or tc.query
                expected = "fire" if tc.should_fire else "not fire"
                actual = "fired" if fired else "did not fire"
                misses.append(f"{label!r}: expected {expected}, {actual}")

        total = len(test_cases)
        precision = hits / total if total > 0 else 0.0

        return TriggerReport(
            precision=precision,
            passed=precision >= threshold,
            total=total,
            hits=hits,
            misses=misses,
            triggers_found=triggers,
        )

    def auto_test_cases(self, skill_md: str) -> List[TriggerTestCase]:
        """Generate basic test cases from a skill's own frontmatter.

        Positive cases: extracted trigger phrases (should fire).
        Negative cases: phrases after "Do NOT activate for" (should not fire).

        Note: negative cases are only included when they don't overlap with
        any positive trigger phrase, since substring matching would otherwise
        produce false positives. Negative triggers are semantic hints for the
        LLM and require semantic evaluation beyond substring matching.
        """
        test_cases: List[TriggerTestCase] = []
        pos_triggers = self.extract_triggers(skill_md)

        for t in pos_triggers:
            test_cases.append(TriggerTestCase(query=t, should_fire=True, label=f"positive: {t!r}"))

        for t in self._extract_negative_triggers(skill_md):
            # Skip negative cases that contain a positive trigger — substring
            # matching would always fire on them, making the test meaningless.
            overlaps = any(pt.lower() in t.lower() for pt in pos_triggers)
            if not overlaps:
                test_cases.append(TriggerTestCase(query=t, should_fire=False, label=f"negative: {t!r}"))

        return test_cases

    @staticmethod
    def extract_triggers(skill_md: str) -> List[str]:
        """Extract positive trigger phrases from frontmatter description.

        Looks for the Anthropic-spec pattern:
            Use when user mentions "t1", "t2", "t3".
        """
        desc = TriggerEvaluator._get_description(skill_md)
        if not desc:
            return []
        match = re.search(r"mentions\s+(.+?)(?:\.\s*Do NOT|\.?\s*$)", desc, re.DOTALL)
        if not match:
            return []
        return re.findall(r'"([^"]+)"', match.group(1))

    @staticmethod
    def _extract_negative_triggers(skill_md: str) -> List[str]:
        """Extract negative trigger phrases from 'Do NOT activate for ...' clause."""
        desc = TriggerEvaluator._get_description(skill_md)
        if not desc:
            return []
        match = re.search(r"Do NOT activate for\s+(.+?)\.?\s*$", desc, re.DOTALL)
        if not match:
            return []
        return re.findall(r'"([^"]+)"', match.group(1))

    @staticmethod
    def _get_description(skill_md: str) -> str:
        """Extract description string from YAML frontmatter."""
        if not skill_md.startswith("---"):
            return ""
        parts = skill_md.split("---", 2)
        if len(parts) < 3:
            return ""
        try:
            fm = yaml.safe_load(parts[1])
            return str(fm.get("description", "")) if fm else ""
        except Exception:
            return ""

    @staticmethod
    def _matches_any(query: str, triggers: List[str]) -> bool:
        """Return True if any trigger phrase appears in the query (case-insensitive)."""
        q = query.lower()
        return any(t.lower() in q for t in triggers)
