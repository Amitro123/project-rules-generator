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


class TriggerEvaluator:
    """Test trigger precision: should-fire vs should-not-fire queries.

    Extracts trigger phrases embedded in the YAML frontmatter description
    (Anthropic spec format) and evaluates them against test cases.
    """

    PRECISION_THRESHOLD = 0.9

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
        except (yaml.YAMLError, OSError):
            return ""

    @staticmethod
    def _matches_any(query: str, triggers: List[str]) -> bool:
        """Return True if any trigger phrase appears in the query (case-insensitive)."""
        q = query.lower()
        return any(t.lower() in q for t in triggers)
