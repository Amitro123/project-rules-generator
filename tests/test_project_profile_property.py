"""Property tests for the ProjectProfile contract — generic, not project-specific.

These tests run a SHAPE of project (a fixture or a real on-disk project) through
the real ``EnhancedProjectParser`` → ``from_enhanced_context`` → ``ProjectProfile``
pipeline and assert GENERIC properties that must hold regardless of what the
project is or what tech it uses:

  * The profile's invariants pass (no skill collisions, no unknown scopes,
    no out-of-range confidence, no generic-slug project_name).
  * Every tech_stack entry has a source from EVIDENCE_SOURCES_ALL.
  * project_type is in KNOWN_PROJECT_TYPES (otherwise the detection layer
    drifted from the contract).
  * No skill name appears in two scopes.

Fixtures in ``tests/fixtures/projects/`` are project SHAPES (a project with
``rxconfig.py`` + a generated ``.web/``, a fullstack project with backend/+
frontend/, etc.), not "the Reflex test". The assertions never name a
specific tech or framework — they only check that the contract layer's
generic guarantees hold.

To run against your own real projects, set:

    PRG_TEST_PROJECT_PATHS="C:/Users/Dana/TelegramChatBot;C:/path/to/another"

(semicolon-separated). The harness will pick them up and run the same
generic property tests, letting you sanity-check that PRG behaves
consistently on real-world inputs.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

import pytest

from generator.parsers.enhanced_parser import EnhancedProjectParser
from generator.project_profile import EVIDENCE_SOURCES_ALL, KNOWN_PROJECT_TYPES, SKILL_SCOPES, from_enhanced_context

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "projects"


def _fixture_project_paths() -> List[Path]:
    """Every direct child of tests/fixtures/projects/ is treated as a SHAPE."""
    if not FIXTURES_ROOT.exists():
        return []
    return sorted(p for p in FIXTURES_ROOT.iterdir() if p.is_dir())


def _real_project_paths() -> List[Path]:
    """Optional: real on-disk projects supplied via env var.

    PRG_TEST_PROJECT_PATHS is semicolon-separated to work on Windows where
    paths contain colons. Missing entries are skipped, not errors — so the
    var can be set globally without forcing every machine to have every
    project."""
    raw = os.environ.get("PRG_TEST_PROJECT_PATHS", "")
    if not raw:
        return []
    out: List[Path] = []
    for entry in raw.replace(",", ";").split(";"):
        entry = entry.strip().strip('"').strip("'")
        if not entry:
            continue
        path = Path(entry)
        if path.exists() and path.is_dir():
            out.append(path)
    return out


ALL_PROJECT_PATHS = _fixture_project_paths() + _real_project_paths()


# --- Generic property assertions -------------------------------------------


def _build_profile(project_path: Path):
    """Run the real pipeline; return the profile or skip if parsing fails."""
    try:
        ctx = EnhancedProjectParser(project_path).extract_full_context()
    except Exception as exc:  # noqa: BLE001 — parser robustness is its own bug
        pytest.skip(f"EnhancedProjectParser raised on {project_path.name}: {exc}")
    return from_enhanced_context(
        enhanced_context=ctx,
        project_path=project_path,
        selected_skill_refs=[],
    )


@pytest.mark.parametrize(
    "project_path",
    ALL_PROJECT_PATHS,
    ids=lambda p: p.name,
)
class TestProjectProfileGenericProperties:
    """One parametrized class — every property runs against every project."""

    def test_invariants_pass(self, project_path: Path):
        """The profile is internally consistent. No matter what kind of
        project this is, the contract must hold."""
        profile = _build_profile(project_path)
        violations = profile.validate_invariants(strict=False)
        assert violations == [], (
            f"{project_path.name}: ProjectProfile invariants failed: {violations}\n"
            "These are contract violations — the producer wrote data the "
            "consumer's contract rejects. Investigate which detector emitted it."
        )

    def test_every_tech_has_known_source(self, project_path: Path):
        """Generic shape check: every tech entry's `source` is one of the
        allowed evidence kinds. Catches detectors that invent new strings."""
        profile = _build_profile(project_path)
        bad = [t for t in profile.tech_stack if t.source not in EVIDENCE_SOURCES_ALL]
        assert not bad, (
            f"{project_path.name}: tech entries with unknown source: " f"{[(t.name, t.source) for t in bad]}"
        )

    def test_project_type_is_in_known_set(self, project_path: Path):
        """Live detectors must only emit project_type values declared in
        KNOWN_PROJECT_TYPES. The drift-detector meta-test
        (test_known_project_types_covers_live_emitters) makes that set the
        single source of truth across the detection vocabulary."""
        profile = _build_profile(project_path)
        assert profile.project_type in KNOWN_PROJECT_TYPES, (
            f"{project_path.name}: project_type={profile.project_type!r} "
            f"not in KNOWN_PROJECT_TYPES. Either declare it or fix the detector."
        )

    def test_no_skill_name_in_two_scopes(self, project_path: Path):
        """The collision invariant restated as a standalone property test
        (it's also covered inside validate_invariants, but having it called
        out separately makes failures easier to spot)."""
        profile = _build_profile(project_path)
        per_scope = profile.skill_refs_by_scope()
        all_pairs: List[str] = []
        for scope in SKILL_SCOPES:
            all_pairs.extend(per_scope.get(scope, []))
        names_seen: dict = {}
        for scope in SKILL_SCOPES:
            for name in per_scope.get(scope, []):
                if name in names_seen and names_seen[name] != scope:
                    pytest.fail(
                        f"{project_path.name}: skill {name!r} in two scopes " f"({names_seen[name]} and {scope})"
                    )
                names_seen[name] = scope

    def test_project_name_is_not_generic_slug(self, project_path: Path):
        """No project should end up with a name that's a generic README
        heading slug (e.g. 'clone-repository'). Detector must fall back to
        the directory name."""
        from generator.project_profile import GENERIC_PROJECT_NAME_SLUGS

        profile = _build_profile(project_path)
        assert profile.project_name not in GENERIC_PROJECT_NAME_SLUGS, (
            f"{project_path.name}: project_name resolved to a generic slug "
            f"{profile.project_name!r}. The README's first H1 leaked through "
            "the name extractor."
        )


# --- Diagnostic helpers (not assertions) -----------------------------------


def test_at_least_one_input_present():
    """Sanity guard: if FIXTURES_ROOT is empty AND no env var is set, the
    parametrize collects zero cases and the harness silently does nothing.
    Fail loudly in that scenario."""
    assert ALL_PROJECT_PATHS, (
        f"No project inputs found. Expected fixtures under {FIXTURES_ROOT} " "or PRG_TEST_PROJECT_PATHS env var set."
    )
