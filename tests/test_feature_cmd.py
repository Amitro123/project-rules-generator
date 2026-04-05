"""Tests for cli/feature_cmd.py — prg feature command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.feature_cmd import feature
from generator.ralph_engine import FeatureState, _load_tasks, next_feature_id

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project(tmp_path):
    """Minimal project directory."""
    (tmp_path / "README.md").write_text("# Demo Project\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Feature directory structure
# ---------------------------------------------------------------------------


def _invoke_feature(runner, project, task="Add loading states", extra_args=None):
    """Helper to invoke 'prg feature' with mocked TaskDecomposer and subprocess."""
    args = [task, "--project", str(project)] + (extra_args or [])
    with patch("generator.task_decomposer.TaskDecomposer") as MockDecomp, patch(
        "cli.feature_cmd._detect_provider", return_value="groq"
    ), patch("cli.feature_cmd._set_api_key"), patch("cli.feature_cmd.is_git_repo", return_value=True), patch(
        "subprocess.run"
    ) as mock_git:
        mock_git.return_value = MagicMock(returncode=0)
        MockDecomp.return_value.decompose.return_value = []
        MockDecomp.return_value.generate_plan_md.return_value = "# Plan\n"
        result = runner.invoke(feature, args)
    return result


def test_feature_creates_directory_structure(runner, project):
    """prg feature creates features/FEATURE-001 with expected files."""
    result = _invoke_feature(runner, project)

    feature_dir = project / "features" / "FEATURE-001"
    assert feature_dir.exists(), f"feature dir missing. Output:\n{result.output}"
    assert (feature_dir / "STATE.json").exists()
    assert (feature_dir / "PLAN.md").exists()
    assert (feature_dir / "TASKS.yaml").exists()
    assert (feature_dir / "CRITIQUES").exists()


def test_feature_auto_increments_id(runner, project):
    """Second call creates FEATURE-002."""
    # Pre-create FEATURE-001
    (project / "features" / "FEATURE-001").mkdir(parents=True)

    result = _invoke_feature(runner, project, task="New task")

    assert (project / "features" / "FEATURE-002").exists(), result.output


def test_feature_state_json_content(runner, project):
    """STATE.json has correct task, branch_name, and status."""
    _invoke_feature(runner, project, task="Add caching layer")

    state = FeatureState.load(project / "features" / "FEATURE-001" / "STATE.json")
    assert state.task == "Add caching layer"
    assert state.status == "planning_complete"
    assert "FEATURE-001" in state.branch_name
    assert "ralph" in state.branch_name


def test_feature_custom_max_iterations(runner, project):
    """--max-iterations is stored in STATE.json."""
    _invoke_feature(runner, project, task="Improve UI", extra_args=["--max-iterations", "5"])

    state = FeatureState.load(project / "features" / "FEATURE-001" / "STATE.json")
    assert state.max_iterations == 5


def test_feature_creates_git_branch(runner, project):
    """prg feature calls git checkout -b with the correct branch name."""
    args = ["Add loading states", "--project", str(project)]
    with patch("generator.task_decomposer.TaskDecomposer") as MockDecomp, patch(
        "cli.feature_cmd._detect_provider", return_value="groq"
    ), patch("cli.feature_cmd._set_api_key"), patch("cli.feature_cmd.is_git_repo", return_value=True), patch(
        "subprocess.run"
    ) as mock_git:
        mock_git.return_value = MagicMock(returncode=0)
        MockDecomp.return_value.decompose.return_value = []
        MockDecomp.return_value.generate_plan_md.return_value = "# Plan\n"
        runner.invoke(feature, args)

    # Verify git checkout -b was called
    calls = [str(c) for c in mock_git.call_args_list]
    assert any("checkout" in c and "-b" in c for c in calls), f"No branch creation call found. Calls: {calls}"


def test_feature_git_fail_does_not_crash(runner, project):
    """Git failure is handled gracefully — command still succeeds."""
    import subprocess

    args = ["Add loading states", "--project", str(project)]
    with patch("generator.task_decomposer.TaskDecomposer") as MockDecomp, patch(
        "cli.feature_cmd._detect_provider", return_value="groq"
    ), patch("cli.feature_cmd._set_api_key"), patch("cli.feature_cmd.is_git_repo", return_value=True), patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")
    ):
        MockDecomp.return_value.decompose.return_value = []
        MockDecomp.return_value.generate_plan_md.return_value = "# Plan\n"

        result = runner.invoke(feature, args)

    assert result.exit_code == 0


def test_feature_plan_generation_failure_handled(runner, project):
    """If TaskDecomposer raises, a placeholder PLAN.md is written and command succeeds."""
    args = ["Add loading states", "--project", str(project)]
    with patch("generator.task_decomposer.TaskDecomposer", side_effect=Exception("AI down")), patch(
        "cli.feature_cmd._detect_provider", return_value=None
    ), patch("cli.feature_cmd._set_api_key"), patch("cli.feature_cmd.is_git_repo", return_value=True), patch(
        "subprocess.run"
    ):
        result = runner.invoke(feature, args)

    plan = project / "features" / "FEATURE-001" / "PLAN.md"
    assert plan.exists()
    assert "Plan generation failed" in plan.read_text(encoding="utf-8")


def test_feature_tasks_yaml_populated(runner, project):
    """TASKS.yaml contains one entry per subtask."""
    from generator.task_decomposer import SubTask

    fake_subtasks = [
        SubTask(id=1, title="Step 1", goal="g1", files=[], changes=[], tests=[], dependencies=[], estimated_minutes=5),
        SubTask(id=2, title="Step 2", goal="g2", files=[], changes=[], tests=[], dependencies=[], estimated_minutes=5),
    ]
    args = ["Add loading states", "--project", str(project)]
    with patch("generator.task_decomposer.TaskDecomposer") as MockDecomp, patch(
        "cli.feature_cmd._detect_provider", return_value="groq"
    ), patch("cli.feature_cmd._set_api_key"), patch("cli.feature_cmd.is_git_repo", return_value=True), patch(
        "subprocess.run"
    ):
        MockDecomp.return_value.decompose.return_value = fake_subtasks
        MockDecomp.return_value.generate_plan_md.return_value = "# Plan\n"

        runner.invoke(feature, args)

    tasks = _load_tasks(project / "features" / "FEATURE-001" / "TASKS.yaml")
    assert len(tasks) == 2
    assert tasks[0]["title"] == "Step 1"
    assert tasks[0]["status"] == "pending"
