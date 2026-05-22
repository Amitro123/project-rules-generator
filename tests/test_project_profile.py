"""Tests for the ProjectProfile contract.

This is Phase 1 of the systemic-bug refactor (see Plans/prg-systemic-bug-refactor
in the Obsidian vault). The tests lock the contract before any producer is
migrated, so later phases that move code into ProjectProfile can't silently
relax an invariant.

Each ``test_*`` either:
  - constructs a ProjectProfile manually and asserts an invariant fires, or
  - constructs one from a synthetic enhanced_context dict and asserts the
    adapter packaged the data correctly.

No subprocess, no LLM, no filesystem mutation. The disk-mismatch test uses
``tmp_path`` to build a tiny fake .clinerules tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.project_profile import (
    EVIDENCE_SOURCES_STRONG,
    GENERIC_PROJECT_NAME_SLUGS,
    InvariantViolation,
    ProjectProfile,
    SkillRef,
    TechEntry,
    from_enhanced_context,
)

# --- Helpers ----------------------------------------------------------------


def _make_profile(**overrides) -> ProjectProfile:
    """Build a valid-by-default ProjectProfile, override specific fields per test."""
    defaults = dict(
        project_name="my-project",
        project_path=Path("/tmp/my-project"),
        project_type="python-cli",
        tech_stack=(TechEntry(name="python", source="dependency"),),
        selected_skills=(SkillRef(scope="project", name="foo"),),
        languages=("python",),
        has_tests=True,
        has_docker=False,
        has_ci=False,
        confidence=0.9,
    )
    defaults.update(overrides)
    return ProjectProfile(**defaults)


# --- Construction / immutability -------------------------------------------


def test_profile_is_immutable():
    """frozen=True dataclass; can't accidentally mutate after construction."""
    profile = _make_profile()
    with pytest.raises((AttributeError, TypeError)):
        profile.project_name = "other"  # type: ignore[misc]


def test_tech_entry_strong_vs_weak():
    """is_strong() reflects EVIDENCE_SOURCES_STRONG membership."""
    assert TechEntry(name="fastapi", source="dependency").is_strong()
    assert TechEntry(name="docker", source="file_pattern").is_strong()
    assert not TechEntry(name="reflex", source="readme").is_strong()
    # Sanity: every source in STRONG passes the gate
    for src in EVIDENCE_SOURCES_STRONG:
        assert TechEntry(name="t", source=src).is_strong()


def test_skill_ref_path_format():
    """ref property always 'scope/name' — matches clinerules.yaml refs."""
    assert SkillRef(scope="project", name="foo").ref == "project/foo"
    assert SkillRef(scope="learned", name="bar").ref == "learned/bar"
    assert SkillRef(scope="builtin", name="code-review").ref == "builtin/code-review"


# --- Invariants -------------------------------------------------------------


def test_unknown_project_type_flagged():
    """Catches the case where a new detector emits a value not in KNOWN_PROJECT_TYPES."""
    profile = _make_profile(project_type="some-future-type")
    violations = profile.validate_invariants(strict=False)
    assert any("unknown_project_type" in v for v in violations)


def test_strict_mode_raises():
    """strict=True raises InvariantViolation instead of returning the list."""
    profile = _make_profile(project_type="never-heard-of-this")
    with pytest.raises(InvariantViolation) as exc:
        profile.validate_invariants(strict=True)
    assert "unknown_project_type" in str(exc.value)


def test_generic_project_name_rejected():
    """Bug7: name = 'clone-repository' came from a generic README H1."""
    for slug in ("clone-repository", "getting-started", "installation"):
        assert slug in GENERIC_PROJECT_NAME_SLUGS  # guard against constant drift
        profile = _make_profile(project_name=slug)
        violations = profile.validate_invariants()
        assert any(
            "generic_project_name" in v for v in violations
        ), f"Expected generic_project_name violation for {slug!r}"


def test_real_project_name_passes():
    """Sanity: a normal project name does not trip the generic-slug check."""
    profile = _make_profile(project_name="telegram-customer-support-agent")
    violations = profile.validate_invariants()
    assert not any("generic_project_name" in v for v in violations)


def test_duplicate_tech_flagged():
    """If two detectors record the same tech with different sources, that's a bug."""
    profile = _make_profile(
        tech_stack=(
            TechEntry(name="fastapi", source="dependency"),
            TechEntry(name="fastapi", source="readme"),
        )
    )
    violations = profile.validate_invariants()
    assert any("duplicate_tech" in v for v in violations)


def test_unknown_tech_source_flagged():
    """Source must be one of EVIDENCE_SOURCES_ALL."""
    profile = _make_profile(tech_stack=(TechEntry(name="custom", source="magic"),))
    violations = profile.validate_invariants()
    assert any("unknown_tech_source" in v for v in violations)


def test_skill_name_collision_across_scopes_flagged():
    """nbug.md: pydantic-validation appeared in BOTH project/ and learned/.

    This is the canonical case for the missing invariant — the three dedup
    passes scattered across analyze_pipeline.py and clinerules_generator.py
    let this slip through. The contract makes it impossible.
    """
    profile = _make_profile(
        selected_skills=(
            SkillRef(scope="project", name="pydantic-validation"),
            SkillRef(scope="learned", name="pydantic-validation"),
        )
    )
    violations = profile.validate_invariants()
    assert any("skill_name_collision" in v for v in violations)


def test_skill_name_repeats_within_same_scope_ok():
    """Same name + same scope (which can only happen if dedup elsewhere
    fails) is caught at dedup time, not here. The collision rule is about
    cross-scope conflicts, which is the actual user-facing bug."""
    # We can't construct duplicate SkillRefs in the same scope through the
    # adapter (dedup keyed by (scope, name) prevents it), but if a caller
    # builds one manually with two identical refs, the collision check
    # treats it as a no-op (seen_skill[name] == scope).
    profile = _make_profile(
        selected_skills=(
            SkillRef(scope="learned", name="api-client-patterns"),
            SkillRef(scope="learned", name="api-client-patterns"),
        )
    )
    violations = profile.validate_invariants()
    assert not any("skill_name_collision" in v for v in violations)


def test_unknown_skill_scope_flagged():
    profile = _make_profile(selected_skills=(SkillRef(scope="external", name="thing"),))
    violations = profile.validate_invariants()
    assert any("unknown_skill_scope" in v for v in violations)


def test_confidence_out_of_range_flagged():
    """Confidence values outside [0.0, 1.0] usually signal a detector bug."""
    too_high = _make_profile(confidence=1.5)
    too_low = _make_profile(confidence=-0.1)
    assert any("confidence_out_of_range" in v for v in too_high.validate_invariants())
    assert any("confidence_out_of_range" in v for v in too_low.validate_invariants())


def test_valid_profile_returns_no_violations():
    """A profile that satisfies every invariant returns an empty list."""
    profile = _make_profile()
    assert profile.validate_invariants() == []


# --- validate_against_disk (the newbug.md invariant) -----------------------


def test_disk_invariant_catches_missing_in_profile(tmp_path: Path):
    """newbug.md: 9 directories under .clinerules/skills/project/ but
    rules.md/clinerules.yaml report project: 0.

    The invariant compares what's on disk to what the profile claims. If
    they disagree, the writer is about to lie — fail loudly.
    """
    project_skills_dir = tmp_path / "skills" / "project"
    project_skills_dir.mkdir(parents=True)
    for name in ("docker-deployment", "fastapi-endpoints", "pydantic-validation"):
        skill_dir = project_skills_dir / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# test", encoding="utf-8")

    profile = _make_profile(selected_skills=())  # empty — like newbug.md "project: 0"

    violations = profile.validate_against_disk(tmp_path, strict=False)
    assert any("skill_set_disk_mismatch" in v for v in violations)
    # Specifically: the disk has 3, profile has 0 → 3 missing in profile.
    msg = " ".join(violations)
    assert "docker-deployment" in msg
    assert "fastapi-endpoints" in msg
    assert "pydantic-validation" in msg


def test_disk_invariant_catches_missing_on_disk(tmp_path: Path):
    """The opposite direction: profile lists a project skill that was
    never actually written to disk (silent stub fallback case from Bug8)."""
    (tmp_path / "skills" / "project").mkdir(parents=True)

    profile = _make_profile(selected_skills=(SkillRef(scope="project", name="claimed-but-missing"),))

    violations = profile.validate_against_disk(tmp_path, strict=False)
    assert any("skill_set_disk_mismatch" in v for v in violations)
    assert "claimed-but-missing" in " ".join(violations)


def test_disk_invariant_passes_when_aligned(tmp_path: Path):
    """When the profile's project skills exactly match the disk, no violation."""
    project_skills_dir = tmp_path / "skills" / "project"
    project_skills_dir.mkdir(parents=True)
    for name in ("alpha", "beta"):
        skill_dir = project_skills_dir / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# test", encoding="utf-8")

    profile = _make_profile(
        selected_skills=(
            SkillRef(scope="project", name="alpha"),
            SkillRef(scope="project", name="beta"),
        )
    )

    assert profile.validate_against_disk(tmp_path) == []


def test_disk_invariant_strict_raises(tmp_path: Path):
    (tmp_path / "skills" / "project").mkdir(parents=True)
    skill_dir = tmp_path / "skills" / "project" / "ghost"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# test", encoding="utf-8")
    profile = _make_profile(selected_skills=())

    with pytest.raises(InvariantViolation) as exc:
        profile.validate_against_disk(tmp_path, strict=True)
    assert exc.value.invariant == "skill_set_disk_mismatch"


# --- Adapter ---------------------------------------------------------------


def test_adapter_packages_basic_context(tmp_path: Path):
    """Smoke test: feed the adapter what enhanced_parser produces and check
    the profile comes out with sensible fields."""
    enhanced_context = {
        "metadata": {
            "project_name": "telegram-bot",
            "project_type": "agent",
            "tech_stack": ["python", "langgraph", "openai", "chromadb"],
            "languages": ["python"],
            "has_tests": True,
            "has_docker": False,
            "confidence": 0.85,
        },
        "structure": {"type": "ml-pipeline", "confidence": 0.6},
        "dependencies": {
            "python": [
                {"name": "langgraph", "version": "0.0.1"},
                {"name": "openai", "version": "1.0"},
                {"name": "chromadb", "version": "0.4"},
            ],
            "node": [],
        },
    }

    profile = from_enhanced_context(
        enhanced_context,
        project_path=tmp_path,
        selected_skill_refs=[
            "builtin/code-review",
            "learned/api-client-patterns",
            "project/chromadb-rag",
        ],
    )

    assert profile.project_name == "telegram-bot"
    assert profile.project_type == "agent"
    assert "langgraph" in profile.tech_names()
    assert "openai" in profile.tech_names()
    assert profile.skill_names(scope="project") == frozenset({"chromadb-rag"})
    assert profile.skill_names(scope="learned") == frozenset({"api-client-patterns"})
    assert profile.skill_names(scope="builtin") == frozenset({"code-review"})


def test_adapter_dedups_skill_refs(tmp_path: Path):
    """nbug.md case: pipeline can emit 'learned/fastapi/async-patterns' and
    'learned/pytest/async-patterns' — same terminal name, different category
    prefixes. Canonical SkillRef key is (scope, terminal_name); dedup MUST
    collapse them into one entry."""
    enhanced_context = {"metadata": {}, "structure": {}, "dependencies": {}}
    profile = from_enhanced_context(
        enhanced_context,
        project_path=tmp_path,
        selected_skill_refs=[
            "learned/fastapi/async-patterns",
            "learned/pytest/async-patterns",
            "learned/async-patterns",
        ],
    )
    # All three collapse to one SkillRef(scope='learned', name='async-patterns')
    learned = [s for s in profile.selected_skills if s.scope == "learned"]
    assert len(learned) == 1
    assert learned[0].name == "async-patterns"


def test_adapter_marks_dependency_source_generically(tmp_path: Path):
    """Generic source attribution: if a tech name appears in the parsed
    dependency names, it's tagged 'dependency'. Otherwise 'inferred'.

    No hardcoded tech→package map in the contract — that's the kind of
    project-specific knowledge that creates drift (and was already
    duplicated in enhanced_parser._extract_metadata). Real per-tech evidence
    moves upstream in Phase 2.
    """
    enhanced_context = {
        "metadata": {
            "tech_stack": ["alpha", "beta", "gamma"],
        },
        "structure": {},
        "dependencies": {
            "python": [{"name": "alpha", "version": "1.0"}],
            "node": [{"name": "beta", "version": "2.0"}],
        },
    }
    profile = from_enhanced_context(enhanced_context, project_path=tmp_path)
    sources = {entry.name: entry.source for entry in profile.tech_stack}
    assert sources["alpha"] == "dependency"  # in python deps
    assert sources["beta"] == "dependency"  # in node deps
    assert sources["gamma"] == "inferred"  # nowhere — generic fallback


def test_adapter_dependency_source_is_case_insensitive(tmp_path: Path):
    """Tech names normalize lowercase; deps may be capitalized. The contract
    has to handle both without project-specific aliasing."""
    enhanced_context = {
        "metadata": {"tech_stack": ["FastAPI", "REACT"]},
        "structure": {},
        "dependencies": {
            "python": [{"name": "FastAPI", "version": "0.100"}],
            "node": [{"name": "react", "version": "18.2"}],
        },
    }
    profile = from_enhanced_context(enhanced_context, project_path=tmp_path)
    sources = {entry.name: entry.source for entry in profile.tech_stack}
    assert sources["fastapi"] == "dependency"
    assert sources["react"] == "dependency"


def test_adapter_falls_back_to_dir_name_when_no_project_name(tmp_path: Path):
    """If metadata didn't set project_name, the profile uses the dir name —
    not an empty string and not a None."""
    enhanced_context = {"metadata": {}, "structure": {}, "dependencies": {}}
    profile = from_enhanced_context(enhanced_context, project_path=tmp_path)
    assert profile.project_name == tmp_path.name


# --- Drift detection -------------------------------------------------------


def test_known_project_types_covers_live_emitters():
    """KNOWN_PROJECT_TYPES must include every value the live detectors emit.

    Without this check, adding a new pattern to StructureAnalyzer (or a new
    label to TYPE_LABEL_MAP) would silently start firing `unknown_project_type`
    violations in shadow mode — exactly the drift this contract is supposed
    to prevent.

    When this test goes red: a new project_type was added somewhere in the
    detection layer without being declared as a known type. Either add it
    to KNOWN_PROJECT_TYPES, or (better) delete it from the detector if it
    was an accident.
    """
    from generator.analyzers.project_type_detector import TYPE_LABEL_MAP
    from generator.analyzers.structure_analyzer import StructureAnalyzer
    from generator.project_profile import KNOWN_PROJECT_TYPES

    live = set(StructureAnalyzer.PATTERNS.keys()) | set(TYPE_LABEL_MAP.values())
    missing = live - KNOWN_PROJECT_TYPES
    assert not missing, (
        f"KNOWN_PROJECT_TYPES is out of sync with live emitters. "
        f"Missing: {sorted(missing)}. Add these to generator/project_profile.py."
    )


def test_adapter_full_validate_clean(tmp_path: Path):
    """The output of the adapter on realistic input passes every invariant."""
    enhanced_context = {
        "metadata": {
            "project_name": "fastapi-service",
            "project_type": "python-api",
            "tech_stack": ["python", "fastapi", "pydantic", "pytest"],
            "languages": ["python"],
            "has_tests": True,
            "confidence": 0.92,
        },
        "structure": {"type": "fastapi-api", "confidence": 0.92},
        "dependencies": {
            "python": [
                {"name": "fastapi", "version": "0.100"},
                {"name": "pydantic", "version": "2.0"},
                {"name": "pytest", "version": "7.0"},
            ],
            "node": [],
        },
    }
    profile = from_enhanced_context(
        enhanced_context,
        project_path=tmp_path,
        selected_skill_refs=[
            "builtin/code-review",
            "learned/fastapi/async-patterns",
            "project/fastapi-endpoints",
        ],
    )
    assert profile.validate_invariants() == []
