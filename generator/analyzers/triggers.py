import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set

from generator.types import Skill


class SkillTriggerDetector:
    """
    Detects which skills should be active based on project context
    and skill auto-trigger definitions.
    """

    def __init__(self, project_path: Path, project_context: Dict[str, Any]):
        self.project_path = project_path
        self.context = project_context
        self._cache_file_list: List[str] = []
        self._load_file_list()

    def _load_file_list(self):
        """Cache list of files for pattern matching."""
        _SKIP_DIRS = {".git", "node_modules", "venv", "__pycache__", ".venv"}
        try:
            for root, dirs, files in os.walk(self.project_path):
                dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
                rel_root = Path(root).relative_to(self.project_path)
                for file in files:
                    self._cache_file_list.append(str(rel_root / file).replace("\\", "/"))
        except OSError:
            pass

    def _get_tech_stack_set(self) -> Set[str]:
        """Extract tech stack as a flat set of lowercase strings."""
        ts = self.context.get("tech_stack", [])
        if isinstance(ts, dict):
            # Flatten dict values
            flat_list: List[str] = sum(ts.values(), [])
            return {t.lower() for t in flat_list}
        elif isinstance(ts, list):
            return {str(t).lower() for t in ts}
        return set()

    def match_skill(self, skill: Skill) -> List[str]:
        """
        Check if skill should be triggered.
        Returns list of matched conditions (empty if not triggered).
        """
        matched_conditions: List[str] = []

        # 0. Check Negative Triggers (Abort immediately if matches)
        neg_triggers = getattr(skill, "negative_triggers", [])
        if neg_triggers:
            tech_stack_lower = self._get_tech_stack_set()
            for neg in neg_triggers:
                if neg.lower() in tech_stack_lower:
                    return []  # Abort condition

        # 1. Check structured auto_triggers (List[Dict])
        if skill.auto_triggers:
            for trigger_group in skill.auto_triggers:
                if self._check_trigger_group(trigger_group, matched_conditions):
                    return matched_conditions

        # 2. Check legacy list triggers (List[str] - keywords)
        # These are usually just keywords like "fastapi" or "python"
        if skill.triggers:
            # Check against tech stack
            tech_stack_lower = self._get_tech_stack_set()

            for trigger in skill.triggers:
                if trigger.lower() in tech_stack_lower:
                    matched_conditions.append(f"Matched tech: {trigger}")

        return matched_conditions

    def _check_trigger_group(self, group: Dict[str, Any], results: List[str]) -> bool:
        """
        Check a single trigger group (AND logic).
        All defined criteria in the group must match.
        """
        matches = []

        # 1. Keywords (matched against project context, primarily README)
        if "keywords" in group:
            tech_stack_lower = self._get_tech_stack_set()
            for kw in group["keywords"]:
                kw_lower = kw.lower()
                # Check against tech stack (exact match)
                if kw_lower in tech_stack_lower:
                    matches.append(f"Keyword: {kw}")
                    continue

                # Check against other context (README, path, type) using word boundaries
                found = False
                for context_val in self.context.values():
                    if isinstance(context_val, str) and re.search(
                        r"\b" + re.escape(kw_lower) + r"\b", context_val.lower()
                    ):
                        found = True
                        break

                if not found:
                    return False
                matches.append(f"Keyword: {kw}")

        # 2. File Patterns
        if "file_patterns" in group:
            for pattern in group["file_patterns"]:
                if not any(fnmatch.fnmatch(f, pattern) for f in self._cache_file_list):
                    return False  # Fail
                matches.append(f"File Pattern: {pattern}")

        # 3. Project Signals (structure analysis)
        if "project_signals" in group:
            structure = self.context.get("structure", {})
            for signal in group["project_signals"]:
                # signal names map to structure keys (e.g. "has_docker")
                if not structure.get(signal, False):
                    return False
                matches.append(f"Signal: {signal}")

        # If we got here, all conditions in this group passed
        results.extend(matches)
        return True
