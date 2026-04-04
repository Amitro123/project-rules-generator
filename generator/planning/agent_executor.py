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
            "bug", "error", "not working", "failing test",
            "ci/cd failure", "exception in logs",
        ],
        "brainstorming": [
            "i want to add", "let's build", "i'm thinking about",
            "before any code is written", "requirements are unclear",
        ],
        "requesting-code-review": [
            "ready for review", "can you review?",
            "task/feature complete", "creating pr/merge request",
        ],
        "test-driven-development": [
            "new feature implementation", "bug fix", "refactoring",
        ],
        "writing-plans": [
            "let's implement this", "create a plan", "design.md exists",
        ],
        "writing-skills": [
            "create a skill for", "we should formalize",
            "repetitive pattern identified",
        ],
        "subagent-driven-development": [
            "execute the plan", "plan.md exists",
        ],
    }

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.triggers_path = project_path / ".clinerules" / "auto-triggers.json"
        self._triggers: Dict[str, List[str]] = {}
        self._load_triggers()

    def _load_triggers(self):
        """Load triggers from JSON, always merging builtin defaults underneath.

        Builtins are the floor: file content overrides them per-skill, but skills
        absent from the file (e.g. when prg analyze ran offline) still fire.
        """
        # Start with builtins as the baseline
        merged: Dict[str, List[str]] = dict(self._BUILTIN_FALLBACK_TRIGGERS)

        if self.triggers_path.exists():
            try:
                content = self.triggers_path.read_text(encoding="utf-8")
                loaded = json.loads(content)
                if loaded:
                    # File content overrides builtins for matching skill names
                    merged.update(loaded)
                    logger.debug("Loaded %d trigger groups from %s.", len(loaded), self.triggers_path)
            except Exception as e:
                logger.warning("Failed to load auto-triggers: %s", e)
        else:
            logger.debug("auto-triggers.json absent — using builtin fallback triggers only.")

        self._triggers = merged

    def match_skill(self, user_input: str) -> Optional[str]:
        """
        Find the best matching skill for the user input.

        Performs substring matching against trigger phrases with synonym
        expansion so natural variants ("there's a regression", "CI is red")
        map to the right skill without requiring exact literal matches.

        Returns the skill name or None.
        """
        if not self._triggers:
            logger.debug("No triggers loaded from %s", self.triggers_path)
            return None

        logger.debug("Loaded %d trigger groups.", len(self._triggers))

        # Expand the input with synonym keywords before matching
        expanded_input = _expand_input(user_input)
        logger.debug("Expanded input: '%s'", expanded_input)

        for skill, phrases in self._triggers.items():
            for phrase in phrases:
                clean_phrase = phrase.strip("\"'").lower()
                logger.debug("Checking '%s' in expanded input", clean_phrase)
                if clean_phrase in expanded_input:
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
                    except Exception as _te:
                        logger.debug("SkillTracker.record_match failed: %s", _te)
                    return skill

        logger.debug("No match found.")
        return None