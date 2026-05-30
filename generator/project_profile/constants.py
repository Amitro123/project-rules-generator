"""ProjectProfile constants and name-validation helpers.

Constants shared across the project_profile package — evidence sources, skill
scopes, known project types, and the heuristics that guard the project name
extractor from accepting README catenations.
"""

from __future__ import annotations

from typing import FrozenSet, Tuple

# --- Evidence sources -------------------------------------------------------

# Evidence sources for a tech entry.
#
# STRONG: code-level evidence — the tech is genuinely used by this project.
#   - "dependency"   : appears in requirements.txt / pyproject.toml / package.json
#   - "manifest"     : appears in another machine-readable manifest (spec.yml, etc.)
#   - "import"       : referenced via an import/require statement
#   - "file_pattern" : presence of a signature file (Dockerfile, rxconfig.py, …)
#   - "spec"         : declared in the project's spec.yml / spec.yaml
#
# WEAK: only README / prose evidence — may be aspirational or noise.
#
# UNKNOWN: the producer didn't record a source. Common during Phase 1, when
# the contract is built from a legacy enhanced_context that doesn't carry
# source attribution. Phase 2 migrates detectors to emit explicit sources.
EVIDENCE_SOURCES_STRONG = frozenset({"dependency", "manifest", "import", "file_pattern", "spec"})
EVIDENCE_SOURCES_WEAK = frozenset({"readme"})
EVIDENCE_SOURCES_UNKNOWN = frozenset({"inferred"})
EVIDENCE_SOURCES_ALL = EVIDENCE_SOURCES_STRONG | EVIDENCE_SOURCES_WEAK | EVIDENCE_SOURCES_UNKNOWN

# --- Skill scopes -----------------------------------------------------------

# Skill scopes. Order matters for precedence (project beats learned beats
# builtin when the same terminal name appears in multiple scopes).
SKILL_SCOPES: Tuple[str, ...] = ("project", "learned", "builtin")

# --- Known project types ----------------------------------------------------

# Project types PRG knows how to reason about. Detection layers may produce
# values outside this set during transition — `validate_invariants` flags
# unknown types as a warning rather than a hard error in Phase 1.
KNOWN_PROJECT_TYPES: FrozenSet[str] = frozenset(
    {
        # From generator/analyzers/structure_analyzer.py:PATTERNS
        "python-cli",
        "fastapi-api",
        "django-app",
        "flask-app",
        "reflex-app",
        "react-app",
        "vue-app",
        "node-api",
        "ml-pipeline",
        "library",
        # From generator/analyzers/project_type_detector.py:TYPE_LABEL_MAP
        "python-api",
        "agent-skills",
        "cli-tool",
        "web-app",
        # From override branches in enhanced_parser.py:_extract_metadata
        "agent",
        "generator",
        # Universal fallback
        "unknown",
    }
)

# --- Project name guards ----------------------------------------------------

# Project names that came from generic README instruction headings rather
# than the project itself. Detection layers should reject these and fall
# back to the project directory name.
GENERIC_PROJECT_NAME_SLUGS: FrozenSet[str] = frozenset(
    {
        "clone-repository",
        "getting-started",
        "quick-start",
        "installation",
        "setup",
        "introduction",
        "overview",
        "usage",
        "table-of-contents",
        "contents",
    }
)

# A project name from an H1 should be short and few-segment. When the
# README parser concatenates multiple H1 lines (or a single very long
# title) the result becomes a multi-segment slug that's clearly not a
# real package/repo name. Real project names are typically 1-4 segments
# and under ~40 characters (django, fastapi, project-rules-generator,
# ultimate-doc-researcher). Anything beyond these bounds is a smell.
#
# Surfaced by an e2e run on ultimate-doc-researcher, which produced
# ``archives-papers-clears-stale-data-resets-prompt-cache-updates-topic``
# — 10 segments, 65 chars — as the project_name. The directory name
# (``ultimate-doc-researcher``, 3 segments / 23 chars) was the correct
# answer.
PROJECT_NAME_MAX_SEGMENTS = 5
PROJECT_NAME_MAX_LENGTH = 50


def looks_like_concatenated_heading_slug(name: str) -> bool:
    """Return True when ``name`` looks like a README H1 catenation rather
    than a real project name.

    Heuristic: more than ``PROJECT_NAME_MAX_SEGMENTS`` dash-separated
    segments, OR longer than ``PROJECT_NAME_MAX_LENGTH`` characters.
    Both bounds are generous — real names rarely come close to either.
    """
    if not name:
        return False
    segments = name.count("-") + 1
    return segments > PROJECT_NAME_MAX_SEGMENTS or len(name) > PROJECT_NAME_MAX_LENGTH
