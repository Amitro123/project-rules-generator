"""Coverage boost: cli/agent_plan_helpers.py (19% covered, 90 miss)."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cli.agent_plan_helpers import (
    _heuristic_files_for_task,
    handle_plan_from_readme,
    handle_plan_status,
    run_interactive_mode,
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


class TestHeuristicValueErrorFallback:
    def test_relative_to_failure_falls_back_to_name(self, tmp_path):
        """When relative_to() raises ValueError, the bare filename is used."""
        (tmp_path / "auth_handler.py").write_text("# auth")
        with patch.object(Path, "relative_to", side_effect=ValueError("not relative")):
            result = _heuristic_files_for_task("Fix auth handler bug", tmp_path)
        assert result == ["auth_handler.py"]


class TestHandlePlanStatus:
    def test_no_plans_reports_and_exits(self, tmp_path):
        with patch("generator.planning.PlanParser") as parser_cls:
            parser_cls.return_value.find_plans.return_value = []
            with pytest.raises(SystemExit) as exc:
                handle_plan_status(tmp_path)
        assert exc.value.code == 0

    def test_reports_each_plan_then_exits(self, tmp_path, capsys):
        with patch("generator.planning.PlanParser") as parser_cls:
            parser = parser_cls.return_value
            parser.find_plans.return_value = [tmp_path / "PLAN.md"]
            parser.parse_plan.return_value = MagicMock()
            parser.format_status_report.return_value = "STATUS: 3/5 done"
            with pytest.raises(SystemExit) as exc:
                handle_plan_status(tmp_path)
        assert exc.value.code == 0
        assert "STATUS: 3/5 done" in capsys.readouterr().out


class TestHandlePlanFromReadme:
    def _plan_obj(self, *, completed=False, fmt_capture=None):
        task = SimpleNamespace(description="Do X", subtasks=["a", "b"], completed=completed)
        phase = SimpleNamespace(name="Phase 1", tasks=[task])
        return SimpleNamespace(title="My Roadmap", phases=[phase], save=MagicMock())

    def test_generates_roadmap_and_tasks_manifest(self, tmp_path):
        plan_obj = self._plan_obj()
        with patch("generator.planning.ProjectPlanner") as planner_cls:
            planner_cls.return_value.generate_roadmap_from_readme.return_value = plan_obj
            with pytest.raises(SystemExit) as exc:
                handle_plan_from_readme(
                    from_readme=str(tmp_path / "README.md"),
                    project_path=tmp_path,
                    provider="groq",
                    api_key=None,
                    output="PROJECT-ROADMAP.md",
                    output_format="markdown",
                    verbose=False,
                    version="9.9",
                )
        assert exc.value.code == 0
        plan_obj.save.assert_called_once()
        tasks = json.loads((tmp_path / "TASKS.json").read_text())
        assert tasks["task"] == "My Roadmap"
        assert tasks["tasks"][0]["phase"] == "Phase 1"
        assert tasks["tasks"][0]["status"] == "pending"

    def test_verbose_mermaid_branch(self, tmp_path, capsys):
        plan_obj = self._plan_obj(completed=True)
        with patch("generator.planning.ProjectPlanner") as planner_cls:
            planner_cls.return_value.generate_roadmap_from_readme.return_value = plan_obj
            with pytest.raises(SystemExit):
                handle_plan_from_readme(
                    from_readme=str(tmp_path / "README.md"),
                    project_path=tmp_path,
                    provider="gemini",
                    api_key="k",
                    output=None,
                    output_format="mermaid",
                    verbose=True,
                    version="9.9",
                )
        out = capsys.readouterr().out
        assert "Mermaid diagram" in out
        # Completed task → status "done"
        tasks = json.loads((tmp_path / "TASKS.json").read_text())
        assert tasks["tasks"][0]["status"] == "done"


class TestRunInteractiveMode:
    def test_opens_files_with_editor_and_auto_execute(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDITOR", "myeditor")
        task = _subtask(files=["src/new_file.py"])
        proc = MagicMock()
        with patch("subprocess.Popen", return_value=proc) as popen:
            run_interactive_mode([task], tmp_path, auto_execute=True)
        # auto_execute created the missing file before opening it.
        assert (tmp_path / "src" / "new_file.py").exists()
        popen.assert_called_once()
        proc.wait.assert_called_once()

    def test_popen_error_is_reported(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("EDITOR", "myeditor")
        (tmp_path / "exists.py").write_text("x")
        task = _subtask(files=["exists.py"])
        with patch("subprocess.Popen", side_effect=OSError("no such editor")):
            run_interactive_mode([task], tmp_path, auto_execute=True)
        assert "Could not open exists.py" in capsys.readouterr().out

    def test_editor_discovered_via_which(self, tmp_path, monkeypatch):
        """With no EDITOR/VISUAL env, the first available candidate is used."""
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.delenv("VISUAL", raising=False)
        (tmp_path / "exists.py").write_text("x")
        task = _subtask(files=["exists.py"])
        proc = MagicMock()
        # "code" is the first candidate; report it as installed, others absent.
        with (
            patch("shutil.which", side_effect=lambda c: "/usr/bin/code" if c == "code" else None),
            patch("subprocess.Popen", return_value=proc) as popen,
        ):
            run_interactive_mode([task], tmp_path, auto_execute=True)
        popen.assert_called_once()
        assert popen.call_args.args[0][0] == "code"

    def test_no_editor_detected_branch(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.delenv("VISUAL", raising=False)
        task = _subtask(files=["a.py"])
        with patch("shutil.which", return_value=None):
            # No editor → falls into the "(no editor detected)" listing branch.
            run_interactive_mode([task], tmp_path, auto_execute=True)

    def test_prompt_eoferror_aborts(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.delenv("VISUAL", raising=False)
        task = _subtask(files=[])
        with patch("shutil.which", return_value=None), patch("builtins.input", side_effect=EOFError):
            # Non-auto-execute path prompts; EOFError aborts the loop cleanly.
            run_interactive_mode([task], tmp_path, auto_execute=False)
