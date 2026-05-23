"""Tests for dedupe_skill_refs (Phase 4d).

Single canonical dedup pass that replaces three scattered sites:

  1. `_parse_skill_refs` in project_profile.py — contract-level dedup
     by (scope, terminal_name), no cross-scope precedence (lets the
     invariant catch collisions). UNCHANGED by Phase 4d.
  2. cross-scope dedup in cli/skill_pipeline.py:_auto_generate_skills —
     drops learned/X when project/X exists (the "Bug 4 fix" inline block).
  3. per-scope `seen_*` dedup in clinerules_generator.py:44-46 — dedupes
     terminal names within each scope as it iterates.

After this phase, sites 2 and 3 both call `dedupe_skill_refs`. The
function is generic — the precedence policy is a parameter, not
hardcoded in the function body.
"""

from __future__ import annotations

import pytest

from generator.project_profile import SKILL_SCOPES, dedupe_skill_refs

# --- Cross-scope precedence (the nbug.md case) ------------------------------


def test_project_beats_learned_for_same_terminal_name():
    """nbug.md: pydantic-validation appeared in both project/ and learned/.
    The contract invariant flags this as a collision; the pipeline must
    dedup BEFORE the contract sees it. project wins by default precedence."""
    refs = {"project/pydantic-validation", "learned/fastapi/pydantic-validation"}
    survivors = dedupe_skill_refs(refs)
    assert "project/pydantic-validation" in survivors
    assert "learned/fastapi/pydantic-validation" not in survivors
    assert len(survivors) == 1


def test_project_beats_builtin_for_same_terminal_name():
    refs = {"project/code-review", "builtin/code-review"}
    survivors = dedupe_skill_refs(refs)
    assert "project/code-review" in survivors
    assert "builtin/code-review" not in survivors


def test_learned_beats_builtin_for_same_terminal_name():
    refs = {"learned/fastapi/code-review", "builtin/code-review"}
    survivors = dedupe_skill_refs(refs)
    assert "learned/fastapi/code-review" in survivors
    assert "builtin/code-review" not in survivors


def test_default_precedence_matches_skill_scopes_constant():
    """Default precedence is the SKILL_SCOPES module constant; if that
    constant ever changes order, this test catches the silent shift."""
    assert SKILL_SCOPES == ("project", "learned", "builtin")
    # Project > learned > builtin in default precedence
    refs = {"project/X", "learned/cat/X", "builtin/X"}
    survivors = dedupe_skill_refs(refs)
    assert survivors == frozenset({"project/X"})


# --- Same-scope, different category prefixes ------------------------------


def test_same_scope_different_categories_collapsed_deterministically():
    """The matcher emits 3-part refs like 'learned/fastapi/async-patterns'
    and 'learned/pytest/async-patterns' — same terminal name, different
    category prefix. Dedup picks the lexicographically-first ref so the
    result is deterministic across runs."""
    refs = {
        "learned/pytest/async-patterns",
        "learned/fastapi/async-patterns",
        "learned/general/async-patterns",
    }
    survivors = dedupe_skill_refs(refs)
    assert len(survivors) == 1
    # 'fastapi' < 'general' < 'pytest' lexicographically
    assert "learned/fastapi/async-patterns" in survivors


def test_same_scope_2part_and_3part_collapsed():
    """A 2-part ref `learned/X` and a 3-part ref `learned/cat/X` are the
    same skill under different shapes — dedup collapses them."""
    refs = {"learned/async-patterns", "learned/fastapi/async-patterns"}
    survivors = dedupe_skill_refs(refs)
    assert len(survivors) == 1
    # '2-part' lexicographic comparison: "learned/async-patterns" sorts before
    # "learned/fastapi/async-patterns" because shorter strings sort first
    # when the common prefix is identical. Either result is correct as long
    # as exactly one survives.
    winner = next(iter(survivors))
    assert winner in refs


# --- Custom precedence ----------------------------------------------------


def test_custom_precedence_inverts_default():
    """The precedence is a parameter — passing a different tuple changes
    which scope wins. Proves the function carries no hardcoded policy."""
    refs = {"project/X", "learned/cat/X", "builtin/X"}
    # Invert so builtin beats learned beats project
    survivors = dedupe_skill_refs(refs, scope_precedence=("builtin", "learned", "project"))
    assert survivors == frozenset({"builtin/X"})


def test_custom_precedence_with_subset_of_scopes_drops_unlisted():
    """If a scope is absent from scope_precedence, its refs are dropped
    entirely (not silently kept). Predictable, explicit behaviour."""
    refs = {"project/X", "learned/cat/X", "builtin/X"}
    # Only allow learned through
    survivors = dedupe_skill_refs(refs, scope_precedence=("learned",))
    assert survivors == frozenset({"learned/cat/X"})


# --- Multiple terminal names ----------------------------------------------


def test_dedup_preserves_distinct_skills():
    """Different terminal names are not collapsed — they're distinct skills."""
    refs = {
        "project/foo",
        "learned/bar",
        "builtin/baz",
    }
    survivors = dedupe_skill_refs(refs)
    assert survivors == refs


def test_multi_collision_independent_per_terminal():
    """Each terminal name dedups independently. Two collisions in the
    input produce two surviving refs, one per terminal."""
    refs = {
        "project/A",
        "learned/cat/A",
        "project/B",
        "builtin/B",
        "learned/cat/C",
    }
    survivors = dedupe_skill_refs(refs)
    assert survivors == frozenset({"project/A", "project/B", "learned/cat/C"})


# --- Degenerate / malformed input ------------------------------------------


def test_empty_input_returns_empty():
    assert dedupe_skill_refs(set()) == frozenset()
    assert dedupe_skill_refs([]) == frozenset()


def test_iterable_input_accepted():
    """Accepts any iterable, not just sets. Lists, tuples, generators all work."""
    refs_list = ["project/X", "learned/X"]
    refs_tuple = ("project/X", "learned/X")
    refs_gen = (r for r in ["project/X", "learned/X"])
    assert dedupe_skill_refs(refs_list) == frozenset({"project/X"})
    assert dedupe_skill_refs(refs_tuple) == frozenset({"project/X"})
    assert dedupe_skill_refs(refs_gen) == frozenset({"project/X"})


def test_empty_strings_silently_dropped():
    refs = {"", "project/X"}
    survivors = dedupe_skill_refs(refs)
    assert survivors == frozenset({"project/X"})


def test_single_segment_refs_dropped():
    """A ref like `justaname` has no scope/terminal structure — drop it."""
    refs = {"justaname", "project/X"}
    survivors = dedupe_skill_refs(refs)
    assert survivors == frozenset({"project/X"})


def test_unknown_scope_dropped():
    """A ref whose scope isn't in scope_precedence is silently dropped
    (not kept-then-deduplicated). Explicit policy: unknown = exclude."""
    refs = {"unknown_scope/X", "project/X"}
    survivors = dedupe_skill_refs(refs)
    assert survivors == frozenset({"project/X"})


def test_trailing_slash_treated_as_empty_terminal_dropped():
    """A ref ending with '/' has an empty terminal name — drop it
    rather than producing a phantom survivor."""
    refs = {"project/", "learned/cat/foo"}
    survivors = dedupe_skill_refs(refs)
    assert survivors == frozenset({"learned/cat/foo"})


# --- Determinism ----------------------------------------------------------


def test_dedup_is_deterministic_across_input_orderings():
    """Set iteration order is non-deterministic, but the function's output
    must be the same regardless of input order. Critical for reproducible
    builds."""
    refs_a = ["learned/pytest/X", "learned/fastapi/X", "learned/general/X"]
    refs_b = list(reversed(refs_a))
    refs_c = [refs_a[1], refs_a[0], refs_a[2]]
    assert dedupe_skill_refs(refs_a) == dedupe_skill_refs(refs_b) == dedupe_skill_refs(refs_c)


# --- Return type ----------------------------------------------------------


def test_returns_frozenset_for_immutability():
    """Caller can safely hold the result without defensive copying."""
    result = dedupe_skill_refs({"project/X"})
    assert isinstance(result, frozenset)
    with pytest.raises((AttributeError, TypeError)):
        result.add("project/Y")  # type: ignore[attr-defined]


# --- Integration: composes with ProjectProfile invariant ------------------


def test_deduped_output_satisfies_project_profile_invariant():
    """After dedup_skill_refs, the resulting set must not trigger the
    `skill_name_collision` invariant in ProjectProfile.validate_invariants.
    This is the contract between the pipeline (which dedupes) and the
    contract (which validates)."""
    from generator.project_profile import from_enhanced_context

    # Input that WOULD trigger a collision violation
    raw_refs = {
        "project/pydantic-validation",
        "learned/fastapi/pydantic-validation",
        "builtin/code-review",
    }
    deduped = dedupe_skill_refs(raw_refs)

    profile = from_enhanced_context(
        enhanced_context={"metadata": {}, "structure": {}, "dependencies": {}},
        project_path=__import__("pathlib").Path("/tmp/x"),
        selected_skill_refs=list(deduped),
    )
    violations = profile.validate_invariants()
    assert not any("skill_name_collision" in v for v in violations)
