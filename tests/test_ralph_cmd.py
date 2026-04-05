"""Tests for cli/ralph_cmd.py — prg ralph subcommands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from click.testing import CliRunner

from cli.ralph_cmd import ralph_group
from generator.ralph_engine import FeatureState, _save_tasks

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


def _setup_feature(tmp_path: Path, feature_id: str = "FEATURE-001", **state_overrides: object) -> Path:
    """Create a minimal feature directory with STATE.json."""
    feature_dir = tmp_path / "features" / feature_id
    feature_dir.mkdir(parents=True)

    defaults: dict = dict(
        feature_id=feature_id,
        task="Add loading states",
        branch_name=f"ralph/{feature_id}-add-loading-states",
        status="planning_complete",
        iteration=0,
        tasks_total=2,
        tasks_complete=0,
        max_iterations=10,
    )
    defaults.update(state_overrides)
    state = FeatureState(**defaults)
    state.save(feature_dir / "STATE.json")
    return feature_dir


# ---------------------------------------------------------------------------
# prg ralph run
# ---------------------------------------------------------------------------


def test_ralph_run_invokes_engine(runner, tmp_path):
    """prg ralph run calls RalphEngine.run_loop."""
    _setup_feature(tmp_path)

    with patch("generator.ralph_engine.RalphEngine") as MockEngine, patch(
        "cli.ralph_cmd._detect_provider", return_value="groq"
    ), patch("cli.ralph_cmd._set_api_key"), patch("subprocess.run") as mock_git:
        mock_git.return_value = MagicMock(returncode=0)
        instance = MockEngine.return_value

        result = runner.invoke(ralph_group, ["run", "FEATURE-001", "--project", str(tmp_path)], catch_exceptions=False)

    MockEngine.assert_called_once()
    instance.run_loop.assert_called_once()


def test_ralph_run_missing_state_raises(runner, tmp_path):
    """prg ralph run fails with helpful message if STATE.json is absent."""
    (tmp_path / "features" / "FEATURE-001").mkdir(parents=True)
    # No STATE.json

    with patch("cli.ralph_cmd._detect_provider", return_value="groq"), patch("cli.ralph_cmd._set_api_key"), patch(
        "prg_utils.git_ops.is_git_repo", return_value=True
    ):
        result = runner.invoke(ralph_group, ["run", "FEATURE-001", "--project", str(tmp_path)])

    assert result.exit_code != 0
    assert "STATE.json" in result.output


def test_ralph_run_passes_max_iterations(runner, tmp_path):
    """--max-iterations is forwarded to run_loop."""
    _setup_feature(tmp_path)

    with patch("generator.ralph_engine.RalphEngine") as MockEngine, patch(
        "cli.ralph_cmd._detect_provider", return_value="groq"
    ), patch("cli.ralph_cmd._set_api_key"), patch("prg_utils.git_ops.is_git_repo", return_value=True), patch(
        "subprocess.run"
    ):
        runner.invoke(ralph_group, ["run", "FEATURE-001", "--project", str(tmp_path), "--max-iterations", "5"])

    MockEngine.return_value.run_loop.assert_called_with(max_iterations=5)


# ---------------------------------------------------------------------------
# prg ralph status
# ---------------------------------------------------------------------------


def test_ralph_status_prints_state(runner, tmp_path):
    """prg ralph status displays key STATE.json fields."""
    _setup_feature(tmp_path, iteration=3, tasks_complete=1, last_review_score=82)

    result = runner.invoke(ralph_group, ["status", "FEATURE-001", "--project", str(tmp_path)])

    assert result.exit_code == 0
    assert "FEATURE-001" in result.output


def test_ralph_status_missing_state(runner, tmp_path):
    """prg ralph status fails when STATE.json absent."""
    (tmp_path / "features" / "FEATURE-001").mkdir(parents=True)
    result = runner.invoke(ralph_group, ["status", "FEATURE-001", "--project", str(tmp_path)])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# prg ralph stop
# ---------------------------------------------------------------------------


def test_ralph_stop_updates_state(runner, tmp_path):
    """prg ralph stop sets status=stopped in STATE.json."""
    _setup_feature(tmp_path, status="running")

    # git_ops.get_current_branch is imported locally inside ralph_stop, patch at source
    with patch("prg_utils.git_ops.get_current_branch", return_value="ralph/FEATURE-001"), patch(
        "subprocess.run"
    ) as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0)

        result = runner.invoke(
            ralph_group,
            ["stop", "FEATURE-001", "--project", str(tmp_path), "--reason", "scope changed"],
        )

    assert result.exit_code == 0
    state = FeatureState.load(tmp_path / "features" / "FEATURE-001" / "STATE.json")
    assert state.status == "stopped"
    assert state.exit_condition == "scope changed"


def test_ralph_stop_default_reason(runner, tmp_path):
    """prg ralph stop uses 'user_requested' as default reason."""
    _setup_feature(tmp_path, status="running")

    with patch("prg_utils.git_ops.get_current_branch", return_value="ralph/FEATURE-001"), patch("subprocess.run"):
        result = runner.invoke(ralph_group, ["stop", "FEATURE-001", "--project", str(tmp_path)])

    state = FeatureState.load(tmp_path / "features" / "FEATURE-001" / "STATE.json")
    assert state.exit_condition == "user_requested"


def test_ralph_stop_graceful_on_git_error(runner, tmp_path):
    """prg ralph stop doesn't crash if git operations fail."""
    _setup_feature(tmp_path, status="running")

    with patch("prg_utils.git_ops.get_current_branch", side_effect=Exception("no git")):
        result = runner.invoke(ralph_group, ["stop", "FEATURE-001", "--project", str(tmp_path)])

    # Should have written state and exited cleanly
    assert result.exit_code == 0
    state = FeatureState.load(tmp_path / "features" / "FEATURE-001" / "STATE.json")
    assert state.status == "stopped"


# ---------------------------------------------------------------------------
# prg ralph resume
# ---------------------------------------------------------------------------


def test_ralph_resume_clears_stopped_status(runner, tmp_path):
    """prg ralph resume resets stopped state before running engine."""
    _setup_feature(tmp_path, status="stopped")

    with patch("generator.ralph_engine.RalphEngine") as MockEngine, patch(
        "cli.ralph_cmd._detect_provider", return_value="groq"
    ), patch("cli.ralph_cmd._set_api_key"), patch("prg_utils.git_ops.is_git_repo", return_value=True):
        MockEngine.return_value.run_loop = MagicMock()
        result = runner.invoke(ralph_group, ["resume", "FEATURE-001", "--project", str(tmp_path)])

    # The engine should have been called
    MockEngine.return_value.run_loop.assert_called_once()
    assert result.exit_code == 0


def test_ralph_resume_non_stopped_still_runs(runner, tmp_path):
    """prg ralph resume works even if status is not 'stopped'."""
    _setup_feature(tmp_path, status="running")

    with patch("generator.ralph_engine.RalphEngine") as MockEngine, patch(
        "cli.ralph_cmd._detect_provider", return_value="groq"
    ), patch("cli.ralph_cmd._set_api_key"), patch("prg_utils.git_ops.is_git_repo", return_value=True):
        MockEngine.return_value.run_loop = MagicMock()
        runner.invoke(ralph_group, ["resume", "FEATURE-001", "--project", str(tmp_path)])

    MockEngine.return_value.run_loop.assert_called_once()


# ---------------------------------------------------------------------------
# prg ralph approve
# ---------------------------------------------------------------------------


def test_ralph_approve_merges_branch(runner, tmp_path):
    """prg ralph approve calls git_ops.checkout + merge_branch and updates STATE.json."""
    _setup_feature(tmp_path, status="running", branch_name="ralph/FEATURE-001-add-loading-states")

    # git_ops is imported locally inside ralph_approve, patch at source module
    with patch("prg_utils.git_ops.checkout") as mock_checkout, patch(
        "prg_utils.git_ops.merge_branch"
    ) as mock_merge, patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0)

        result = runner.invoke(
            ralph_group,
            ["approve", "FEATURE-001", "--project", str(tmp_path)],
        )

    assert result.exit_code == 0, result.output
    mock_checkout.assert_called_once()
    mock_merge.assert_called_once()

    state = FeatureState.load(tmp_path / "features" / "FEATURE-001" / "STATE.json")
    assert state.status == "success"
    assert state.exit_condition == "human_approved"
    assert state.human_feedback == "approved"


def test_ralph_approve_graceful_on_git_error(runner, tmp_path):
    """prg ralph approve outputs an error message but doesn't crash if git fails."""
    _setup_feature(tmp_path, status="running")

    with patch("prg_utils.git_ops.checkout", side_effect=Exception("git failed")):
        result = runner.invoke(ralph_group, ["approve", "FEATURE-001", "--project", str(tmp_path)])

    # Should show the error in output but exit 0 (exception is caught and printed)
    assert "failed" in result.output.lower() or result.exit_code == 0
