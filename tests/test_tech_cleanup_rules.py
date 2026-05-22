"""Tests for declarative tech-stack cleanup rules (Phase 3a).

These tests pin the same behavior the post-detection patches at
``enhanced_parser.py:431-438`` used to enforce (noise-token strip + Reflex
JS-artifact strip), but now expressed as a generic function over a rule
list — `apply_tech_cleanup_rules`.

The aim is: when Phase 3b moves DEFAULT_TECH_CLEANUP_RULES into YAML files,
these tests stay green because they test the FUNCTION, not the source of
the rule data.
"""

from __future__ import annotations

import pytest

from generator.project_profile import (
    DEFAULT_TECH_CLEANUP_RULES,
    CleanupTrace,
    TechCleanupRule,
    apply_tech_cleanup_rules,
)

# --- Each default rule fires under the right conditions --------------------


def test_strip_gpt_always_fires():
    """The gpt-stripping rule fires unconditionally — 'gpt' is a model
    nickname, not a package, and pollutes skill matching wherever it
    appears in tech_stack."""
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"python", "openai", "gpt"}),
        context={},
    )
    assert "gpt" not in cleaned
    assert "openai" in cleaned
    assert any(t.rule_name == "strip-gpt-vague-token" for t in traces)
    # Trace records exactly what was removed
    gpt_trace = next(t for t in traces if t.rule_name == "strip-gpt-vague-token")
    assert gpt_trace.stripped == frozenset({"gpt"})


def test_strip_jest_when_not_test_framework():
    """Bug4: 'jest' leaked into tech_stack from skill-name matching even
    though the project uses pytest. Cleanup rule strips jest unless the
    project's test_framework actually IS jest."""
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"python", "pytest", "jest"}),
        context={"test_framework": "pytest"},
    )
    assert "jest" not in cleaned
    assert "pytest" in cleaned
    assert any(t.rule_name == "strip-jest-when-not-test-framework" for t in traces)


def test_jest_preserved_when_it_IS_the_test_framework():
    """A genuine Jest project must keep 'jest' in tech_stack. The rule
    only strips it when test_framework is anything other than 'jest'."""
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"node", "react", "jest"}),
        context={"test_framework": "jest"},
    )
    assert "jest" in cleaned
    # No jest-strip trace
    assert not any(t.rule_name == "strip-jest-when-not-test-framework" for t in traces)


def test_strip_reflex_js_build_artifacts():
    """Bug8: Reflex compiles Python to React/Next.js in `.web/`. Those JS
    deps are build artifacts, not project tech. The rule strips them
    whenever 'reflex' is in the stack."""
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"reflex", "python", "react", "node", "javascript", "typescript", "nextjs"}),
        context={},
    )
    assert "reflex" in cleaned  # Reflex itself is kept
    assert "python" in cleaned  # Real project tech kept
    # JS build artifacts gone
    for stripped_tech in ("react", "node", "javascript", "typescript", "nextjs"):
        assert stripped_tech not in cleaned, f"{stripped_tech} should have been stripped"
    assert any(t.rule_name == "strip-reflex-js-build-artifacts" for t in traces)


def test_react_preserved_in_non_reflex_react_project():
    """A real React project (no Reflex) must keep React in tech_stack."""
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"react", "typescript", "node"}),
        context={},
    )
    assert "react" in cleaned
    assert "typescript" in cleaned
    assert "node" in cleaned
    # No reflex-strip trace
    assert not any(t.rule_name == "strip-reflex-js-build-artifacts" for t in traces)


# --- The function is pure and generic --------------------------------------


def test_function_does_not_mutate_input():
    """`apply_tech_cleanup_rules` must return a NEW frozenset; never
    mutate the caller's stack. Frozen sets can't be mutated anyway, but
    the contract still applies — no shared state with the input."""
    original = frozenset({"gpt", "python"})
    cleaned, _ = apply_tech_cleanup_rules(tech_stack=original, context={})
    assert original == frozenset({"gpt", "python"})  # unchanged
    assert cleaned == frozenset({"python"})  # gpt stripped


def test_no_traces_when_nothing_is_stripped():
    """A clean tech_stack returns the same set + an empty trace tuple."""
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"python", "fastapi", "pytest"}),
        context={"test_framework": "pytest"},
    )
    assert cleaned == frozenset({"python", "fastapi", "pytest"})
    assert traces == ()


def test_empty_input_returns_empty():
    """Edge case: empty stack in → empty stack out, no traces."""
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset(),
        context={},
    )
    assert cleaned == frozenset()
    assert traces == ()


def test_none_context_is_tolerated():
    """Callers that don't have auxiliary signal should be able to pass
    None and get sane behavior — rules that depend on context simply
    don't fire."""
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"jest", "react"}),
        context=None,
    )
    # jest still stripped because the rule fires when context.get('test_framework')
    # != 'jest', and None.get() effectively returns None which != 'jest'.
    assert "jest" not in cleaned


# --- Genericity: custom rule tables drive arbitrary behavior ----------------


def test_custom_rules_override_default_behavior():
    """Pass a custom rule list and the function applies THOSE rules, not
    the defaults. This proves the function carries no project-specific
    logic — the rules are pure data."""

    custom = (
        TechCleanupRule(
            name="strip-everything-test",
            predicate=lambda _techs, _ctx: True,
            strip=frozenset({"python", "fastapi", "openai"}),
            reason="Test policy: clear out a specific custom set.",
        ),
    )

    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"python", "fastapi", "openai", "kept-tech"}),
        context={},
        rules=custom,
    )

    assert cleaned == frozenset({"kept-tech"})
    assert len(traces) == 1
    assert traces[0].rule_name == "strip-everything-test"


def test_empty_rule_table_is_a_passthrough():
    """No rules → input is returned unchanged."""
    stack = frozenset({"python", "gpt", "jest", "react"})  # would normally trip defaults
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=stack,
        context={"test_framework": "pytest"},
        rules=(),
    )
    assert cleaned == stack  # nothing stripped
    assert traces == ()


def test_rules_are_applied_in_order():
    """Each rule sees the result of all prior rules. Order matters."""

    custom = (
        TechCleanupRule(
            name="first-strip",
            predicate=lambda _techs, _ctx: True,
            strip=frozenset({"alpha"}),
            reason="strip alpha first",
        ),
        TechCleanupRule(
            name="second-strip-if-alpha-gone",
            # Fires only when alpha is already stripped — proves ordering
            predicate=lambda techs, _ctx: "alpha" not in techs,
            strip=frozenset({"beta"}),
            reason="strip beta only after alpha is gone",
        ),
    )

    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"alpha", "beta", "gamma"}),
        context={},
        rules=custom,
    )

    assert cleaned == frozenset({"gamma"})
    # Both rules fired in order
    assert [t.rule_name for t in traces] == ["first-strip", "second-strip-if-alpha-gone"]


# --- CleanupTrace records exactly what happened ----------------------------


def test_trace_only_reports_techs_actually_present():
    """The trace.stripped is the INTERSECTION of rule.strip and the
    current stack — it never claims to have removed something that
    wasn't there."""
    custom = (
        TechCleanupRule(
            name="big-strip-but-most-not-present",
            predicate=lambda _techs, _ctx: True,
            strip=frozenset({"alpha", "beta", "gamma", "delta", "epsilon"}),
            reason="strip a lot, but only some are present",
        ),
    )
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"alpha", "kept"}),
        context={},
        rules=custom,
    )
    assert cleaned == frozenset({"kept"})
    assert len(traces) == 1
    # Trace only reports the intersection (alpha), not the entire strip set
    assert traces[0].stripped == frozenset({"alpha"})


def test_rule_with_no_effect_produces_no_trace():
    """When a rule's predicate fires but its strip set has no overlap with
    the current stack, no trace is recorded. Traces should only describe
    real changes."""
    custom = (
        TechCleanupRule(
            name="strip-things-not-present",
            predicate=lambda _techs, _ctx: True,
            strip=frozenset({"never-in-stack"}),
            reason="strip something that isn't there",
        ),
    )
    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"actually-here"}),
        context={},
        rules=custom,
    )
    assert cleaned == frozenset({"actually-here"})
    assert traces == ()


# --- Every default rule is reachable ---------------------------------------


@pytest.mark.parametrize(
    "rule",
    DEFAULT_TECH_CLEANUP_RULES,
    ids=lambda r: r.name,
)
def test_each_default_rule_has_a_reaching_input(rule: TechCleanupRule):
    """Meta-test: every rule in DEFAULT_TECH_CLEANUP_RULES is reachable
    by SOME plausible input. Catches a rule that's been added but is dead
    because its predicate never matches realistic context.

    The "universe" stack here is intentionally rich — it includes the rule's
    own strip set (so the rule has something to remove) PLUS common
    predicate-trigger tokens (reflex, react, python, …) so rules whose
    predicate checks for the presence of a triggering tech can still fire.
    """
    # A broad stack covering rule.strip plus common predicate triggers.
    # This keeps the meta-test generic: it doesn't need to know which
    # token each rule's predicate depends on.
    trigger_universe = frozenset(
        {"reflex", "react", "python", "node", "javascript", "typescript", "nextjs", "jest", "gpt", "fastapi"}
    )
    stack = frozenset(rule.strip) | trigger_universe

    candidate_contexts = [
        {},
        {"test_framework": "pytest"},
        {"test_framework": "jest"},
        {"test_framework": None},
    ]
    fired = False
    for ctx in candidate_contexts:
        _, traces = apply_tech_cleanup_rules(
            tech_stack=stack,
            context=ctx,
            rules=(rule,),  # isolate this single rule
        )
        if any(t.rule_name == rule.name for t in traces):
            fired = True
            break
    assert fired, (
        f"Rule {rule.name!r} is unreachable — no plausible input fires it. "
        "Either the predicate is wrong, or this rule should be removed."
    )


# --- Type-safety / immutability --------------------------------------------


def test_trace_is_immutable():
    """CleanupTrace is a frozen dataclass — caller can't accidentally
    edit a trace and mislead later inspection."""
    _, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"gpt"}),
        context={},
    )
    assert len(traces) >= 1
    with pytest.raises((AttributeError, TypeError)):
        traces[0].rule_name = "tampered"  # type: ignore[misc]


def test_cleanup_rule_is_immutable():
    """TechCleanupRule itself is frozen — rule tables can't be tampered
    with at runtime to bypass policy."""
    rule = DEFAULT_TECH_CLEANUP_RULES[0]
    with pytest.raises((AttributeError, TypeError)):
        rule.name = "tampered"  # type: ignore[misc]
