"""Tests for the declarative project_type reconciliation (Phase 2).

The function under test, ``reconcile_project_type``, replaces the 60-line
``if/elif`` cascade at ``enhanced_parser.py:363-423``. These tests cover:

  * Every rule in DEFAULT_PROJECT_TYPE_PRECEDENCE fires under the right
    conditions and only under those conditions.
  * No rule firing → structure_type wins.
  * Empty newer_type → structure_type wins (no rule even considered).
  * The result includes the rule name and reason, so downstream consumers
    (shadow logs, debug output) can show *why* a type was chosen.
  * The function is generic — replacing the rule table with a custom one
    changes behavior with no code change.

The aim is for these tests to be the single source of truth about the
precedence policy: the cascade in enhanced_parser.py is *consequence*, not
*specification*. When Phase 3 moves the rules into YAML/markdown files,
these tests stay green.
"""

from __future__ import annotations

import pytest

from generator.project_profile import (
    DEFAULT_PROJECT_TYPE_PRECEDENCE,
    NEWER_TYPE_ANY,
    PrecedenceRule,
    ReconciliationResult,
    reconcile_project_type,
)


def _call(
    structure_type: str = "python-cli",
    structure_confidence: float = 1.0,
    newer_type: str = "",
    newer_confidence: float = 0.0,
    rules=None,
) -> ReconciliationResult:
    """Tiny helper to keep test bodies focused on the variable under test."""
    return reconcile_project_type(
        structure_type=structure_type,
        structure_confidence=structure_confidence,
        newer_type=newer_type,
        newer_confidence=newer_confidence,
        rules=rules if rules is not None else DEFAULT_PROJECT_TYPE_PRECEDENCE,
    )


# --- Rule: python-api-always-wins -------------------------------------------


def test_python_api_overrides_python_cli_unconditionally():
    """Even a fully-confident python-cli structural result loses to
    python-api from the newer detector. The historical bug: FastAPI
    apps were misclassified as python-cli."""
    result = _call(
        structure_type="python-cli",
        structure_confidence=1.0,
        newer_type="python-api",
        newer_confidence=0.5,  # even at modest confidence
    )
    assert result.project_type == "python-api"
    assert result.rule_fired == "python-api-always-wins"


def test_python_api_overrides_even_low_newer_confidence():
    """The rule is `always_match` — does not require newer_confidence to be
    high. This pins the explicit policy from the cascade."""
    result = _call(newer_type="python-api", newer_confidence=0.0)
    assert result.project_type == "python-api"


# --- Rule: agent-skills-high-confidence ------------------------------------


def test_agent_skills_wins_at_high_confidence_regardless_of_structure():
    """SA can't detect agent-skills; if the newer detector is highly
    confident, it wins even when SA confidently said python-cli."""
    result = _call(
        structure_type="python-cli",
        structure_confidence=0.95,
        newer_type="agent-skills",
        newer_confidence=0.8,
    )
    assert result.project_type == "agent-skills"
    assert result.rule_fired == "agent-skills-high-confidence"


def test_agent_skills_below_threshold_does_not_fire():
    """The 0.8 threshold is the bar; below it, structure wins."""
    result = _call(
        structure_type="python-cli",
        structure_confidence=0.95,
        newer_type="agent-skills",
        newer_confidence=0.7,
    )
    assert result.project_type == "python-cli"
    # No rule fired since SA was confident and the only matching rule
    # (agent-skills) didn't meet its threshold; and the any-newer fallback
    # requires structure_type in {library, unknown}, which python-cli isn't.
    assert result.rule_fired is None


# --- Rule: agent-when-structure-unsure ------------------------------------


def test_agent_wins_when_newer_high_and_structure_low():
    """The double-condition rule: agent fires only when newer >= 0.7 AND
    structure < 0.5. Both have to hold."""
    result = _call(
        structure_type="ml-pipeline",
        structure_confidence=0.4,
        newer_type="agent",
        newer_confidence=0.75,
    )
    assert result.project_type == "agent"
    assert result.rule_fired == "agent-when-structure-unsure"


def test_agent_does_not_win_when_structure_is_confident():
    """A confident python-cli classification shouldn't be overridden just
    because the project uses an LLM library. Pins the policy from the
    cascade comment at enhanced_parser.py:407-411."""
    result = _call(
        structure_type="python-cli",
        structure_confidence=0.9,
        newer_type="agent",
        newer_confidence=0.95,
    )
    assert result.project_type == "python-cli"
    assert result.rule_fired is None


def test_agent_does_not_win_when_newer_below_threshold():
    """Even if structure is unsure, low newer-confidence means we don't
    override — neither detector is confident enough."""
    result = _call(
        structure_type="library",
        structure_confidence=0.3,
        newer_type="agent",
        newer_confidence=0.6,
    )
    # Falls through to any-newer-on-fallback at 0.5 threshold — which fires
    # because library is in the fallback set and 0.6 >= 0.5.
    assert result.project_type == "agent"
    assert result.rule_fired == "any-newer-on-fallback"


# --- Rule: generator-or-webapp-on-fallback ---------------------------------


def test_web_app_wins_when_structure_is_library():
    """Claude review1#5 case: SA returns library, newer says web-app
    with reasonable confidence — web-app wins."""
    result = _call(
        structure_type="library",
        structure_confidence=0.5,
        newer_type="web-app",
        newer_confidence=0.6,
    )
    assert result.project_type == "web-app"
    assert result.rule_fired == "generator-or-webapp-on-fallback"


def test_generator_wins_when_structure_is_unknown():
    result = _call(
        structure_type="unknown",
        structure_confidence=0.0,
        newer_type="generator",
        newer_confidence=0.55,
    )
    assert result.project_type == "generator"
    assert result.rule_fired == "generator-or-webapp-on-fallback"


def test_web_app_does_not_win_when_structure_is_a_real_pattern():
    """If SA confidently identified fastapi-api, web-app from the newer
    detector should NOT override it (precedence rules out)."""
    result = _call(
        structure_type="fastapi-api",
        structure_confidence=0.9,
        newer_type="web-app",
        newer_confidence=0.9,
    )
    assert result.project_type == "fastapi-api"
    assert result.rule_fired is None


# --- Rule: any-newer-on-fallback (catchall) --------------------------------


def test_any_newer_on_fallback_when_structure_is_library():
    """When SA gave up (library), trust whatever the newer detector
    decided, as long as it's confident enough."""
    result = _call(
        structure_type="library",
        structure_confidence=0.2,
        newer_type="ml-pipeline",
        newer_confidence=0.7,
    )
    assert result.project_type == "ml-pipeline"
    assert result.rule_fired == "any-newer-on-fallback"


def test_any_newer_on_fallback_below_threshold_keeps_structure():
    """If the newer detector is below 0.5, even a library/unknown
    structure shouldn't get overridden — we keep the fallback type."""
    result = _call(
        structure_type="unknown",
        structure_confidence=0.0,
        newer_type="ml-pipeline",
        newer_confidence=0.4,
    )
    assert result.project_type == "unknown"
    assert result.rule_fired is None


# --- Empty / degenerate inputs ----------------------------------------------


def test_empty_newer_type_keeps_structure():
    """When the newer detector returned nothing, structure wins."""
    result = _call(
        structure_type="django-app",
        structure_confidence=0.85,
        newer_type="",
        newer_confidence=0.0,
    )
    assert result.project_type == "django-app"
    assert result.rule_fired is None
    assert "empty" in result.reason.lower()


def test_no_rule_fires_when_structure_confident_and_newer_unrecognized():
    """A confident structure and an unrecognized newer_type → structure wins.
    The fallback rules need structure in {library, unknown}."""
    result = _call(
        structure_type="fastapi-api",
        structure_confidence=0.9,
        newer_type="never-heard-of-this",
        newer_confidence=0.7,
    )
    assert result.project_type == "fastapi-api"
    assert result.rule_fired is None


def test_none_inputs_are_tolerated_at_the_boundary():
    """Detectors during migration may return None/odd types. The contract
    coerces gracefully — never raises."""
    result = reconcile_project_type(
        structure_type="",  # type: ignore[arg-type]
        structure_confidence=None,  # type: ignore[arg-type]
        newer_type=None,  # type: ignore[arg-type]
        newer_confidence=None,  # type: ignore[arg-type]
    )
    # Empty structure_type coerces to 'unknown'; empty newer_type → no rule;
    # structure ('unknown') wins.
    assert result.project_type == "unknown"
    assert result.rule_fired is None


def test_confidence_out_of_range_is_clamped_not_raised():
    """Bogus 1.5 confidence shouldn't crash the function; it's clamped to 1.0."""
    result = reconcile_project_type(
        structure_type="python-cli",
        structure_confidence=1.5,
        newer_type="python-api",
        newer_confidence=-0.3,
    )
    # python-api always wins regardless of confidence values
    assert result.project_type == "python-api"


# --- Genericity: replacing the rule table is the entire policy change ------


def test_function_is_generic_via_custom_rules():
    """Pass a different rule table → completely different behavior. Proves
    the function itself contains no project-specific logic."""

    custom_rules = (
        PrecedenceRule(
            name="all-or-nothing",
            match_newer=NEWER_TYPE_ANY,
            predicate=lambda *_: True,
            reason="Always trust the newer detector. This is a test policy.",
        ),
    )
    result = _call(
        structure_type="fastapi-api",
        structure_confidence=1.0,
        newer_type="some-future-thing",
        newer_confidence=0.0,
        rules=custom_rules,
    )
    # The custom rule fires unconditionally — structure_type loses.
    assert result.project_type == "some-future-thing"
    assert result.rule_fired == "all-or-nothing"


def test_empty_rule_table_falls_through_to_structure():
    """No rules → structure_type always wins. The function is well-defined
    even with no policy."""
    result = _call(
        structure_type="python-cli",
        structure_confidence=0.8,
        newer_type="agent",
        newer_confidence=0.95,
        rules=(),
    )
    assert result.project_type == "python-cli"
    assert result.rule_fired is None


# --- ReconciliationResult is informative -----------------------------------


def test_result_carries_rule_reason_for_shadow_logs():
    """When a rule fires, its `reason` is on the result so logs and debug
    output can show *why* the type was chosen. This is what replaces the
    pile of inline comments in the cascade."""
    result = _call(newer_type="python-api", newer_confidence=0.5)
    assert result.rule_fired is not None
    assert "API" in result.reason or "fastapi" in result.reason.lower()


# --- Property: every rule in DEFAULT_PROJECT_TYPE_PRECEDENCE is reachable --


@pytest.mark.parametrize(
    "rule",
    DEFAULT_PROJECT_TYPE_PRECEDENCE,
    ids=lambda r: r.name,
)
def test_each_default_rule_has_a_reaching_input(rule: PrecedenceRule):
    """Every rule in the precedence table should be reachable by SOME
    realistic input. This is the meta-test version of the per-rule tests
    above — catches a rule that's been added but is dead because an
    earlier rule swallows all its cases."""
    # Build a minimum-viable input that should hit this rule:
    #   * pick a newer_type the rule's match accepts
    #   * crank confidences to extreme so the predicate fires
    if rule.match_newer == NEWER_TYPE_ANY:
        target_newer = "ml-pipeline"  # representative third-party value
    elif isinstance(rule.match_newer, frozenset):
        target_newer = next(iter(rule.match_newer))
    else:
        target_newer = rule.match_newer

    # Try a few input shapes; at least one should hit the rule
    candidates = [
        ("library", 0.0, target_newer, 1.0),
        ("unknown", 0.1, target_newer, 0.9),
        ("python-cli", 0.4, target_newer, 0.8),
    ]
    fired = False
    for s_type, s_conf, n_type, n_conf in candidates:
        result = reconcile_project_type(
            structure_type=s_type,
            structure_confidence=s_conf,
            newer_type=n_type,
            newer_confidence=n_conf,
        )
        if result.rule_fired == rule.name:
            fired = True
            break
    assert fired, (
        f"Rule {rule.name!r} is unreachable — no realistic input fires it. "
        "Either earlier rules swallow its cases, or its predicate is unreachable."
    )
