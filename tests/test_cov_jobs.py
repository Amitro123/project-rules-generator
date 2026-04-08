"""Coverage tests for cli/jobs.py.

Covers exec_task, status, next_task, query_tasks — happy paths,
no-manifest paths, JSON vs YAML dispatch, and error paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.jobs import exec_task, next_task, query_tasks, status

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manifest(tasks=None, task_description="Do work"):
    manifest = MagicMock()
    manifest.task_description = task_description
    manifest.tasks = tasks or []
    return manifest


def _make_entry(id=1, title="Task 1", file="task_001.md", status_val="pending", deps=None):
    entry = MagicMock()
    entry.id = id
    entry.title = title
    entry.file = file
    entry.status.value = status_val
    entry.dependencies = deps or []
    entry.estimated_minutes = 10
    return entry


def _make_executor(summary=None, next_task_obj=None):
    executor = MagicMock()
    executor.get_progress_summary.return_value = summary or {
        "done": 1,
        "total": 3,
        "percent": 33,
        "est_remaining_minutes": 20,
    }
    executor.get_next_task.return_value = next_task_obj
    return executor


# ---------------------------------------------------------------------------
# exec_task
# ---------------------------------------------------------------------------


def test_exec_task_no_tasks_yaml_exits_1(tmp_path):
    """exec_task exits 1 when no TASKS.yaml exists."""
    runner = CliRunner()
    result = runner.invoke(exec_task, ["tasks/task_001.md", "--project-path", str(tmp_path)])
    assert result.exit_code == 1
    assert "TASKS.yaml" in result.output or "No TASKS" in result.output


def test_exec_task_task_not_found_exits_1(tmp_path):
    """exec_task exits 1 when task file is not in TASKS.yaml."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    tasks_yaml = tasks_dir / "TASKS.yaml"
    tasks_yaml.write_text("task_description: test\ntasks: []\n")

    entry = _make_entry(file="task_001.md")
    manifest = _make_manifest(tasks=[entry])
    executor = _make_executor()

    runner = CliRunner()
    with (
        patch("generator.planning.task_creator.TaskManifest") as MockManifest,
        patch("generator.planning.task_executor.TaskExecutor", return_value=executor),
    ):
        MockManifest.from_yaml.return_value = manifest
        result = runner.invoke(exec_task, ["tasks/nonexistent.md", "--project-path", str(tmp_path)])

    assert result.exit_code == 1


def _exec_with_mocks(tmp_path, *extra_args):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    tasks_yaml = tasks_dir / "TASKS.yaml"
    tasks_yaml.write_text("task_description: test\ntasks: []\n")

    entry = _make_entry(file="task_001.md")
    manifest = _make_manifest(tasks=[entry])
    executor = _make_executor(next_task_obj=_make_entry(id=2, title="Next", file="task_002.md"))

    runner = CliRunner()
    with (
        patch("generator.planning.task_creator.TaskManifest") as MockManifest,
        patch("generator.planning.task_executor.TaskExecutor", return_value=executor),
    ):
        MockManifest.from_yaml.return_value = manifest
        result = runner.invoke(
            exec_task,
            ["tasks/task_001.md", "--project-path", str(tmp_path)] + list(extra_args),
        )
    return result, executor


def test_exec_task_start(tmp_path):
    """exec_task without flags starts the task."""
    result, executor = _exec_with_mocks(tmp_path)
    assert result.exit_code == 0
    executor.execute_single.assert_called_once_with(1)


def test_exec_task_complete(tmp_path):
    """exec_task --complete marks task done."""
    result, executor = _exec_with_mocks(tmp_path, "--complete")
    assert result.exit_code == 0
    executor.complete_task.assert_called_once_with(1)


def test_exec_task_skip(tmp_path):
    """exec_task --skip skips the task."""
    result, executor = _exec_with_mocks(tmp_path, "--skip")
    assert result.exit_code == 0
    executor.skip_task.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_status_no_manifest_no_plans(tmp_path):
    """status exits 0 and prints tip when nothing exists."""
    runner = CliRunner()
    with patch("generator.planning.PlanParser") as MockParser:
        MockParser.return_value.find_plans.return_value = []
        result = runner.invoke(status, ["--project-path", str(tmp_path)])
    assert result.exit_code == 0
    assert "No tasks" in result.output or "Tip" in result.output


def test_status_shows_yaml_progress(tmp_path):
    """status with TASKS.yaml shows progress."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    tasks_yaml = tasks_dir / "TASKS.yaml"
    tasks_yaml.write_text("task_description: test\ntasks: []\n")

    entry = _make_entry(status_val="done")
    manifest = _make_manifest(tasks=[entry])
    executor = _make_executor(next_task_obj=None)
    executor.get_progress_summary.return_value = {"done": 1, "total": 1, "percent": 100, "est_remaining_minutes": 0}

    runner = CliRunner()
    with (
        patch("generator.planning.task_creator.TaskManifest") as MockManifest,
        patch("generator.planning.task_executor.TaskExecutor", return_value=executor),
    ):
        MockManifest.from_yaml.return_value = manifest
        result = runner.invoke(status, ["--project-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "Task Progress" in result.output or "100" in result.output


def test_status_shows_json_progress(tmp_path):
    """status with TASKS.json shows JSON-based progress."""
    tasks_json = tmp_path / "TASKS.json"
    tasks_json.write_text(
        json.dumps(
            {
                "task": "Build feature",
                "tasks": [
                    {"id": 1, "title": "Step 1", "status": "done"},
                    {"id": 2, "title": "Step 2", "status": "pending"},
                ],
            }
        )
    )

    runner = CliRunner()
    result = runner.invoke(status, ["--project-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "Build feature" in result.output
    assert "1/2" in result.output or "50" in result.output


# ---------------------------------------------------------------------------
# next_task
# ---------------------------------------------------------------------------


def test_next_task_no_manifest(tmp_path):
    """next_task with no manifest prints no pending tasks."""
    runner = CliRunner()
    result = runner.invoke(next_task, ["--project-path", str(tmp_path)])
    assert result.exit_code == 0
    assert "No pending" in result.output


def test_next_task_json_path(tmp_path):
    """next_task finds next task from TASKS.json."""
    tasks_json = tmp_path / "TASKS.json"
    tasks_json.write_text(json.dumps({"task": "x", "tasks": [{"id": 1, "title": "First", "status": "pending"}]}))

    runner = CliRunner()
    result = runner.invoke(next_task, ["--project-path", str(tmp_path)])
    assert result.exit_code == 0
    assert "First" in result.output


def test_next_task_yaml_path(tmp_path):
    """next_task finds next task from TASKS.yaml via TaskExecutor."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    tasks_yaml = tasks_dir / "TASKS.yaml"
    tasks_yaml.write_text("task_description: test\ntasks: []\n")

    nxt = _make_entry(id=1, title="Do X", file="task_001.md")
    manifest = _make_manifest(tasks=[nxt])
    executor = _make_executor(next_task_obj=nxt)

    runner = CliRunner()
    with (
        patch("generator.planning.task_creator.TaskManifest") as MockManifest,
        patch("generator.planning.task_executor.TaskExecutor", return_value=executor),
    ):
        MockManifest.from_yaml.return_value = manifest
        result = runner.invoke(next_task, ["--project-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "Do X" in result.output


# ---------------------------------------------------------------------------
# query_tasks
# ---------------------------------------------------------------------------


def test_query_tasks_no_catalog(tmp_path):
    """query_tasks exits 0 with 'No tasks' when no manifest found."""
    runner = CliRunner()
    result = runner.invoke(query_tasks, ["something", "--project-path", str(tmp_path)])
    assert result.exit_code == 0
    assert "No tasks" in result.output


def test_query_tasks_json_match(tmp_path):
    """query_tasks finds best match from TASKS.json."""
    tasks_json = tmp_path / "TASKS.json"
    tasks_json.write_text(
        json.dumps(
            {
                "task": "x",
                "tasks": [
                    {"id": 1, "title": "fix login bug", "goal": "fix the login page bug", "status": "pending"},
                    {"id": 2, "title": "refactor cache", "goal": "", "status": "pending"},
                ],
            }
        )
    )

    runner = CliRunner()
    result = runner.invoke(query_tasks, ["login", "--project-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "login" in result.output.lower()
    assert "Best Match" in result.output


def test_query_tasks_no_match_message(tmp_path):
    """query_tasks shows 'No matching tasks' when nothing matches."""
    tasks_json = tmp_path / "TASKS.json"
    tasks_json.write_text(
        json.dumps({"task": "x", "tasks": [{"id": 1, "title": "write tests", "goal": "", "status": "pending"}]})
    )

    runner = CliRunner()
    result = runner.invoke(query_tasks, ["zxqzxqzxq", "--project-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "No matching" in result.output
