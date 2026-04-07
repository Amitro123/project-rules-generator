"""Characterization tests for run_generation_pipeline().

These tests lock down phase-boundary behavior so refactoring (PipelineConfig
dataclass, phase-function extraction) doesn't silently change semantics.
Each test patches only the parts it isn't testing.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skills_manager(tmp_path: Path) -> MagicMock:
    sm = MagicMock()
    sm.project_path = tmp_path
    sm.extract_project_triggers.return_value = {}
    sm.save_triggers_json.return_value = None
    sm.generate_from_readme.return_value = []
    sm.check_global_skill_reuse.return_value = {}
    return sm


def _call_pipeline(tmp_path: Path, **overrides):
    """Call run_generation_pipeline with safe defaults, allowing per-test overrides.

    Always patches generate_rules and EnhancedProjectParser at the pipeline module
    level so tests don't depend on filesystem content or LLM calls for phases they
    aren't testing. Tests that explicitly test these phases override the patches
    themselves.
    """
    from cli.analyze_pipeline import run_generation_pipeline

    output_dir = overrides.pop("output_dir", tmp_path / ".clinerules")
    output_dir.mkdir(parents=True, exist_ok=True)

    defaults = dict(
        project_path=tmp_path,
        project_name="test-project",
        project_data={
            "tech_stack": [],
            "name": "test-project",
            "description": "A test project.",
            "features": [],
        },
        readme_path=None,
        config={},
        provider="groq",
        skills_manager=_make_skills_manager(tmp_path),
        output_dir=output_dir,
        verbose=False,
        ai=False,
        auto_generate_skills=False,
        constitution=False,
        with_skills=False,
        merge=False,
        save_learned=False,
        export_json=False,
        export_yaml=False,
        inc_analyzer=None,
        strategy="auto",
    )
    defaults.update(overrides)
    defaults["output_dir"] = output_dir

    with (
        patch("cli.analyze_pipeline.generate_rules", return_value="# Rules\n") as _,
        patch("cli.analyze_pipeline.EnhancedProjectParser") as mock_parser,
    ):
        mock_parser.return_value.extract_full_context.return_value = {"tech_stack": [], "structure": {}}
        return run_generation_pipeline(**defaults), output_dir


# ---------------------------------------------------------------------------
# Phase 3 (Rules) — incremental skip
# ---------------------------------------------------------------------------


def test_incremental_rules_skipped_uses_cached_rules_md(tmp_path):
    """When inc_analyzer says _run_rules=False and rules.md exists,
    the existing rules.md content is used rather than calling generate_rules."""
    output_dir = tmp_path / ".clinerules"
    output_dir.mkdir(parents=True, exist_ok=True)
    cached_content = "# Cached rules\n- rule A\n"
    (output_dir / "rules.md").write_text(cached_content, encoding="utf-8")

    inc = MagicMock()
    inc.phases_to_run.return_value = (False, False, False, False)  # all skipped
    inc.detect_changes.return_value = set()

    with patch("generator.rules_generator.generate_rules") as mock_gen_rules:
        _, out_dir = _call_pipeline(tmp_path, output_dir=output_dir, inc_analyzer=inc)

    mock_gen_rules.assert_not_called()
    written = (out_dir / "rules.md").read_text(encoding="utf-8")
    assert "Cached rules" in written


def test_incremental_rules_skipped_no_cache_falls_back_to_generate(tmp_path):
    """When inc_analyzer says _run_rules=False but no rules.md exists,
    generate_rules is still called as fallback.

    Note: _call_pipeline already patches generate_rules; we capture the mock
    via the return value to verify it was called.
    """
    output_dir = tmp_path / ".clinerules"
    output_dir.mkdir(parents=True, exist_ok=True)

    inc = MagicMock()
    inc.phases_to_run.return_value = (False, False, False, False)
    inc.detect_changes.return_value = set()

    # Patch BEFORE calling _call_pipeline so we can inspect the mock
    with patch("cli.analyze_pipeline.generate_rules", return_value="# Generated fallback\n") as mock_gen:
        # _call_pipeline also patches generate_rules, but since we hold the outer
        # patch active, ours takes precedence and the inner one re-uses the same attr.
        from cli.analyze_pipeline import run_generation_pipeline

        output_dir2 = tmp_path / ".clinerules"
        from generator.parsers.enhanced_parser import EnhancedProjectParser

        with patch("cli.analyze_pipeline.EnhancedProjectParser") as mock_ep:
            mock_ep.return_value.extract_full_context.return_value = {}
            run_generation_pipeline(
                project_path=tmp_path,
                project_name="test-project",
                project_data={"tech_stack": [], "name": "test-project", "description": "A.", "features": []},
                readme_path=None,
                config={},
                provider="groq",
                skills_manager=_make_skills_manager(tmp_path),
                output_dir=output_dir2,
                verbose=False,
                ai=False,
                auto_generate_skills=False,
                constitution=False,
                with_skills=False,
                merge=False,
                save_learned=False,
                export_json=False,
                export_yaml=False,
                inc_analyzer=inc,
                strategy="auto",
            )

    mock_gen.assert_called_once()


# ---------------------------------------------------------------------------
# Phase 2 (Constitution) — incremental skip
# ---------------------------------------------------------------------------


def test_constitution_skipped_when_run_constitution_false(tmp_path):
    """When inc_analyzer says _run_constitution=False, constitution.md is NOT written."""
    inc = MagicMock()
    inc.phases_to_run.return_value = (True, True, False, True)  # constitution skipped
    inc.detect_changes.return_value = {"source"}

    with patch("cli.analyze_pipeline.generate_constitution") as mock_gen_const:
        _, output_dir = _call_pipeline(tmp_path, inc_analyzer=inc, constitution=True)

    mock_gen_const.assert_not_called()
    assert not (output_dir / "constitution.md").exists()


def test_constitution_written_when_run_constitution_true(tmp_path):
    """When constitution=True and inc_analyzer says _run_constitution=True,
    constitution.md is written."""
    inc = MagicMock()
    inc.phases_to_run.return_value = (True, True, True, True)
    inc.detect_changes.return_value = {"readme"}

    with patch("cli.analyze_pipeline.generate_constitution", return_value="# Constitution\n") as mock_const:
        # _call_pipeline already patches EnhancedProjectParser with a fake context
        _, output_dir = _call_pipeline(tmp_path, inc_analyzer=inc, constitution=True)

    mock_const.assert_called_once()
    assert (output_dir / "constitution.md").exists()


# ---------------------------------------------------------------------------
# Phase 4 (Skills auto-gen) — incremental skip
# ---------------------------------------------------------------------------


def test_auto_generate_skills_skipped_when_run_skills_gen_false(tmp_path):
    """When inc_analyzer says _run_skills_gen=False, _auto_generate_skills is not called."""
    inc = MagicMock()
    inc.phases_to_run.return_value = (False, True, False, False)  # skills skipped
    inc.detect_changes.return_value = set()

    with patch("cli.analyze_pipeline._auto_generate_skills") as mock_auto:
        _call_pipeline(tmp_path, inc_analyzer=inc, auto_generate_skills=True, ai=True)

    mock_auto.assert_not_called()


# ---------------------------------------------------------------------------
# Phase 6 (Write rules.md) — incremental merge
# ---------------------------------------------------------------------------


def test_incremental_merge_called_when_rules_md_exists(tmp_path):
    """When inc_analyzer is set and rules.md already exists, IncrementalAnalyzer.merge_rules
    is called to merge rather than replace."""
    output_dir = tmp_path / ".clinerules"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rules.md").write_text("# Old rules\n", encoding="utf-8")

    inc = MagicMock()
    inc.phases_to_run.return_value = (True, True, False, False)
    inc.detect_changes.return_value = {"deps"}

    with patch(
        "cli.analyze_pipeline.IncrementalAnalyzer.merge_rules", return_value="# Merged rules\n"
    ) as mock_merge:
        _call_pipeline(tmp_path, output_dir=output_dir, inc_analyzer=inc)

    mock_merge.assert_called_once()


# ---------------------------------------------------------------------------
# Output contract — rules.md + rules.json always in returned list
# ---------------------------------------------------------------------------


def test_pipeline_always_returns_rules_md_and_rules_json(tmp_path):
    """run_generation_pipeline always includes rules.md and rules.json in the
    returned file list, regardless of flags."""
    generated, output_dir = _call_pipeline(tmp_path)
    names = [Path(f).name for f in generated]
    assert "rules.md" in names
    assert "rules.json" in names
