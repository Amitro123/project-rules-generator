"""Tests for negation-aware tech extraction in the README parser.

Closes the over-matching bug surfaced during Phase 5 of the systemic-bug
refactor: a README that says *"This is not a Python application"* must
not cause ``python`` to land in the detected tech list.

The fix lives in ``generator/analyzers/readme_parser.py``:
``_tech_has_non_negated_mention``. These tests pin the boundary cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.analyzers.readme_parser import _tech_has_non_negated_mention, extract_tech_stack

# --- Direct unit tests on the helper ---------------------------------------


def test_helper_returns_false_when_only_mention_is_negated():
    """The canonical fixture case: 'not a Python application'."""
    content = "this project is not a python application."
    assert _tech_has_non_negated_mention("python", content) is False


def test_helper_returns_true_when_at_least_one_mention_is_non_negated():
    """A README that disclaims one usage but affirms another keeps the tech."""
    content = "we are not a python application. however, the build scripts use python."
    # First match preceded by 'not a', second match has no negation in the window
    assert _tech_has_non_negated_mention("python", content) is True


def test_helper_returns_true_for_normal_mention():
    """Affirmative declaration: clearly part of the stack."""
    content = "built with python, fastapi, and chromadb."
    assert _tech_has_non_negated_mention("python", content) is True
    assert _tech_has_non_negated_mention("fastapi", content) is True


def test_helper_returns_false_when_keyword_absent():
    content = "this project uses only typescript."
    assert _tech_has_non_negated_mention("python", content) is False


# --- Negation tokens that must be recognised -------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        "this is not a python project",
        "this isn't a python project",
        "this isn't python",
        "we don't use python",
        "we doesn't use python",  # ungrammatical but common typo
        "no longer python",
        "instead of python",
        "rather than python",
        "without python",
        "never python",
        "wasn't python",
        "weren't python",
        "didn't use python",
    ],
)
def test_helper_recognises_common_negation_phrases(phrase: str):
    """All of these phrasings disclaim the tech and should be filtered."""
    assert _tech_has_non_negated_mention("python", phrase) is False, f"Negation phrase not recognised: {phrase!r}"


def test_helper_proximity_window_does_not_cross_far_negation():
    """A 'not' very far from the tech keyword (~100 chars) should NOT count
    as scoping over the tech — proves the proximity window is bounded."""
    # 'not' appears ~150 chars before 'python' — well outside the 40-char window
    content = (
        "this codebase is not focused on machine learning. "
        "we use a wide variety of tools across many sub-systems, "
        "and one of the languages we ship in production is python."
    )
    assert _tech_has_non_negated_mention("python", content) is True


def test_helper_does_not_match_partial_substring():
    """Word-boundary matching: 'jython' does not count as a 'python' mention."""
    assert _tech_has_non_negated_mention("python", "we use jython exclusively.") is False


def test_helper_handles_capitalisation():
    """Caller is responsible for lowercasing; the helper expects already-lower."""
    # If a caller forgets to lower, the helper still does word-bounded match,
    # but on the literal lowercase tech. So uppercase 'PYTHON' in content
    # wouldn't match — and that's the documented contract.
    # We just confirm the lowercase path works as expected.
    assert _tech_has_non_negated_mention("python", "python is great") is True


# --- Integration with extract_tech_stack -----------------------------------


def test_extract_drops_only_negated_python():
    """End-to-end: extract_tech_stack runs the negation filter as part of
    its normal flow. Only uses techs in the parser's TECH_KEYWORDS list."""
    content = "this is not a python application. it is built with docker and langchain."
    techs = extract_tech_stack(content)
    assert "python" not in techs
    assert "docker" in techs
    assert "langchain" in techs


def test_extract_keeps_python_when_genuinely_declared():
    """Only uses techs in the parser's TECH_KEYWORDS list (pytest is NOT;
    fastapi/docker/openai ARE)."""
    content = "this project is a python service. it uses fastapi and openai."
    techs = extract_tech_stack(content)
    assert "python" in techs
    assert "fastapi" in techs
    assert "openai" in techs


# --- Integration: the agent-skills-repo fixture --------------------------


def test_agent_skills_repo_fixture_excludes_python_from_readme():
    """The Phase 5 fixture that originally surfaced this bug: a README that
    declares the project is 'not a Python application' must NOT cause
    'python' to leak into the detected tech list.

    Note: this tests ``extract_tech_stack`` from ``readme_parser`` which
    only considers techs in its local ``TECH_KEYWORDS`` list (a subset).
    The broader fixture-level test in
    ``test_bug_regressions.py::test_bugs_md_python_not_leaked_from_negated_readme_mention``
    asserts the same property over the FULL enhanced-parser pipeline.
    """
    fx_readme = Path(__file__).parent / "fixtures" / "projects" / "agent-skills-repo" / "README.md"
    if not fx_readme.exists():
        pytest.skip(f"Fixture missing: {fx_readme}")
    content = fx_readme.read_text(encoding="utf-8")
    techs = extract_tech_stack(content)
    assert (
        "python" not in techs
    ), f"Negation-aware extractor failed on agent-skills-repo README — 'python' still present in {techs}."
    # Sanity: docker is in TECH_KEYWORDS and is genuinely declared in the
    # README, so it should come through.
    assert "docker" in techs
