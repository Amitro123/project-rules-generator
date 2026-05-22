"""Tests for the shadow-mode ProjectProfile validator.

Shadow mode is observational: it must NEVER raise and NEVER alter pipeline
output. These tests pin both properties — happy path, violations path, and
failure modes (bad context, write-only filesystem, missing dirs).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

import pytest

from cli.profile_shadow import INVARIANTS_REPORT_FILENAME, shadow_validate


def _good_context() -> Dict[str, Any]:
    """Realistic enhanced_context that should pass every invariant."""
    return {
        "metadata": {
            "project_name": "fastapi-service",
            "project_type": "python-api",
            "tech_stack": ["python", "fastapi", "pydantic", "pytest"],
            "languages": ["python"],
            "has_tests": True,
            "has_docker": False,
            "confidence": 0.9,
        },
        "structure": {"type": "fastapi-api", "confidence": 0.9},
        "dependencies": {
            "python": [
                {"name": "fastapi", "version": "0.100"},
                {"name": "pydantic", "version": "2.0"},
                {"name": "pytest", "version": "7.0"},
            ],
            "node": [],
        },
    }


# --- Happy path -------------------------------------------------------------


def test_shadow_clean_writes_empty_violations(tmp_path: Path):
    """A valid profile with matching disk state writes an empty violations list."""
    (tmp_path / "skills" / "project").mkdir(parents=True)
    (tmp_path / "skills" / "project" / "fastapi-endpoints").mkdir()
    (tmp_path / "skills" / "project" / "fastapi-endpoints" / "SKILL.md").write_text("# test", encoding="utf-8")

    violations = shadow_validate(
        enhanced_context=_good_context(),
        project_path=tmp_path,
        selected_skill_refs=[
            "builtin/code-review",
            "learned/fastapi/async-patterns",
            "project/fastapi-endpoints",
        ],
        output_dir=tmp_path,
    )

    assert violations == []
    report = json.loads((tmp_path / INVARIANTS_REPORT_FILENAME).read_text())
    assert report["violations"] == []
    assert report["profile"]["project_name"] == "fastapi-service"
    assert report["profile"]["project_type"] == "python-api"
    assert "fastapi" in {t["name"] for t in report["profile"]["tech_stack"]}


def test_shadow_records_tech_source_in_report(tmp_path: Path):
    """The report annotates each tech with its evidence source — useful for
    debugging why a tech got included."""
    (tmp_path / "skills" / "project").mkdir(parents=True)
    shadow_validate(
        enhanced_context=_good_context(),
        project_path=tmp_path,
        selected_skill_refs=set(),
        output_dir=tmp_path,
    )
    report = json.loads((tmp_path / INVARIANTS_REPORT_FILENAME).read_text())
    sources = {t["name"]: t["source"] for t in report["profile"]["tech_stack"]}
    assert sources["fastapi"] == "dependency"
    assert sources["pydantic"] == "dependency"
    # python is in the tech list but not in dep_aliases — falls back to readme
    assert "python" in sources


# --- Violations are surfaced but never raised ------------------------------


def test_shadow_disk_mismatch_logged_not_raised(tmp_path: Path, caplog):
    """The newbug.md case: skills on disk, none in selected_skills.
    Shadow mode must report it, log a warning, and return — never raise."""
    project_skills_dir = tmp_path / "skills" / "project"
    project_skills_dir.mkdir(parents=True)
    for name in ("a", "b", "c"):
        sd = project_skills_dir / name
        sd.mkdir()
        (sd / "SKILL.md").write_text("# test", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="cli.profile_shadow"):
        violations = shadow_validate(
            enhanced_context=_good_context(),
            project_path=tmp_path,
            selected_skill_refs=set(),
            output_dir=tmp_path,
        )

    assert any("skill_set_disk_mismatch" in v for v in violations)
    assert any("skill_set_disk_mismatch" in rec.message for rec in caplog.records)


def test_shadow_skill_collision_violation(tmp_path: Path):
    """nbug.md: pydantic-validation in both project/ and learned/.
    Shadow mode records the collision in the report."""
    (tmp_path / "skills" / "project").mkdir(parents=True)
    (tmp_path / "skills" / "project" / "pydantic-validation").mkdir()
    (tmp_path / "skills" / "project" / "pydantic-validation" / "SKILL.md").write_text("# test", encoding="utf-8")

    violations = shadow_validate(
        enhanced_context=_good_context(),
        project_path=tmp_path,
        selected_skill_refs=[
            "project/pydantic-validation",
            "learned/pydantic-validation",
        ],
        output_dir=tmp_path,
    )

    assert any("skill_name_collision" in v for v in violations)


def test_shadow_unknown_project_type_violation(tmp_path: Path):
    """Detector emitted a value not in KNOWN_PROJECT_TYPES — surface it."""
    (tmp_path / "skills" / "project").mkdir(parents=True)
    ctx = _good_context()
    ctx["metadata"]["project_type"] = "future-unknown-type"

    violations = shadow_validate(
        enhanced_context=ctx,
        project_path=tmp_path,
        selected_skill_refs=set(),
        output_dir=tmp_path,
    )
    assert any("unknown_project_type" in v for v in violations)


# --- Robustness: never raises, even on bad inputs --------------------------


def test_shadow_handles_none_context(tmp_path: Path):
    """None enhanced_context is tolerated — early exit with a marker violation."""
    violations = shadow_validate(
        enhanced_context=None,
        project_path=tmp_path,
        selected_skill_refs=set(),
        output_dir=tmp_path,
    )
    assert violations == ["enhanced_context_missing"]
    # Report still written so the user knows a run happened
    report_path = tmp_path / INVARIANTS_REPORT_FILENAME
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert report["violations"] == ["enhanced_context_missing"]
    assert "profile" not in report


def test_shadow_handles_minimal_context(tmp_path: Path):
    """A context that's missing every optional field still produces a profile,
    just one with mostly-default values. No raise."""
    violations = shadow_validate(
        enhanced_context={},
        project_path=tmp_path,
        selected_skill_refs=set(),
        output_dir=tmp_path,
    )
    # 'unknown' is in KNOWN_PROJECT_TYPES so it's clean, but the project name
    # falls back to tmp_path.name which won't be a generic slug. Should be clean.
    assert isinstance(violations, list)
    report = json.loads((tmp_path / INVARIANTS_REPORT_FILENAME).read_text())
    assert report["profile"]["project_type"] == "unknown"


def test_shadow_deduplicates_skill_refs(tmp_path: Path):
    """When the live pipeline passes a set with same-name learned skills under
    different category prefixes (nbug.md), shadow dedup collapses them in
    the report."""
    violations = shadow_validate(
        enhanced_context=_good_context(),
        project_path=tmp_path,
        selected_skill_refs=[
            "learned/fastapi/async-patterns",
            "learned/pytest/async-patterns",
            "learned/general/async-patterns",
        ],
        output_dir=tmp_path,
    )
    report = json.loads((tmp_path / INVARIANTS_REPORT_FILENAME).read_text())
    learned = report["profile"]["skills_by_scope"]["learned"]
    assert learned == ["async-patterns"]
    assert report["profile"]["skills_total"] == 1
    assert isinstance(violations, list)  # never raises


def test_shadow_overwrites_report_each_run(tmp_path: Path):
    """Second run should overwrite, not append. Idempotent."""
    shadow_validate(
        enhanced_context=_good_context(),
        project_path=tmp_path,
        selected_skill_refs=set(),
        output_dir=tmp_path,
    )
    first = (tmp_path / INVARIANTS_REPORT_FILENAME).read_text()

    # Change something and run again
    ctx2 = _good_context()
    ctx2["metadata"]["project_name"] = "different-project"
    shadow_validate(
        enhanced_context=ctx2,
        project_path=tmp_path,
        selected_skill_refs=set(),
        output_dir=tmp_path,
    )
    second = (tmp_path / INVARIANTS_REPORT_FILENAME).read_text()

    assert "fastapi-service" in first
    assert "different-project" in second
    assert "fastapi-service" not in second  # overwrite, not append


def test_shadow_creates_output_dir_if_missing(tmp_path: Path):
    """Shadow shouldn't fail if the output dir doesn't exist yet — it creates it."""
    missing_dir = tmp_path / "fresh" / "clinerules"
    assert not missing_dir.exists()

    violations = shadow_validate(
        enhanced_context=_good_context(),
        project_path=tmp_path,
        selected_skill_refs=set(),
        output_dir=missing_dir,
    )

    assert isinstance(violations, list)
    assert (missing_dir / INVARIANTS_REPORT_FILENAME).exists()


# --- The crucial property: shadow mode never raises -----------------------


@pytest.mark.parametrize(
    "ctx",
    [
        None,
        {},
        {"metadata": None},
        {"metadata": {"project_type": 12345}},  # wrong type
        {"metadata": {"tech_stack": "not-a-list"}},  # wrong shape
    ],
)
def test_shadow_never_raises_on_garbage_input(ctx, tmp_path):
    """No matter how malformed the input, shadow_validate must not raise.
    Pipeline correctness must not depend on it."""
    try:
        shadow_validate(
            enhanced_context=ctx,
            project_path=tmp_path,
            selected_skill_refs=[],
            output_dir=tmp_path,
        )
    except Exception as exc:  # noqa: BLE001 — test asserts no raise
        pytest.fail(f"shadow_validate raised on garbage input {ctx!r}: {exc}")
