import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Synonym expansion table — maps natural language variants to canonical keywords
# that appear in trigger lists.  Keys are regex patterns (case-insensitive);
# values are the canonical keywords to inject into the expanded search text.
_SYNONYM_PATTERNS: List[tuple] = [
    # Debugging synonyms
    (r"\bregression\b", "bug"),
    (r"\bci is red\b", "bug error failing test"),
    (r"\bnothing works\b", "bug error not working"),
    (r"\bbroken\b", "bug error"),
    (r"\bit stopped working\b", "bug error not working"),
    (r"\bexception\b", "error bug"),
    (r"\btraceback\b", "error bug"),
    (r"\bcrash(es|ing)?\b", "bug error not working"),
    # Refactor synonyms
    (r"\bclean\s+up\b", "refactor clean up code"),
    (r"\breadability\b", "refactor clean up code"),
    (r"\btoo\s+long\b", "refactor"),
    # Review synonyms
    (r"\bpr\b", "ready for review"),
    (r"\bpull\s+request\b", "ready for review"),
    (r"\bmerge\s+request\b", "ready for review"),
    # Plan/design synonyms
    (r"\blet'?s\s+(build|create|make|add)\b", "i want to add let's build"),
    (r"\bi('?m|\s+am)\s+thinking\b", "i'm thinking about"),
    (r"\bhow\s+(should|do)\s+we\b", "i want to add"),
    # Test synonyms
    (r"\bcoverage\b", "check coverage"),
    (r"\btest\s+suite\b", "run tests check coverage"),
]


def _expand_input(user_input: str) -> str:
    """Expand user input with synonym keywords for broader trigger matching."""
    expanded = user_input.lower()
    extra_keywords: List[str] = []
    for pattern, replacement in _SYNONYM_PATTERNS:
        if re.search(pattern, expanded, re.IGNORECASE):
            extra_keywords.append(replacement)
    if extra_keywords:
        expanded = expanded + " " + " ".join(extra_keywords)
    return expanded


class AgentExecutor:
    """Handles agent-related tasks like auto-triggering skills."""

    # Fallback trigger map used when auto-triggers.json doesn't exist or is empty.
    # Derived from the Auto-Trigger sections of the bundled builtin SKILL.md files.
    # Keeps prg agent functional on fresh projects that haven't run prg analyze yet.
    _BUILTIN_FALLBACK_TRIGGERS: Dict[str, List[str]] = {
        "systematic-debugging": [
            "bug",
            "error",
            "not working",
            "failing test",
            "ci/cd failure",
            "exception in logs",
        ],
        "brainstorming": [
            "i want to add",
            "let's build",
            "i'm thinking about",
            "before any code is written",
            "requirements are unclear",
        ],
        "requesting-code-review": [
            "ready for review",
            "can you review",
            "task/feature complete",
            "creating pr/merge request",
            "please review",
            "take a look at",
        ],
        "test-driven-development": [
            "new feature implementation",
            "bug fix",
            "refactoring",
        ],
        "writing-plans": [
            "let's implement this",
            "create a plan",
            "design.md exists",
        ],
        "writing-skills": [
            "create a skill for",
            "we should formalize",
            "repetitive pattern identified",
        ],
        "subagent-driven-development": [
            "execute the plan",
            "plan.md exists",
        ],
    }

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.triggers_path = project_path / ".clinerules" / "auto-triggers.json"
        self._file_triggers: Dict[str, List[str]] = {}
        self._load_triggers()

    def _load_triggers(self) -> None:
        """Load project-specific triggers from auto-triggers.json.

        Matching uses a two-pass strategy in match_skill():
          Pass 1 — file-defined triggers (auto-triggers.json), if any.
          Pass 2 — builtin fallback triggers, only when pass 1 finds no match.

        This guarantees that explicit project triggers always outrank generic
        builtins, even when a builtin phrase is a substring of a project phrase.
        """
        if self.triggers_path.exists():
            try:
                content = self.triggers_path.read_text(encoding="utf-8")
                parsed = json.loads(content)
                if parsed:
                    self._file_triggers = parsed
                    logger.debug("Loaded %d trigger groups from %s.", len(parsed), self.triggers_path)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.warning("Failed to load auto-triggers: %s", e)
        else:
            logger.debug("auto-triggers.json absent — will use builtin fallback triggers only.")

    def _search_triggers(self, triggers: Dict[str, List[str]], expanded_input: str) -> Optional[str]:
        """Return the first skill whose phrases match expanded_input, or None."""
        for skill, phrases in triggers.items():
            for phrase in phrases:
                clean_phrase = phrase.strip("\"'").lower()
                logger.debug("Checking '%s' in expanded input", clean_phrase)
                if clean_phrase in expanded_input:
                    return skill
        return None

    def match_skill(self, user_input: str) -> Optional[str]:
        """
        Find the best matching skill for the user input.

        Uses a two-pass strategy to prevent over-eager matching:
          1. Search project-specific triggers (auto-triggers.json) first.
          2. Only if no match found, fall back to builtin triggers.

        This ensures explicit project triggers (e.g. "fix a bug") always
        outrank generic builtins (e.g. "bug"), not just when they share a skill
        name but also across all skill names in the file.

        Returns the skill name or None.
        """
        expanded_input = _expand_input(user_input)
        logger.debug("Expanded input: '%s'", expanded_input)

        # Pass 1 — project-specific triggers
        if self._file_triggers:
            logger.debug("Pass 1: searching %d file trigger groups.", len(self._file_triggers))
            match = self._search_triggers(self._file_triggers, expanded_input)
            if match is not None:
                logger.debug("MATCH FOUND (file triggers): %s", match)
                self._record_match(match)
                return match

        # Pass 2 — builtin fallbacks (only reached when file triggers produced no match)
        logger.debug("Pass 2: searching builtin fallback triggers.")
        match = self._search_triggers(self._BUILTIN_FALLBACK_TRIGGERS, expanded_input)
        if match is not None:
            logger.debug("MATCH FOUND (builtin triggers): %s", match)
            self._record_match(match)
            return match

        logger.debug("No match found.")
        return None

    def _record_match(self, skill: str) -> None:
        """Log skill path presence and record the match via SkillTracker (best-effort)."""
        skill_path = self.project_path / ".clinerules" / "skills" / "learned" / skill
        flat_path = self.project_path / ".clinerules" / "skills" / "learned" / f"{skill}.md"
        if skill_path.exists() or flat_path.exists():
            logger.debug("MATCH FOUND for skill: %s", skill)
        else:
            logger.debug(
                "Trigger matched but skill '%s' not found in .clinerules/skills/learned — "
                "returning anyway (may be a builtin)",
                skill,
            )
        try:
            from generator.skill_tracker import SkillTracker

            SkillTracker().record_match(skill)
        except Exception as _te:  # noqa: BLE001 — tracking is non-critical; ImportError or any runtime error must not break routing
            logger.debug("SkillTracker.record_match failed: %s", _te)
