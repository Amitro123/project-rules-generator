"""Coverage boost: cli/agent_plan_helpers.py (19% covered, 90 miss)."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cli.agent_plan_helpers import (
    _heuristic_files_for_task,
    write_tasks_manifest,
)


def _subtask(id=1, title="Add feature", goal="Implement X", files=None, deps=None, mins=5):
    return SimpleNamespace(
        id=id,
        title=title,
        goal=goal,
        files=files or [],
        dependencies=deps or [],
        estimated_minutes=mins,
    )


class TestHeuristicFilesForTask:
    def test_returns_empty_when_project_path_none(self):
        result = _heuristic_files_for_task("Install parser", None)
        assert result == []

    def test_returns_empty_when_path_not_dir(self, tmp_path):
        nondir = tmp_path / "not_a_dir.txt"
        nondir.write_text("x")
        result = _heuristic_files_for_task("Install parser", nondir)
        assert result == []

    def test_finds_matching_python_file(self, tmp_path):
        (tmp_path / "skill_parser.py").write_text("class SkillParser: pass")
        result = _heuristic_files_for_task("Fix skill parser logic", tmp_path)
        assert any("skill_parser" in f or "parser" in f for f in result)

    def test_skips_test_files(self, tmp_path):
        (tmp_path / "test_parser.py").write_text("def test_parse(): pass")
        result = _heuristic_files_for_task("Fix parser logic", tmp_path)
        assert not any("test_parser" in f for f in result)

    def test_skips_pycache(self, tmp_path):
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "parser.py").write_text("# cached")
        result = _heuristic_files_for_task("Fix parser logic", tmp_path)
        assert not any("__pycache__" in f for f in result)

    def test_max_three_candidates(self, tmp_path):
        for i in range(5):
            (tmp_path / f"auth_{i}.py").write_text(f"# auth module {i}")
        result = _heuristic_files_for_task("Fix auth module handling", tmp_path)
        assert len(result) <= 3

    def test_short_keywords_ignored(self, tmp_path):
        (tmp_path / "ok.py").write_text("# ok")
        result = _heuristic_files_for_task("Fix it now", tmp_path)
        # Words "Fix", "it", "now" — "Fix" has 3 chars, "now" has 3 chars — all <= 3, no keywords
        assert result == []


class TestWriteTasksManifest:
    def test_creates_tasks_json(self, tmp_path):
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("# PLAN")
        subtasks = [_subtask()]

        result = write_tasks_manifest(plan_path, "Add feature", subtasks)
        assert result.name == "TASKS.json"
        assert result.exists()

    def test_json_has_correct_structure(self, tmp_path):
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("# PLAN")
        subtasks = [
            _subtask(id=1, title="Task A", goal="Goal A"),
            _subtask(id=2, title="Task B", goal="Goal B"),
        ]

        tasks_path = write_tasks_manifest(plan_path, "My Task", subtasks)
        data = json.loads(tasks_path.read_text())

        assert data["task"] == "My Task"
        assert data["plan_file"] == "PLAN.md"
        assert len(data["tasks"]) == 2
        assert data["tasks"][0]["title"] == "Task A"

    def test_enriches_empty_files_with_heuristics(self, tmp_path):
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("# PLAN")
        (tmp_path / "skill_parser.py").write_text("class Parser: pass")
        subtasks = [_subtask(title="Fix skill parser bug", files=[])]

        tasks_path = write_tasks_manifest(plan_path, "Bug fix", subtasks, project_path=tmp_path)
        data = json.loads(tasks_path.read_text())

        # Heuristic should have found skill_parser.py
        files = data["tasks"][0]["files"]
        assert any("parser" in f for f in files)

    def test_preserves_existing_files(self, tmp_path):
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("# PLAN")
        subtasks = [_subtask(files=["src/main.py", "src/utils.py"])]

        tasks_path = write_tasks_manifest(plan_path, "Feature", subtasks)
        data = json.loads(tasks_path.read_text())

        assert "src/main.py" in data["tasks"][0]["files"]

    def test_task_status_is_pending(self, tmp_path):
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("# PLAN")
        tasks_path = write_tasks_manifest(plan_path, "Feature", [_subtask()])
        data = json.loads(tasks_path.read_text())
        assert data["tasks"][0]["status"] == "pending"

    def test_task_estimated_minutes_included(self, tmp_path):
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("# PLAN")
        tasks_path = write_tasks_manifest(plan_path, "Feature", [_subtask(mins=10)])
        data = json.loads(tasks_path.read_text())
        assert data["tasks"][0]["estimated_minutes"] == 10

    def test_dependencies_included(self, tmp_path):
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("# PLAN")
        tasks_path = write_tasks_manifest(plan_path, "Feature", [_subtask(deps=[1, 2])])
        data = json.loads(tasks_path.read_text())
        assert data["tasks"][0]["dependencies"] == [1, 2]
