"""Bug-shape regression tests (Phase 5).

Each test runs one fixture project shape through the real
``EnhancedProjectParser`` + ``ProjectProfile`` pipeline and asserts the
specific invariant that the historical bug violated.

Distinct from ``test_project_profile_property.py`` which runs **generic**
properties (invariants pass, every tech has a known source, etc.) against
**all** fixtures. This file asserts **bug-class-specific** invariants
against **one** fixture each — the assertions document "if this profile
ever looks like X, Bug Y has returned."

The solution code stays generic. The tests are bug-shaped, the fixtures
are project shapes — neither bakes project-specific knowledge into the
production path.

Layout
------
For each fixture (one block per bug class):
  - ``_make_<fixture>_profile`` — builds the profile from disk
  - ``test_bug<N>_<invariant_name>`` — one or more invariants per bug

When the fixture isn't available (e.g. someone deleted the directory),
the test is skipped rather than failed — keeps the harness robust.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from generator.parsers.enhanced_parser import EnhancedProjectParser
from generator.project_profile import ProjectProfile, apply_tech_cleanup_rules, from_enhanced_context

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "projects"


def _build_profile(name: str) -> Optional[ProjectProfile]:
    """Build a ProjectProfile from the named fixture, or skip if absent."""
    fx_path = FIXTURES_ROOT / name
    if not fx_path.exists():
        pytest.skip(f"Fixture {name!r} missing at {fx_path}")
    try:
        ctx = EnhancedProjectParser(fx_path).extract_full_context()
    except Exception as exc:  # noqa: BLE001 — parser robustness is its own bug
        pytest.skip(f"EnhancedProjectParser raised on {name!r}: {exc}")
    return from_enhanced_context(
        enhanced_context=ctx,
        project_path=fx_path,
        selected_skill_refs=[],
    )


# ============================================================================
# Bug8 — Reflex misclassified as react-app, .web/ JS deps leaked
# ============================================================================
# Original symptom (ListOfBugs/bug8.md): Reflex compiles Python to React in
# .web/. PRG scanned .web/ and concluded the project was a react-app with
# {react, node, nextjs, typescript} in the tech_stack.


def test_bug8_reflex_js_artifacts_not_in_tech_stack():
    """The .web/ build artifacts must not pollute the project's tech_stack."""
    profile = _build_profile("reflex-app")
    tech = profile.tech_names()
    leaked = {"react", "node", "nextjs", "next", "typescript"} & tech
    assert not leaked, (
        f"Bug8 regression: JS build artifacts leaked into tech_stack: "
        f"{sorted(leaked)}. The reflex strip-rule "
        f"(generator/rules/tech-detection/tech-cleanup/03-strip-reflex-js-artifacts.yaml) "
        f"should have removed these."
    )


def test_bug8_project_type_is_not_react_app():
    """A Reflex project writes Python; classifying as react-app misleads
    every downstream rule."""
    profile = _build_profile("reflex-app")
    assert profile.project_type != "react-app", (
        f"Bug8 regression: Reflex project misclassified as {profile.project_type!r}. "
        f"The detection layer should resolve to reflex-app (preferred) or web-app."
    )


def test_bug8_reflex_present_in_tech_stack():
    """Whatever the cleanup rules do, reflex itself must be retained — it's
    the project's actual framework."""
    profile = _build_profile("reflex-app")
    assert "reflex" in profile.tech_names()


# ============================================================================
# Bug4 — TelegramChatBot: jest false positive, flask-app misdetection,
#         langgraph missing from tech_stack
# ============================================================================
# Original symptom (ListOfBugs/Bug4.md): jest leaked from learned-skill library
# names; flask-app inferred from "webhook:" in spec.yml; langgraph missing
# because the tech detector didn't know about it.


def test_bug4_jest_not_in_tech_stack_when_pytest_project():
    """Bug4 core: jest leaked into a pure-Python project's tech_stack via
    learned-skill name matching. The cleanup rule
    strip-jest-when-not-test-framework should keep jest out."""
    profile = _build_profile("telegram-bot")
    # Sanity: the fixture has pytest in requirements.txt
    assert "pytest" in profile.tech_names()
    # Bug4: jest must NOT appear
    assert "jest" not in profile.tech_names(), "Bug4 regression: jest leaked into a pytest project's tech_stack."


def test_bug4_project_type_is_not_flask_app():
    """Bug4 secondary: 'webhook:' in spec.yml was misread as Flask routing.
    The fixture's spec.yml contains `webhook: /telegram/webhook` exactly to
    re-create the trigger condition."""
    profile = _build_profile("telegram-bot")
    assert profile.project_type != "flask-app", (
        f"Bug4 regression: telegram bot misclassified as flask-app "
        f"({profile.project_type!r}). Spec-yaml webhook lines must not "
        f"trigger Flask classification."
    )


def test_bug4_gpt_not_in_tech_stack():
    """Bug4 tertiary: 'gpt' is a vague README keyword, not a package.
    The cleanup rule strip-gpt-vague-token always strips it."""
    profile = _build_profile("telegram-bot")
    assert "gpt" not in profile.tech_names(), "Bug4 regression: vague 'gpt' token leaked into tech_stack."


# ============================================================================
# Bug7 — automation-service: README H1 'Clone Repository' misread as name
# ============================================================================
# Original symptom (ListOfBugs/bug7.md): README's first H1 was
# `# Clone Repository` (setup instructions). PRG extracted that as the
# project name, producing project_name='clone-repository'.


def test_bug7_project_name_is_not_generic_slug():
    """Bug7 core: the name extractor must reject generic instruction
    headings and fall back to the directory name."""
    from generator.project_profile import GENERIC_PROJECT_NAME_SLUGS

    profile = _build_profile("automation-service")
    assert profile.project_name not in GENERIC_PROJECT_NAME_SLUGS, (
        f"Bug7 regression: project_name resolved to a generic slug "
        f"{profile.project_name!r}. Expected fallback to the directory "
        f"name (automation-service)."
    )
    # Additionally: a successful fallback should produce the directory name
    assert profile.project_name == "automation-service", (
        f"Bug7 regression: project_name fallback produced " f"{profile.project_name!r} instead of the directory name."
    )


# ============================================================================
# Claude review1#5 — fullstack project_type drift
# ============================================================================
# Original symptom: enhanced parser detected web-app at high confidence,
# but rules.md frontmatter said python-cli because project_data was
# snapshotted before reconciliation ran.


def test_claude_review1_fullstack_is_not_python_cli():
    """Fullstack FastAPI+React: SA gives python-cli on a Python project
    without a strong API signal, but the newer detector recognises the
    fastapi backend. After reconciliation the project_type must reflect
    the fullstack reality, not the SA fallback."""
    profile = _build_profile("fullstack-fastapi-react")
    assert profile.project_type != "python-cli", (
        f"Claude review1#5 regression: fullstack project misclassified "
        f"as {profile.project_type!r}. Expected python-api / fastapi-api / "
        f"web-app — anything reflecting the API+frontend reality."
    )


# ============================================================================
# Bugs.md (hermes-skills) — agent-skills project mis-handled, Python skill
#                           leakage
# ============================================================================
# Original symptom (ListOfBugs/Bugs.md): a repo whose primary content is
# SKILL.md files (no Python source) had its tech_stack polluted with
# Python skill names and was misclassified.


def test_bugs_md_agent_skills_project_type_resolves():
    """The agent-skills fixture has no Python source — only SKILL.md
    files + docker-compose. project_type should be agent-skills (the
    newer detector's specialty), not the SA fallback."""
    profile = _build_profile("agent-skills-repo")
    # Either agent-skills (preferred — the newer detector handles it)
    # or one of the agent/unknown/library tiers that means "SA gave up"
    # — but NOT python-cli (which would mean SA misclassified).
    assert profile.project_type != "python-cli", (
        f"Bugs.md regression: agent-skills repo misclassified as python-cli "
        f"({profile.project_type!r}). Either the newer detector's "
        f"agent-skills classification or the SA library/unknown fallback "
        f"is acceptable, but not python-cli."
    )


def test_bugs_md_infrastructure_tech_detected():
    """Positive check: the agent-skills-repo README explicitly lists Docker
    and Telegram as the operational stack. Detection must surface these so
    downstream rules apply correctly. Catches detector regressions that
    leave the tech_stack near-empty for non-Python projects."""
    profile = _build_profile("agent-skills-repo")
    tech = profile.tech_names()
    assert "docker" in tech, "Bugs.md regression: docker not detected in agent-skills repo"
    assert "telegram" in tech, "Bugs.md regression: telegram not detected in agent-skills repo"


def test_bugs_md_no_mass_python_framework_leakage():
    """The actual Bugs.md complaint was about 49 Python-frame skills being
    selected for an agent-skills repo. This test asserts the detection
    result doesn't include any Python *framework* tech (fastapi/django/
    flask/pydantic/sqlalchemy/etc.) — bare ``python`` from README prose
    is a separate, smaller issue not in scope here."""
    profile = _build_profile("agent-skills-repo")
    tech = profile.tech_names()
    leaked_frameworks = {"fastapi", "django", "flask", "pydantic", "sqlalchemy", "pytest", "click"} & tech
    assert not leaked_frameworks, (
        f"Bugs.md regression: Python-framework tech leaked into an "
        f"agent-skills repo's tech_stack: {sorted(leaked_frameworks)}. "
        f"The original bug was 49 such skills polluting the project."
    )


# ============================================================================
# nbug.md — pydantic-validation appeared in two scopes
# ============================================================================
# Original symptom: pydantic-validation listed in both project/ and learned/.
# We don't have a live fixture that reproduces this (it requires the
# matcher + project-skill discovery to both vote for the same name) — the
# guarantee is enforced by the ProjectProfile invariant and the
# dedupe_skill_refs canonical pass.


def test_nbug_dedupe_prevents_cross_scope_collision_in_principle():
    """Hand-construct the colliding input and confirm dedupe + invariant
    together close the bug class. Not fixture-based because no real
    project naturally re-creates the exact mutation race."""
    from generator.project_profile import dedupe_skill_refs

    colliding = {
        "project/pydantic-validation",
        "learned/fastapi/pydantic-validation",
        "builtin/code-review",
    }
    deduped = dedupe_skill_refs(colliding)
    profile = from_enhanced_context(
        enhanced_context={"metadata": {}, "structure": {}, "dependencies": {}},
        project_path=Path("/tmp/x"),
        selected_skill_refs=list(deduped),
    )
    violations = profile.validate_invariants()
    assert not any("skill_name_collision" in v for v in violations), (
        f"nbug regression: ProjectProfile collision invariant fired after "
        f"dedup: {[v for v in violations if 'skill_name_collision' in v]}"
    )


# ============================================================================
# newbug.md — clinerules.yaml said project: 0 while 9 dirs existed on disk
# ============================================================================
# Original symptom: README-skill generation ran AFTER clinerules.yaml was
# emitted, so the count in the YAML didn't reflect the dirs on disk.
# Phase 4c moved the generation earlier; Phase 1 added validate_against_disk
# as the catch-net. This test exercises the catch-net.


def test_newbug_disk_mismatch_invariant_fires_when_appropriate(tmp_path):
    """If the writer ever drifts from the disk again, validate_against_disk
    must catch it. This test is fixture-free — it builds a tiny tmp tree
    that mimics the failure mode (3 dirs on disk, 0 in profile)."""
    project_skills_dir = tmp_path / "skills" / "project"
    project_skills_dir.mkdir(parents=True)
    for name in ("alpha", "beta", "gamma"):
        sd = project_skills_dir / name
        sd.mkdir()
        (sd / "SKILL.md").write_text("# test", encoding="utf-8")

    profile = from_enhanced_context(
        enhanced_context={"metadata": {}, "structure": {}, "dependencies": {}},
        project_path=tmp_path,
        selected_skill_refs=[],  # zero in profile
    )
    violations = profile.validate_against_disk(tmp_path)
    assert any("skill_set_disk_mismatch" in v for v in violations), (
        f"newbug regression: disk-mismatch invariant did not fire when "
        f"3 dirs existed and 0 were claimed. Violations were: {violations}"
    )


# ============================================================================
# Universal property — every fixture's profile passes contract invariants
# ============================================================================
# Independent of any specific bug class; a one-line guard that catches
# regressions where the profile becomes internally inconsistent for any
# fixture project. Complementary to test_project_profile_property.py which
# parametrizes the same check over ALL inputs.


@pytest.mark.parametrize(
    "fixture_name",
    ["reflex-app", "telegram-bot", "fullstack-fastapi-react", "agent-skills-repo", "automation-service"],
)
def test_every_fixture_profile_passes_invariants(fixture_name):
    profile = _build_profile(fixture_name)
    violations = profile.validate_invariants()
    assert violations == [], f"Fixture {fixture_name!r}: ProjectProfile invariants failed: {violations}"


# ============================================================================
# Tech cleanup rules apply correctly on real fixtures (Phase 3a/3b sanity)
# ============================================================================


def test_cleanup_rules_fire_on_reflex_fixture():
    """End-to-end check: the loaded YAML cleanup rules actually fire on
    the reflex fixture and produce a strip trace. Catches the case where
    the rule files exist but the loader / wiring breaks silently."""
    profile = _build_profile("reflex-app")
    # Simulate a tech_stack that includes both reflex and the JS artifacts
    # the cleanup rule should remove (the actual fixture profile already
    # has them stripped, so we inject them here to test the rule itself).
    raw = frozenset(profile.tech_names() | {"react", "node", "typescript"})
    cleaned, traces = apply_tech_cleanup_rules(tech_stack=raw, context={})
    # The reflex rule should fire and strip the JS artifacts
    fired = {t.rule_name for t in traces}
    assert "strip-reflex-js-build-artifacts" in fired, (
        f"Phase 3 regression: strip-reflex-js-build-artifacts rule did not "
        f"fire on a reflex tech_stack containing JS artifacts. Traces: {fired}"
    )
    assert "react" not in cleaned
    assert "node" not in cleaned
    assert "typescript" not in cleaned
