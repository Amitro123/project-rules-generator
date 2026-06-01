"""generator.project_profile — single immutable construction site for a
project's identity.

This package owns the contract between PRG's detection layer (tech_detector,
project_type_detector, readme_parser, skill_discovery,
enhanced_skill_matcher) and its output layer (rules.md, clinerules.yaml,
skills/index.md).

Why this exists
---------------
Historically PRG produced these fields via several independent subsystems
that each wrote into a shared mutable dict (``project_data``). Every
recurring bug traced to one symptom: producers got out of sync with
consumers and nothing enforced an invariant between them — 9 project
skills on disk while ``rules.md`` reported ``project: 0``,
``pydantic-validation`` appearing in two scopes, learned skills tagged
``[jest, react]`` selected for pure-Python projects, and so on.

``ProjectProfile`` is constructed once after all detectors have run, then
frozen. ``validate_invariants()`` is the single place that enforces the
contract; violations raise ``InvariantViolation`` rather than silently
degrading.

Package layout (the public API is the package, not the submodules — every
public name is re-exported here):

  constants       : evidence-source / skill-scope / project-type constants
  exceptions      : ``InvariantViolation``
  models          : ``TechEntry``, ``SkillRef``, ``ProjectProfile``
  adapter         : ``from_enhanced_context`` (Phase 1 adapter)
  skill_dedup     : ``dedupe_skill_refs`` (canonical cross-scope dedup)
  reconciliation  : ``reconcile_project_type`` + ``PrecedenceRule`` table
  tech_cleanup    : ``apply_tech_cleanup_rules`` + ``TechCleanupRule`` table
  skill_filter    : ``filter_skills_by_tech_overlap``
"""

from __future__ import annotations

# --- Re-exports: every public name from the submodules ----------------------
from generator.project_profile.adapter import _build_tech_entries, _parse_skill_refs, from_enhanced_context
from generator.project_profile.constants import (
    EVIDENCE_SOURCES_ALL,
    EVIDENCE_SOURCES_STRONG,
    EVIDENCE_SOURCES_UNKNOWN,
    EVIDENCE_SOURCES_WEAK,
    GENERIC_PROJECT_NAME_SLUGS,
    KNOWN_PROJECT_TYPES,
    PROJECT_NAME_MAX_LENGTH,
    PROJECT_NAME_MAX_SEGMENTS,
    SKILL_SCOPES,
    looks_like_concatenated_heading_slug,
)
from generator.project_profile.exceptions import InvariantViolation
from generator.project_profile.models import ProjectProfile, SkillRef, TechEntry
from generator.project_profile.reconciliation import (
    DEFAULT_PROJECT_TYPE_PRECEDENCE,
    NEWER_TYPE_ANY,
    PrecedenceRule,
    ReconciliationResult,
    _always_match,
    _newer_confident_structure_uncertain,
    _newer_min_confidence,
    _structure_unreliable_and_newer_confident,
    reconcile_project_type,
)
from generator.project_profile.skill_dedup import dedupe_skill_refs
from generator.project_profile.skill_filter import FilterTrace, TagResolver, filter_skills_by_tech_overlap
from generator.project_profile.tech_cleanup import (
    DEFAULT_TECH_CLEANUP_RULES,
    CleanupPredicate,
    CleanupTrace,
    TechCleanupRule,
    _always_apply,
    _when_context_key_not_equal,
    _when_stack_contains,
    apply_tech_cleanup_rules,
)

__all__ = [
    # constants
    "EVIDENCE_SOURCES_ALL",
    "EVIDENCE_SOURCES_STRONG",
    "EVIDENCE_SOURCES_UNKNOWN",
    "EVIDENCE_SOURCES_WEAK",
    "GENERIC_PROJECT_NAME_SLUGS",
    "KNOWN_PROJECT_TYPES",
    "PROJECT_NAME_MAX_LENGTH",
    "PROJECT_NAME_MAX_SEGMENTS",
    "SKILL_SCOPES",
    "looks_like_concatenated_heading_slug",
    # exceptions
    "InvariantViolation",
    # models
    "ProjectProfile",
    "SkillRef",
    "TechEntry",
    # adapter
    "from_enhanced_context",
    # skill dedup
    "dedupe_skill_refs",
    # reconciliation
    "DEFAULT_PROJECT_TYPE_PRECEDENCE",
    "NEWER_TYPE_ANY",
    "PrecedenceRule",
    "ReconciliationResult",
    "reconcile_project_type",
    # tech cleanup
    "DEFAULT_TECH_CLEANUP_RULES",
    "CleanupPredicate",
    "CleanupTrace",
    "TechCleanupRule",
    "apply_tech_cleanup_rules",
    # skill filter
    "FilterTrace",
    "TagResolver",
    "filter_skills_by_tech_overlap",
]


# --- Load declarative rule files at import time -----------------------------
#
# This runs AFTER all submodule symbols have been imported above so the
# loader can rely on every dataclass being defined. Failure to load is
# non-fatal: the contract layer still works (with empty tables), but the
# default reconciliation/cleanup behaviour is unavailable. Functions that
# take a `rules` parameter look up the module-level default at call time,
# so reassignment here propagates correctly.
#
# We assign to TWO places per default-table:
#   1. The submodule global (e.g. ``reconciliation.DEFAULT_PROJECT_TYPE_PRECEDENCE``)
#      — this is what ``reconcile_project_type`` reads at call time.
#   2. The package-level re-export (``globals()['DEFAULT_PROJECT_TYPE_PRECEDENCE']``)
#      — this is what ``from generator.project_profile import DEFAULT_PROJECT_TYPE_PRECEDENCE``
#      resolves to in callers.
# Without both assignments, callers that import the name at the package
# level would see the empty stub forever.


def _load_rules_at_import() -> None:
    """Populate DEFAULT_PROJECT_TYPE_PRECEDENCE and DEFAULT_TECH_CLEANUP_RULES
    from the YAML rule files. Logs and continues on failure."""
    from generator.project_profile import reconciliation as _reconciliation
    from generator.project_profile import tech_cleanup as _tech_cleanup

    try:
        from generator.rules.tech_detection_loader import load_cleanup_rules, load_precedence_rules

        precedence = load_precedence_rules()
        cleanup = load_cleanup_rules()
    except Exception as exc:  # noqa: BLE001 — must never break package import
        import logging

        logging.getLogger(__name__).warning(
            "project_profile: failed to load YAML rule files: %s. "
            "DEFAULT_PROJECT_TYPE_PRECEDENCE and DEFAULT_TECH_CLEANUP_RULES "
            "remain empty; reconcile_project_type / apply_tech_cleanup_rules "
            "will be no-ops until rule files are restored.",
            exc,
        )
        return

    _reconciliation.DEFAULT_PROJECT_TYPE_PRECEDENCE = precedence
    _tech_cleanup.DEFAULT_TECH_CLEANUP_RULES = cleanup
    globals()["DEFAULT_PROJECT_TYPE_PRECEDENCE"] = precedence
    globals()["DEFAULT_TECH_CLEANUP_RULES"] = cleanup


_load_rules_at_import()
