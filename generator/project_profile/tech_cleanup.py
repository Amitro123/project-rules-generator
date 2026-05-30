"""Declarative tech-stack cleanup rules.

Replaces the post-detection patches at ``enhanced_parser.py`` (the
``_noise_tokens`` strip + the ``if "reflex" in tech_stack`` block) with a
list of declarative records. ``apply_tech_cleanup_rules`` is generic — it
iterates rule records and strips the configured techs whenever a rule's
predicate fires.

The ``DEFAULT_TECH_CLEANUP_RULES`` module-level table is reassigned at
import time by ``generator.project_profile.__init__`` after loading YAML
rule files. ``apply_tech_cleanup_rules`` reads it at CALL time so the
reassignment is picked up correctly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

# A predicate takes (current tech_stack, cleanup_context) → True when the
# rule's strip set should be applied. The context carries auxiliary signal
# (e.g. ``test_framework``) that the predicate may need.
CleanupPredicate = Callable[[FrozenSet[str], Dict[str, Any]], bool]


@dataclass(frozen=True)
class TechCleanupRule:
    """One declarative rule for removing techs from a detected stack.

    Fields
    ------
    name : human label; surfaces in shadow logs and CleanupTrace.
    predicate : callable returning True when this rule's strip set applies.
        Receives a snapshot of the *current* tech_stack (after earlier rules
        have already run) plus a context dict (typically ``{"test_framework":
        "pytest"}`` or similar).
    strip : the techs this rule removes if the predicate fires.
    reason : prose explanation. Used in shadow logs so users can see *why*
        a tech was removed without reading the code.
    """

    name: str
    predicate: CleanupPredicate
    strip: FrozenSet[str]
    reason: str


@dataclass(frozen=True)
class CleanupTrace:
    """One rule's effect on the tech_stack, recorded for diagnostics."""

    rule_name: str
    stripped: FrozenSet[str]
    reason: str


# Predicate factories — closures over the values they test, keeping the rule
# table itself terse and declarative.


def _always_apply(_techs: FrozenSet[str], _ctx: Dict[str, Any]) -> bool:
    return True


def _when_stack_contains(token: str) -> CleanupPredicate:
    """Fire when `token` is currently present in the tech_stack."""

    def _pred(techs: FrozenSet[str], _ctx: Dict[str, Any]) -> bool:
        return token in techs

    return _pred


def _when_context_key_not_equal(key: str, value: Any) -> CleanupPredicate:
    """Fire unless context[key] equals value. Used to strip a leaked
    framework keyword UNLESS that framework is actually the project's
    test framework."""

    def _pred(_techs: FrozenSet[str], ctx: Dict[str, Any]) -> bool:
        return ctx.get(key) != value

    return _pred


# Default cleanup rule table. Populated by
# ``generator.project_profile.__init__._load_rules_at_import`` from the
# YAML rule files at import time. Pre-declared as empty so any tooling
# that references the name during import sees a valid value rather than
# NameError. ``apply_tech_cleanup_rules`` looks this up at CALL time so
# the reassignment by the loader propagates correctly.
DEFAULT_TECH_CLEANUP_RULES: Tuple[TechCleanupRule, ...] = ()


def apply_tech_cleanup_rules(
    tech_stack: FrozenSet[str],
    context: Optional[Dict[str, Any]] = None,
    rules: Optional[Tuple[TechCleanupRule, ...]] = None,
) -> Tuple[FrozenSet[str], Tuple[CleanupTrace, ...]]:
    """Apply each cleanup rule in order; return the post-cleanup tech_stack
    plus a trace of which rules actually changed anything.

    Pure function. No I/O, no globals, no project-specific branches —
    rule data drives behaviour. Adding a new cleanup rule = appending to
    DEFAULT_TECH_CLEANUP_RULES (or passing a custom tuple at call site).

    Parameters
    ----------
    tech_stack : the set of detected techs to clean.
    context : auxiliary signal predicates may consult (e.g.
        ``{"test_framework": "pytest"}``). ``None`` is treated as ``{}``.
    rules : ordered tuple of TechCleanupRule. Defaults to
        ``DEFAULT_TECH_CLEANUP_RULES``. Passing a custom tuple lets
        callers (especially tests) drive arbitrary policy with no code
        changes.

    Returns
    -------
    (cleaned_stack, traces) :
        * cleaned_stack : a new frozenset; original is not mutated.
        * traces : tuple of CleanupTrace records — one per rule that
          actually stripped something. Empty when nothing was removed.
          Useful for shadow logs ("why did 'react' disappear?").
    """
    ctx = context or {}
    current = frozenset(tech_stack)
    traces: List[CleanupTrace] = []

    # Default to the module-level table, evaluated at CALL time so YAML
    # rules loaded at import time are picked up correctly.
    if rules is None:
        rules = DEFAULT_TECH_CLEANUP_RULES

    for rule in rules:
        if not rule.predicate(current, ctx):
            continue
        # Only strip what's actually there; CleanupTrace records the
        # intersection (so traces never claim to have removed something
        # that wasn't present).
        stripped_here = rule.strip & current
        if not stripped_here:
            continue
        current = current - stripped_here
        traces.append(
            CleanupTrace(
                rule_name=rule.name,
                stripped=stripped_here,
                reason=rule.reason,
            )
        )

    return current, tuple(traces)
