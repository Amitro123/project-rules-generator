"""Loader for declarative tech-detection rule files.

Reads YAML files under ``generator/rules/tech-detection/`` at import time
and produces ``PrecedenceRule`` / ``TechCleanupRule`` tuples that drop into
``reconcile_project_type`` and ``apply_tech_cleanup_rules`` (defined in
``generator.project_profile``).

The point of this module
------------------------
After Phase 3b, **adding or modifying a tech-detection rule is a YAML PR
with zero Python edits**. The Python layer holds the *machinery* (generic
functions, predicate builders) but not the *policy* (which techs trigger
what, which thresholds apply).

If the rule files are missing or malformed at load time, the loader logs
a warning and returns an empty tuple — callers fall back to safe defaults
("no rules applied") rather than crashing the import. This is intentional:
the contract layer must keep working even when policy is unavailable.

Predicate types
---------------
See ``generator/rules/tech-detection/_schema.md`` for the schema. Predicate
``type`` strings are mapped to the builder functions in
``generator.project_profile`` via the registries below. Unknown predicate
types are rejected during loading.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, FrozenSet, List, Optional, Tuple, Union

import yaml

# IMPORTANT: project_profile imports are LAZY (done inside functions) to avoid
# a circular-import deadlock. project_profile.py calls back into this module
# at import time to load YAML rules; if we did `from generator.project_profile
# import ...` at module top, it would race with project_profile's own loader
# call and silently leave DEFAULT_* tables empty. Imports below are guarded
# behind TYPE_CHECKING so type checkers still see the dependency.
if TYPE_CHECKING:
    from generator.project_profile import PrecedenceRule, TechCleanupRule

logger = logging.getLogger(__name__)

# Repository-relative directory where rule YAML files live. Resolved relative
# to this file so the loader works whether PRG is installed editable or as
# a wheel.
RULES_ROOT = Path(__file__).parent / "tech-detection"
PRECEDENCE_DIR_NAME = "project-type-precedence"
CLEANUP_DIR_NAME = "tech-cleanup"


# --- Predicate registries ---------------------------------------------------
#
# Each entry maps a predicate `type` string (as it appears in YAML) to a
# builder that turns the type-specific params dict into a callable. The
# registries are the *only* place where predicate vocabulary is declared;
# adding a new predicate type means adding one entry + a corresponding
# builder in project_profile.py. No other code change.


def _build_always_precedence_predicate(_spec: Dict[str, Any]) -> Callable:
    from generator.project_profile import _always_match

    return _always_match


def _build_newer_min_confidence_predicate(spec: Dict[str, Any]) -> Callable:
    from generator.project_profile import _newer_min_confidence

    threshold = float(spec["threshold"])
    return _newer_min_confidence(threshold)


def _build_newer_confident_structure_uncertain_predicate(spec: Dict[str, Any]) -> Callable:
    from generator.project_profile import _newer_confident_structure_uncertain

    return _newer_confident_structure_uncertain(
        newer_min=float(spec["newer_min"]),
        structure_max=float(spec["structure_max"]),
    )


def _build_structure_unreliable_predicate(spec: Dict[str, Any]) -> Callable:
    from generator.project_profile import _structure_unreliable_and_newer_confident

    return _structure_unreliable_and_newer_confident(
        fallback_structure_types=frozenset(spec["fallback_structure_types"]),
        newer_min=float(spec["newer_min"]),
    )


PRECEDENCE_PREDICATE_BUILDERS: Dict[str, Callable[[Dict[str, Any]], Callable]] = {
    "always": _build_always_precedence_predicate,
    "newer_min_confidence": _build_newer_min_confidence_predicate,
    "newer_confident_structure_uncertain": _build_newer_confident_structure_uncertain_predicate,
    "structure_unreliable_and_newer_confident": _build_structure_unreliable_predicate,
}


def _build_always_cleanup_predicate(_spec: Dict[str, Any]) -> Callable:
    from generator.project_profile import _always_apply

    return _always_apply


def _build_stack_contains_predicate(spec: Dict[str, Any]) -> Callable:
    from generator.project_profile import _when_stack_contains

    return _when_stack_contains(spec["token"])


def _build_context_key_not_equal_predicate(spec: Dict[str, Any]) -> Callable:
    from generator.project_profile import _when_context_key_not_equal

    return _when_context_key_not_equal(spec["key"], spec["value"])


CLEANUP_PREDICATE_BUILDERS: Dict[str, Callable[[Dict[str, Any]], Callable]] = {
    "always": _build_always_cleanup_predicate,
    "stack_contains": _build_stack_contains_predicate,
    "context_key_not_equal": _build_context_key_not_equal_predicate,
}


# --- Parse + validate -------------------------------------------------------


class RuleParseError(ValueError):
    """Raised when a single rule file can't be parsed. The loader catches
    this and skips the offending file, but tests use it to assert errors."""


def _require(spec: Dict[str, Any], field: str, rule_name: str = "<unnamed>") -> Any:
    if field not in spec or spec[field] is None:
        raise RuleParseError(f"rule {rule_name!r}: missing required field {field!r}")
    return spec[field]


def _build_predicate(
    predicate_spec: Dict[str, Any],
    builders: Dict[str, Callable[[Dict[str, Any]], Callable]],
    rule_name: str,
) -> Callable:
    if not isinstance(predicate_spec, dict):
        raise RuleParseError(f"rule {rule_name!r}: 'predicate' must be a mapping, got {type(predicate_spec).__name__}")
    p_type = predicate_spec.get("type")
    if not p_type:
        raise RuleParseError(f"rule {rule_name!r}: predicate is missing 'type'")
    builder = builders.get(p_type)
    if builder is None:
        valid = ", ".join(sorted(builders.keys()))
        raise RuleParseError(f"rule {rule_name!r}: unknown predicate type {p_type!r}. Valid types: {valid}")
    try:
        return builder(predicate_spec)
    except (KeyError, TypeError, ValueError) as exc:
        raise RuleParseError(f"rule {rule_name!r}: predicate {p_type!r} rejected its params: {exc}") from exc


def _parse_precedence_rule(spec: Dict[str, Any]) -> "PrecedenceRule":
    # Lazy import — see file-top comment about circular-import avoidance.
    from generator.project_profile import PrecedenceRule

    if not isinstance(spec, dict):
        raise RuleParseError(f"precedence rule file must contain a mapping, got {type(spec).__name__}")
    name = str(_require(spec, "name"))
    reason = str(_require(spec, "reason")).strip()
    match_newer = _require(spec, "match_newer", name)
    predicate_spec = _require(spec, "predicate", name)

    # Normalise match_newer into the canonical type the contract expects:
    # str (single or "*" sentinel) or frozenset[str].
    match_newer_canon: Union[str, FrozenSet[str]]
    if isinstance(match_newer, list):
        if not match_newer:
            raise RuleParseError(f"rule {name!r}: match_newer list is empty")
        match_newer_canon = frozenset(str(x) for x in match_newer)
    elif isinstance(match_newer, str):
        match_newer_canon = match_newer  # may be specific value or NEWER_TYPE_ANY ("*")
    else:
        raise RuleParseError(
            f"rule {name!r}: match_newer must be a string or list of strings, " f"got {type(match_newer).__name__}"
        )

    predicate = _build_predicate(predicate_spec, PRECEDENCE_PREDICATE_BUILDERS, name)

    return PrecedenceRule(
        name=name,
        match_newer=match_newer_canon,
        predicate=predicate,
        reason=reason,
    )


def _parse_cleanup_rule(spec: Dict[str, Any]) -> "TechCleanupRule":
    from generator.project_profile import TechCleanupRule

    if not isinstance(spec, dict):
        raise RuleParseError(f"cleanup rule file must contain a mapping, got {type(spec).__name__}")
    name = str(_require(spec, "name"))
    reason = str(_require(spec, "reason")).strip()
    strip = _require(spec, "strip", name)
    predicate_spec = _require(spec, "predicate", name)

    if not isinstance(strip, list) or not all(isinstance(x, str) for x in strip):
        raise RuleParseError(f"rule {name!r}: 'strip' must be a list of strings")
    if not strip:
        raise RuleParseError(f"rule {name!r}: 'strip' list cannot be empty")

    predicate = _build_predicate(predicate_spec, CLEANUP_PREDICATE_BUILDERS, name)

    return TechCleanupRule(
        name=name,
        predicate=predicate,
        strip=frozenset(strip),
        reason=reason,
    )


# --- Public loaders ---------------------------------------------------------


def _iter_yaml_files(directory: Path) -> List[Path]:
    """Lexicographically-sorted YAML files in a directory. Files starting
    with ``_`` are skipped (reserved for schema docs etc.)."""
    if not directory.exists() or not directory.is_dir():
        return []
    return sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in (".yaml", ".yml") and not p.name.startswith("_")
    )


def _load_yaml(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("tech_detection_loader: could not read %s: %s", path, exc)
        return None
    if data is None:
        logger.warning("tech_detection_loader: %s is empty", path)
        return None
    if not isinstance(data, dict):
        logger.warning(
            "tech_detection_loader: %s top-level is not a mapping (got %s); skipping",
            path,
            type(data).__name__,
        )
        return None
    return data


def load_precedence_rules(root: Path = RULES_ROOT) -> Tuple["PrecedenceRule", ...]:
    """Load all YAML files in ``<root>/project-type-precedence/`` and return
    a tuple of PrecedenceRule in lexicographic filename order.

    Files that fail to parse are logged and skipped, never propagated as
    exceptions. Missing or empty directory returns ``()``.
    """
    rules: List[Any] = []
    for path in _iter_yaml_files(root / PRECEDENCE_DIR_NAME):
        data = _load_yaml(path)
        if data is None:
            continue
        try:
            rules.append(_parse_precedence_rule(data))
        except RuleParseError as exc:
            logger.warning("tech_detection_loader: %s: %s", path.name, exc)
    return tuple(rules)


def load_cleanup_rules(root: Path = RULES_ROOT) -> Tuple["TechCleanupRule", ...]:
    """Load all YAML files in ``<root>/tech-cleanup/`` and return a tuple of
    TechCleanupRule in lexicographic filename order.

    Failure semantics match load_precedence_rules.
    """
    rules: List[Any] = []
    for path in _iter_yaml_files(root / CLEANUP_DIR_NAME):
        data = _load_yaml(path)
        if data is None:
            continue
        try:
            rules.append(_parse_cleanup_rule(data))
        except RuleParseError as exc:
            logger.warning("tech_detection_loader: %s: %s", path.name, exc)
    return tuple(rules)


# Sanity exports for tests / introspection
__all__ = [
    "RULES_ROOT",
    "PRECEDENCE_DIR_NAME",
    "CLEANUP_DIR_NAME",
    "PRECEDENCE_PREDICATE_BUILDERS",
    "CLEANUP_PREDICATE_BUILDERS",
    "RuleParseError",
    "load_precedence_rules",
    "load_cleanup_rules",
]
