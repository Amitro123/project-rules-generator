"""Skill-name selection.

Curated tech profiles win; any unmapped-but-skill-worthy tech gets a synthesized
``{tech}-workflow`` skill so a project's core technologies are never silently
dropped just because no one authored a profile ``skill_name`` for them.

The "skill-worthy" decision reuses the profile ``category`` already attached to
every detected tech (see ``generator/tech/lookups.py``): libraries an agent
benefits from a dedicated skill for (backend, frontend, database, ml, ai,
testing) qualify; languages (``python``, ``go``) and generic infrastructure
(``git``, ``linux``, ``yaml``) do not. An unknown tech with no profile/category
never reaches synthesis, so transitive or unrecognised packages produce no noise.
"""

from __future__ import annotations

from typing import Iterable, List

from generator.tech.lookups import TECH_CATEGORIES, TECH_SKILL_NAMES

# Profile categories whose unmapped techs deserve a synthesized "{tech}-workflow".
SKILL_WORTHY_CATEGORIES = frozenset({"backend", "frontend", "database", "ml", "ai", "testing"})

# Explicit overrides: techs in a skill-worthy category that are too ubiquitous
# (stdlib) or generic to warrant their own skill. Extend as real noise appears.
NON_SKILL_TECHS = frozenset({"asyncio"})


def is_skill_worthy(tech: str) -> bool:
    """True if an unmapped detected tech should get a synthesized ``{tech}-workflow``."""
    key = tech.lower().strip()
    if key in NON_SKILL_TECHS:
        return False
    return TECH_CATEGORIES.get(key) in SKILL_WORTHY_CATEGORIES


def select_skill_names(tech_stack: Iterable[str], project_name: str) -> List[str]:
    """Map a detected tech stack to a deduplicated, sorted list of skill names.

    Curated ``TECH_SKILL_NAMES`` entries win; unmapped-but-skill-worthy techs get
    ``{tech}-workflow``. Falls back to ``{project_name}-workflow`` when nothing
    qualifies (empty or language-only stack).
    """
    names: List[str] = []
    for tech in tech_stack:
        key = tech.lower().strip()
        mapped = TECH_SKILL_NAMES.get(key)
        if mapped:
            names.append(mapped)
        elif is_skill_worthy(key):
            names.append(f"{key}-workflow")

    if not names:
        names.append(f"{project_name}-workflow")

    return sorted(set(names))
