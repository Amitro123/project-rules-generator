"""Characterization tests for the analyze() CLI command early-exit paths.

These tests lock down the four early-exit scenarios before any structural
refactor of analyze_cmd.py, so regressions are caught immediately.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.analyze_cmd import analyze
from prg_utils.exceptions import ProjectRulesGeneratorError, READMENotFoundError


# ---------------------------------------------------------------------------
# Scenario 1: --generate-index exits 0 after generating the index
# ---------------------------------------------------------------------------


def test_generate_index_flag_exits_0(tmp_path):
    """--generate-index generates skills/index.md then exits 0 immediately."""
    runner = CliRunner()

    mock_sm = MagicMock()
    mock_sm.generate_perfect_index.return_value = tmp_path / "skills" / "index.md"

    with patch("cli.analyze_cmd.SkillsManager", return_value=mock_sm):
        result = runner.invoke(analyze, [str(tmp_path), "--generate-index", "--no-commit"])

    assert result.exit_code == 0, result.output
    mock_sm.generate_perfect_index.assert_called_once()


def test_generate_index_flag_does_not_run_pipeline(tmp_path):
    """--generate-index must NOT invoke the generation pipeline."""
    runner = CliRunner()

    mock_sm = MagicMock()
    mock_sm.generate_perfect_index.return_value = tmp_path / "skills" / "index.md"

    with (
        patch("cli.analyze_cmd.SkillsManager", return_value=mock_sm),
        patch("cli.analyze_cmd.run_generation_pipeline") as mock_pipeline,
    ):
        runner.invoke(analyze, [str(tmp_path), "--generate-index", "--no-commit"])

    mock_pipeline.assert_not_called()


def test_generate_index_failure_exits_1(tmp_path):
    """If generate_perfect_index raises, exits 1 with an error message."""
    runner = CliRunner()

    mock_sm = MagicMock()
    mock_sm.generate_perfect_index.side_effect = RuntimeError("disk full")

    with patch("cli.analyze_cmd.SkillsManager", return_value=mock_sm):
        result = runner.invoke(analyze, [str(tmp_path), "--generate-index", "--no-commit"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Scenario 2: --incremental with no changes exits 0 before generation
# ---------------------------------------------------------------------------


def test_incremental_no_changes_exits_0(tmp_path):
    """When --incremental detects no changes, exits 0 without generating."""
    runner = CliRunner()

    mock_inc = MagicMock()
    mock_inc.detect_changes.return_value = set()  # nothing changed

    with (
        patch("generator.incremental_analyzer.IncrementalAnalyzer", return_value=mock_inc),
        patch("cli.analyze_cmd.run_generation_pipeline") as mock_pipeline,
    ):
        result = runner.invoke(analyze, [str(tmp_path), "--incremental", "--no-commit"])

    assert result.exit_code == 0, result.output
    assert "No changes detected" in result.output
    mock_pipeline.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 3: READMENotFoundError → click.echo + sys.exit(1)
# ---------------------------------------------------------------------------


def _patch_analyze_for_readme_error():
    """Return a context-manager stack that patches everything except resolve_readme."""
    from contextlib import ExitStack

    stack = ExitStack()

    mock_sm = MagicMock()
    mock_sm.generate_perfect_index.return_value = MagicMock()
    stack.enter_context(patch("cli.analyze_cmd.SkillsManager", return_value=mock_sm))
    stack.enter_context(patch("cli.analyze_cmd.setup_incremental", return_value=None))
    stack.enter_context(patch("cli.analyze_cmd.setup_logging_and_provider", return_value="groq"))
    stack.enter_context(patch("cli.analyze_cmd.load_config", return_value={}))
    stack.enter_context(patch("cli.analyze_cmd._handle_skill_management"))
    stack.enter_context(patch("cli.analyze_cmd.load_external_packs"))
    return stack


def test_readme_not_found_error_exits_1(tmp_path):
    """READMENotFoundError from resolve_readme exits 1 with error message."""
    runner = CliRunner()

    with _patch_analyze_for_readme_error():
        with patch("cli.analyze_cmd.resolve_readme", side_effect=READMENotFoundError("no readme")):
            result = runner.invoke(analyze, [str(tmp_path), "--no-commit"])

    assert result.exit_code == 1


def test_readme_not_found_error_prints_tip(tmp_path):
    """READMENotFoundError output includes the README tip."""
    runner = CliRunner()

    with _patch_analyze_for_readme_error():
        with patch("cli.analyze_cmd.resolve_readme", side_effect=READMENotFoundError("no readme")):
            result = runner.invoke(analyze, [str(tmp_path), "--no-commit"])

    combined = result.output + (result.stderr or "")
    assert "README" in combined or "readme" in combined.lower()


# ---------------------------------------------------------------------------
# Scenario 4: ProjectRulesGeneratorError → click.echo + sys.exit(1)
# ---------------------------------------------------------------------------


def test_project_rules_generator_error_exits_1(tmp_path):
    """ProjectRulesGeneratorError raised during pipeline exits 1."""
    runner = CliRunner()

    with _patch_analyze_for_readme_error():
        with (
            patch(
                "cli.analyze_cmd.resolve_readme",
                return_value=(None, {"tech_stack": [], "name": "x", "description": "", "features": []}, "x"),
            ),
            patch(
                "cli.analyze_cmd.run_generation_pipeline",
                side_effect=ProjectRulesGeneratorError("config broken"),
            ),
        ):
            result = runner.invoke(analyze, [str(tmp_path), "--no-commit"])

    assert result.exit_code == 1


def test_project_rules_generator_error_shows_message(tmp_path):
    """ProjectRulesGeneratorError message is shown to the user."""
    runner = CliRunner()

    with _patch_analyze_for_readme_error():
        with (
            patch(
                "cli.analyze_cmd.resolve_readme",
                return_value=(None, {"tech_stack": [], "name": "x", "description": "", "features": []}, "x"),
            ),
            patch(
                "cli.analyze_cmd.run_generation_pipeline",
                side_effect=ProjectRulesGeneratorError("config broken"),
            ),
        ):
            result = runner.invoke(analyze, [str(tmp_path), "--no-commit"])

    combined = result.output + (result.stderr or "")
    assert "config broken" in combined
