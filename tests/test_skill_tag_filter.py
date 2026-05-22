"""Tests for filter_skills_by_tech_overlap (Phase 4a).

Pins the missing invariant from Bug4 / Bug6 / Bugs.md: learned skills tagged
with techs the project doesn't use must not appear in the selected set.

The function under test is generic — it takes any candidate ref set, any
tech_stack, and an injected tag-resolver callable. No hardcoded skill
knowledge. These tests use synthetic tag-resolver dicts as input, so they
don't depend on any specific skill library layout.
"""

from __future__ import annotations

from typing import Dict, FrozenSet

import pytest

from generator.project_profile import FilterTrace, filter_skills_by_tech_overlap


def _make_resolver(tag_table: Dict[str, FrozenSet[str]]):
    """Build a tag-resolver from a dict. Unknown refs return frozenset()."""

    def _resolver(ref: str) -> FrozenSet[str]:
        return tag_table.get(ref, frozenset())

    return _resolver


# --- The canonical Bug4 / Bug6 case ----------------------------------------


def test_drops_learned_skill_with_no_overlap():
    """Bug4: 'jest' learned skills selected for a pure-Python project.
    The filter drops them because their tags don't intersect tech_stack."""
    tags = {
        "learned/jest/snapshot-testing": frozenset({"jest", "javascript", "react"}),
    }
    survivors, traces = filter_skills_by_tech_overlap(
        selected_refs={"learned/jest/snapshot-testing"},
        tech_stack={"python", "langgraph", "openai"},
        tag_resolver=_make_resolver(tags),
    )
    assert survivors == frozenset()
    assert len(traces) == 1
    assert traces[0].skill_ref == "learned/jest/snapshot-testing"
    assert "no_tag_overlap" in traces[0].reason


def test_keeps_learned_skill_with_overlap():
    """A learned skill whose tags include any tech in the project survives."""
    tags = {
        "learned/fastapi/async-patterns": frozenset({"fastapi", "async", "python"}),
    }
    survivors, traces = filter_skills_by_tech_overlap(
        selected_refs={"learned/fastapi/async-patterns"},
        tech_stack={"python", "fastapi", "pytest"},
        tag_resolver=_make_resolver(tags),
    )
    assert survivors == frozenset({"learned/fastapi/async-patterns"})
    assert traces == ()


def test_mixed_selection_drops_only_the_irrelevant_ones():
    """Realistic Bug4 scenario: matcher returned 5 skills, 3 are relevant
    and 2 are leaked. The filter drops exactly the 2 with no overlap."""
    tags = {
        "learned/fastapi/async-patterns": frozenset({"fastapi", "python"}),
        "learned/pytest/coverage-patterns": frozenset({"pytest", "python"}),
        "learned/api-integration/retry-error-handling": frozenset({"api", "python"}),
        "learned/jest/snapshot-testing": frozenset({"jest", "javascript"}),  # LEAK
        "learned/react/component-patterns": frozenset({"react", "jsx"}),  # LEAK
    }
    survivors, traces = filter_skills_by_tech_overlap(
        selected_refs=set(tags.keys()),
        tech_stack={"python", "fastapi", "pytest", "openai"},
        tag_resolver=_make_resolver(tags),
    )
    assert survivors == frozenset(
        {
            "learned/fastapi/async-patterns",
            "learned/pytest/coverage-patterns",
            "learned/api-integration/retry-error-handling",
        }
    )
    dropped = {t.skill_ref for t in traces}
    assert dropped == {"learned/jest/snapshot-testing", "learned/react/component-patterns"}


# --- Scope handling ---------------------------------------------------------


def test_builtin_skills_bypass_filter():
    """Builtin skills are universal — they're shipped with PRG and apply
    to every project. They must NOT be filtered out even if their tags
    don't overlap (or have no tags at all)."""
    tags = {
        "builtin/code-review": frozenset({"code-quality"}),
    }
    survivors, _ = filter_skills_by_tech_overlap(
        selected_refs={"builtin/code-review"},
        tech_stack={"python"},  # 'code-quality' not in here
        tag_resolver=_make_resolver(tags),
    )
    assert survivors == frozenset({"builtin/code-review"})


def test_project_skills_bypass_filter():
    """Project-local skills are project-specific by definition; even if
    their tags don't overlap, they were created for this project and
    must not be dropped."""
    tags = {
        "project/custom-thing": frozenset({"obscure-internal-tag"}),
    }
    survivors, _ = filter_skills_by_tech_overlap(
        selected_refs={"project/custom-thing"},
        tech_stack={"python", "fastapi"},
        tag_resolver=_make_resolver(tags),
    )
    assert survivors == frozenset({"project/custom-thing"})


def test_filter_scope_is_configurable():
    """The set of scopes the filter applies to is a parameter. Callers
    that want to filter ALL scopes can pass a richer set."""
    tags = {
        "builtin/has-no-overlap": frozenset({"jest"}),
    }
    # Default: builtin bypasses → survives
    survivors_default, _ = filter_skills_by_tech_overlap(
        selected_refs={"builtin/has-no-overlap"},
        tech_stack={"python"},
        tag_resolver=_make_resolver(tags),
    )
    assert survivors_default == frozenset({"builtin/has-no-overlap"})

    # Override: filter builtin too → dropped
    survivors_strict, traces = filter_skills_by_tech_overlap(
        selected_refs={"builtin/has-no-overlap"},
        tech_stack={"python"},
        tag_resolver=_make_resolver(tags),
        scopes_to_filter=frozenset({"learned", "builtin"}),
    )
    assert survivors_strict == frozenset()
    assert len(traces) == 1


# --- Tag-resolver edge cases ----------------------------------------------


def test_resolver_returning_empty_keeps_skill_by_default():
    """A skill whose resolver returns frozenset() — meaning it has no
    declared tags OR the resolver couldn't find it — is kept by default
    (conservative). Absence of tags isn't proof of irrelevance."""
    tags: Dict[str, FrozenSet[str]] = {}  # all resolvers return empty
    survivors, traces = filter_skills_by_tech_overlap(
        selected_refs={"learned/some/skill"},
        tech_stack={"python"},
        tag_resolver=_make_resolver(tags),
    )
    assert survivors == frozenset({"learned/some/skill"})
    assert traces == ()


def test_strict_mode_drops_skills_with_no_tags():
    """When keep_when_no_tags=False, the filter is strict: any skill
    without resolvable tags gets dropped along with no-overlap skills."""
    tags: Dict[str, FrozenSet[str]] = {}
    survivors, traces = filter_skills_by_tech_overlap(
        selected_refs={"learned/some/skill"},
        tech_stack={"python"},
        tag_resolver=_make_resolver(tags),
        keep_when_no_tags=False,
    )
    assert survivors == frozenset()
    assert len(traces) == 1
    assert "strict_mode_no_tags" in traces[0].reason


def test_resolver_raising_keeps_skill():
    """If the resolver crashes (e.g. unreadable file), the filter must
    not propagate the exception — it keeps the skill conservatively."""

    def _broken_resolver(ref: str) -> FrozenSet[str]:
        raise RuntimeError("disk gone")

    survivors, traces = filter_skills_by_tech_overlap(
        selected_refs={"learned/some/skill"},
        tech_stack={"python"},
        tag_resolver=_broken_resolver,
    )
    assert survivors == frozenset({"learned/some/skill"})
    assert traces == ()


# --- Case-insensitivity ----------------------------------------------------


def test_tag_matching_is_case_insensitive():
    """Tech names in YAML / dependency files arrive in various cases;
    the filter normalises both sides to lowercase before comparing."""
    tags = {"learned/cat/skill": frozenset({"FastAPI"})}
    survivors, _ = filter_skills_by_tech_overlap(
        selected_refs={"learned/cat/skill"},
        tech_stack={"fastapi"},  # lowercase
        tag_resolver=_make_resolver(tags),
    )
    assert survivors == frozenset({"learned/cat/skill"})


def test_tech_stack_matching_is_case_insensitive():
    tags = {"learned/cat/skill": frozenset({"react"})}
    survivors, _ = filter_skills_by_tech_overlap(
        selected_refs={"learned/cat/skill"},
        tech_stack={"REACT", "PYTHON"},  # uppercase
        tag_resolver=_make_resolver(tags),
    )
    assert survivors == frozenset({"learned/cat/skill"})


# --- Pure-function properties ----------------------------------------------


def test_filter_does_not_mutate_input():
    """The function must return a NEW frozenset; never mutate the input set."""
    original = {"learned/jest/x"}
    tags = {"learned/jest/x": frozenset({"jest"})}
    filter_skills_by_tech_overlap(
        selected_refs=original,
        tech_stack={"python"},
        tag_resolver=_make_resolver(tags),
    )
    # Input is unchanged
    assert original == {"learned/jest/x"}


def test_empty_input_returns_empty():
    survivors, traces = filter_skills_by_tech_overlap(
        selected_refs=set(),
        tech_stack={"python"},
        tag_resolver=_make_resolver({}),
    )
    assert survivors == frozenset()
    assert traces == ()


def test_empty_tech_stack_drops_all_filterable_skills():
    """If we don't know the project's tech, every learned skill fails the
    overlap check. Builtins still bypass. This is a degenerate but
    well-defined behaviour — predictable, not surprising."""
    tags = {
        "learned/x/y": frozenset({"some-tag"}),
        "builtin/code-review": frozenset({"code-quality"}),
    }
    survivors, traces = filter_skills_by_tech_overlap(
        selected_refs={"learned/x/y", "builtin/code-review"},
        tech_stack=set(),
        tag_resolver=_make_resolver(tags),
    )
    assert survivors == frozenset({"builtin/code-review"})
    assert len(traces) == 1
    assert traces[0].skill_ref == "learned/x/y"


# --- Genericity: arbitrary resolvers, arbitrary scopes ---------------------


def test_function_works_with_any_resolver_shape():
    """The filter has no idea where tags come from. Any callable that
    accepts (str) and returns an iterable of strings works."""

    # A resolver that derives tags from the ref itself — weird but valid.
    def _derive_from_ref(ref: str) -> FrozenSet[str]:
        # Tag = the middle segment of the ref
        parts = ref.split("/")
        return frozenset({parts[1]}) if len(parts) >= 2 else frozenset()

    survivors, _ = filter_skills_by_tech_overlap(
        selected_refs={"learned/python/abc", "learned/jest/xyz"},
        tech_stack={"python"},
        tag_resolver=_derive_from_ref,
    )
    assert survivors == frozenset({"learned/python/abc"})


def test_filter_trace_records_full_diagnostic():
    """Each dropped skill's trace carries the skill's tags and the
    project's tech for inspection."""
    tags = {"learned/leaked/skill": frozenset({"jest", "react"})}
    _, traces = filter_skills_by_tech_overlap(
        selected_refs={"learned/leaked/skill"},
        tech_stack={"python", "fastapi"},
        tag_resolver=_make_resolver(tags),
    )
    assert len(traces) == 1
    t = traces[0]
    assert t.skill_ref == "learned/leaked/skill"
    assert t.skill_tags == frozenset({"jest", "react"})
    assert t.project_tech == frozenset({"python", "fastapi"})


def test_filter_trace_is_immutable():
    """FilterTrace is a frozen dataclass — diagnostics can be safely
    shared across logging/reporting without defensive copies."""
    tags = {"learned/leaked/skill": frozenset({"jest"})}
    _, traces = filter_skills_by_tech_overlap(
        selected_refs={"learned/leaked/skill"},
        tech_stack={"python"},
        tag_resolver=_make_resolver(tags),
    )
    assert len(traces) == 1
    with pytest.raises((AttributeError, TypeError)):
        traces[0].skill_ref = "tampered"  # type: ignore[misc]


# --- Boundary: malformed refs ----------------------------------------------


def test_empty_ref_strings_are_ignored():
    """Empty strings in the input set are skipped, not crashed on."""
    tags = {"learned/x/y": frozenset({"python"})}
    survivors, _ = filter_skills_by_tech_overlap(
        selected_refs={"", "learned/x/y"},
        tech_stack={"python"},
        tag_resolver=_make_resolver(tags),
    )
    assert "" not in survivors
    assert "learned/x/y" in survivors


def test_single_segment_ref_treated_as_unknown_scope():
    """A ref without '/' has no scope. It falls in the 'not in
    scopes_to_filter' branch and bypasses the filter."""
    tags = {"justaname": frozenset({"jest"})}
    survivors, _ = filter_skills_by_tech_overlap(
        selected_refs={"justaname"},
        tech_stack={"python"},
        tag_resolver=_make_resolver(tags),
    )
    # Scope was '' (empty after split); not in default filter scopes; kept.
    assert "justaname" in survivors
