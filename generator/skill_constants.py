"""Central constants for skill layer names and filenames.

Use these instead of raw strings to avoid typo-bugs and ease future refactoring.
All comparisons like ``scope == SkillScope.LEARNED`` remain valid because the
values are plain strings — no enum overhead, full Python 3.8 compatibility.
"""


class SkillScope:
    """Valid values for the skill storage layer / scope parameter."""

    LEARNED = "learned"
    BUILTIN = "builtin"
    PROJECT = "project"

    # Ordered by override priority (project > learned > builtin)
    ALL = (PROJECT, LEARNED, BUILTIN)

    # Iteration order for "last writer wins" merging: lowest priority first so
    # higher-priority layers overwrite on name collision (builtin → learned → project).
    MERGE_ORDER = (BUILTIN, LEARNED, PROJECT)

    # The two global layers (no project-local involvement)
    GLOBAL_LAYERS = (LEARNED, BUILTIN)


# Canonical filename for every skill's main document
SKILL_FILENAME = "SKILL.md"
