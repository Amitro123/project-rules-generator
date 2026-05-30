"""Declarative project_type reconciliation.

Replaces the if/elif cascade at ``enhanced_parser.py:_extract_metadata``
(two project_type detectors with hardcoded thresholds) with a precedence
table evaluated in order. ``reconcile_project_type`` is fully generic — it
iterates rule records and applies whichever first matches. Per-tech
decisions live in the rule data, not in branching code, so new rules can
be added without touching the function itself.

The ``DEFAULT_PROJECT_TYPE_PRECEDENCE`` module-level table is reassigned
at import time by ``generator.project_profile.__init__`` after loading
YAML rule files. Functions read it at CALL time so reassignment is
picked up correctly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, FrozenSet, Optional, Tuple, Union

# Sentinel meaning "any newer_type matches this rule".
NEWER_TYPE_ANY = "*"


@dataclass(frozen=True)
class PrecedenceRule:
    """One row in the project_type precedence table.

    A rule fires when ``match_newer`` matches the newer-detector's output AND
    ``predicate`` (given the two detectors' types + confidences) returns True.
    The first rule that fires wins; its newer_type becomes the resolved
    project_type. If no rule fires, the structure_type wins.

    Fields
    ------
    name : human label for debugging / log lines
    match_newer : either a specific newer_type, a frozenset of acceptable
        newer_types, or the sentinel ``NEWER_TYPE_ANY`` ("*") which matches
        any non-empty newer_type
    predicate : callable taking (structure_type, structure_confidence,
        newer_type, newer_confidence) and returning True when the rule
        should fire
    reason : prose explanation, surfaced in shadow logs to make the
        precedence transparent in real runs
    """

    name: str
    match_newer: Union[str, FrozenSet[str]]
    predicate: Callable[[str, float, str, float], bool]
    reason: str

    def matches_newer(self, newer_type: str) -> bool:
        """Type-side match, before evaluating the predicate."""
        if self.match_newer == NEWER_TYPE_ANY:
            return bool(newer_type)
        if isinstance(self.match_newer, frozenset):
            return newer_type in self.match_newer
        return newer_type == self.match_newer


# Predicate factories — closures over numeric thresholds and structure
# vocabularies. Using factories keeps the table itself terse and lets future
# rule additions stay declarative.


def _always_match(*_args, **_kwargs) -> bool:
    return True


def _newer_min_confidence(min_conf: float) -> Callable[[str, float, str, float], bool]:
    def _pred(_structure_type: str, _structure_conf: float, _newer_type: str, newer_conf: float) -> bool:
        return newer_conf >= min_conf

    return _pred


def _newer_confident_structure_uncertain(
    newer_min: float, structure_max: float
) -> Callable[[str, float, str, float], bool]:
    def _pred(_structure_type: str, structure_conf: float, _newer_type: str, newer_conf: float) -> bool:
        return newer_conf >= newer_min and structure_conf < structure_max

    return _pred


def _structure_unreliable_and_newer_confident(
    fallback_structure_types: FrozenSet[str],
    newer_min: float,
) -> Callable[[str, float, str, float], bool]:
    """When the structural detector gave a generic fallback (library/unknown)
    AND the newer detector is reasonably confident, prefer the newer result.
    """

    def _pred(structure_type: str, _structure_conf: float, _newer_type: str, newer_conf: float) -> bool:
        return structure_type in fallback_structure_types and newer_conf >= newer_min

    return _pred


# Default precedence table. Populated by
# ``generator.project_profile.__init__._load_rules_at_import`` from the
# YAML rule files at import time. Pre-declared as an empty tuple so any
# tooling that references the name during import sees a valid value
# rather than NameError. Functions look this up at CALL time so the
# reassignment by the loader propagates correctly.
DEFAULT_PROJECT_TYPE_PRECEDENCE: Tuple[PrecedenceRule, ...] = ()


@dataclass(frozen=True)
class ReconciliationResult:
    """Outcome of project_type reconciliation. The resolved type plus a
    machine-readable trace so shadow logs / debug output can show which
    rule fired (if any)."""

    project_type: str
    rule_fired: Optional[str]  # PrecedenceRule.name, or None if no rule applied
    reason: str  # the rule's reason, or a default when no rule fired


def reconcile_project_type(
    structure_type: str,
    structure_confidence: float,
    newer_type: str,
    newer_confidence: float,
    rules: Optional[Tuple[PrecedenceRule, ...]] = None,
) -> ReconciliationResult:
    """Resolve the canonical project_type given two detectors' outputs.

    Replaces the if/elif cascade in ``enhanced_parser._extract_metadata``.
    Pure function — no I/O, no globals, no project-specific code paths.
    The precedence is data; this function is generic.

    Parameters
    ----------
    structure_type : output of ``StructureAnalyzer.detect_project_type()``
        (typically one of python-cli, fastapi-api, library, unknown, …).
    structure_confidence : confidence in [0.0, 1.0] from the same detector.
    newer_type : output of ``project_type_detector.detect_project_type()``,
        already translated through TYPE_LABEL_MAP. May be ``""`` when the
        detector produced no opinion.
    newer_confidence : confidence in [0.0, 1.0] from the newer detector.
    rules : ordered precedence table. Defaults to
        ``DEFAULT_PROJECT_TYPE_PRECEDENCE``. Passing a custom tuple lets
        callers (especially tests) override the policy without monkey-patching.

    Returns
    -------
    ReconciliationResult with the resolved project_type plus the rule that
    fired (or ``None`` when no rule matched and structure_type was kept).
    """
    # Normalize inputs — guards against detectors that return None or float
    # confidences outside [0, 1]. The contract here is "tolerate ugly input
    # from upstream detectors during the migration; clamp and proceed".
    s_type = (structure_type or "unknown").strip() or "unknown"
    s_conf = max(0.0, min(1.0, float(structure_confidence or 0.0)))
    n_type = (newer_type or "").strip()
    n_conf = max(0.0, min(1.0, float(newer_confidence or 0.0)))

    # Default to the module-level table, evaluated at CALL time so YAML
    # rules loaded at import time are picked up correctly.
    if rules is None:
        rules = DEFAULT_PROJECT_TYPE_PRECEDENCE

    if not n_type:
        return ReconciliationResult(
            project_type=s_type,
            rule_fired=None,
            reason="newer_type was empty; kept structure_type unchanged.",
        )

    for rule in rules:
        if not rule.matches_newer(n_type):
            continue
        if rule.predicate(s_type, s_conf, n_type, n_conf):
            return ReconciliationResult(
                project_type=n_type,
                rule_fired=rule.name,
                reason=rule.reason,
            )

    # No rule fired — structure detector wins by default.
    return ReconciliationResult(
        project_type=s_type,
        rule_fired=None,
        reason="No precedence rule matched; kept structure_type as the default.",
    )
