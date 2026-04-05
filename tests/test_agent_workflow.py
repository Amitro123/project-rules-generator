"""Tests for agent workflow orchestrator and CLI integration."""

from unittest.mock import patch

from click.testing import CliRunner

from cli.cli import cli
from generator.planning.task_creator import TaskEntry, TaskManifest
from generator.planning.workflow import AgentWorkflow
from generator.task_decomposer import SubTask

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _setup_project(tmp_path, with_readme=True, with_plan=False, with_tasks=False):
    """Create a minimal project directory."""
    if with_readme:
        (tmp_path / "README.md").write_text("# Test Project\nFastAPI + Redis\n", encoding="utf-8")

    if with_plan:
        plan_content = """# PLAN

> **Goal:** Add cache

**Subtasks:** 2
**Estimated time:** 8 minutes

---

## 1. Research caching

**Goal:** Understand caching patterns
**Depends on:** none
**Estimated:** ~3 min

---

## 2. Implement cache

**Goal:** Add cache layer
**Depends on:** #1
**Estimated:** ~5 min

---
"""
        (tmp_path / "PLAN.md").write_text(plan_content, encoding="utf-8")

    if with_tasks:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        manifest = TaskManifest(
            plan_file="PLAN.md",
            task_description="Add cache",
            tasks=[
                TaskEntry(id=1, file="001-research.md", title="Research", estimated_minutes=3),
                TaskEntry(
                    id=2,
                    file="002-implement.md",
                    title="Implement",
                    dependencies=[1],
                    estimated_minutes=5,
                ),
            ],
        )
        manifest.save(tasks_dir / "TASKS.yaml")
        (tasks_dir / "001-research.md").write_text("# Task 1", encoding="utf-8")
        (tasks_dir / "002-implement.md").write_text("# Task 2", encoding="utf-8")

    return tmp_path


def _mock_subtasks():
    return [
        SubTask(
            id=1,
            title="Research caching",
            goal="Understand caching",
            estimated_minutes=3,
        ),
        SubTask(
            id=2,
            title="Implement cache",
            goal="Add cache",
            dependencies=[1],
            estimated_minutes=5,
        ),
    ]


# ---------------------------------------------------------------------------
# AgentWorkflow unit tests
# ---------------------------------------------------------------------------


class TestAgentWorkflow:

    def test_find_existing_plan(self, tmp_path):
        proj = _setup_project(tmp_path, with_plan=True)
        wf = AgentWorkflow(proj, "Add cache", verbose=False)
        plan_path = wf._find_or_create_plan()
        assert plan_path.name == "PLAN.md"

    def test_create_task_files_from_plan(self, tmp_path):
        proj = _setup_project(tmp_path, with_plan=True)
        wf = AgentWorkflow(proj, "Add cache", verbose=False)
        plan_path = proj / "PLAN.md"
        manifest = wf._create_task_files(plan_path)
        assert len(manifest.tasks) >= 1
        assert (proj / "tasks" / "TASKS.yaml").exists()

    def test_reuses_existing_tasks(self, tmp_path):
        proj = _setup_project(tmp_path, with_plan=True, with_tasks=True)
        wf = AgentWorkflow(proj, "Add cache", verbose=False)
        manifest = wf._create_task_files(proj / "PLAN.md")
        # Should load existing, not recreate
        assert len(manifest.tasks) == 2
        assert manifest.tasks[0].title == "Research"

    @patch("generator.planning.workflow.AgentWorkflow._generate_plan")
    def test_generates_plan_when_missing(self, mock_gen, tmp_path):
        proj = _setup_project(tmp_path)
        # No PLAN.md exists — should trigger _generate_plan
        plan_path = proj / "PLAN.md"
        mock_gen.return_value = plan_path

        wf = AgentWorkflow(proj, "Add cache", verbose=False)
        wf._find_or_create_plan()
        mock_gen.assert_called_once()

    def test_preflight_on_complete_project(self, tmp_path):
        proj = _setup_project(tmp_path, with_plan=True, with_tasks=True)
        # Add rules + skills + design
        (proj / ".clinerules").mkdir(exist_ok=True)
        (proj / ".clinerules" / "rules.json").write_text("{}", encoding="utf-8")
        skills_dir = proj / ".clinerules" / "skills" / "learned"
        skills_dir.mkdir(parents=True)
        for i in range(3):
            (skills_dir / f"s{i}.md").write_text(f"# S{i}", encoding="utf-8")
        (proj / "DESIGN.md").write_text("# Design", encoding="utf-8")

        wf = AgentWorkflow(proj, "Add cache", verbose=False)
        report = wf._preflight()
        assert report.all_passed


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestCLICommands:

    def test_status_no_tasks(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--project-path", str(tmp_path)])
        assert "No tasks or plans found" in result.output

    def test_status_with_tasks(self, tmp_path):
        _setup_project(tmp_path, with_tasks=True)
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--project-path", str(tmp_path)])
        assert result.exit_code == 0
        assert "Add cache" in result.output
        assert "0/2 done" in result.output

    def test_exec_no_manifest(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "exec",
                "tasks/001-x.md",
                "--project-path",
                str(tmp_path),
            ],
        )
        assert result.exit_code != 0
        assert "No TASKS.yaml" in result.output

    def test_exec_start_task(self, tmp_path):
        _setup_project(tmp_path, with_tasks=True)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "exec",
                "tasks/001-research.md",
                "--project-path",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert "started" in result.output

    def test_exec_complete_task(self, tmp_path):
        # First start a task
        _setup_project(tmp_path, with_tasks=True)
        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "exec",
                "tasks/001-research.md",
                "--project-path",
                str(tmp_path),
            ],
        )
        # Then complete it
        result = runner.invoke(
            cli,
            [
                "exec",
                "tasks/001-research.md",
                "--complete",
                "--project-path",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert "done" in result.output

    def test_exec_skip_task(self, tmp_path):
        _setup_project(tmp_path, with_tasks=True)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "exec",
                "tasks/001-research.md",
                "--skip",
                "--project-path",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert "skipped" in result.output

    def test_exec_blocked_task(self, tmp_path):
        _setup_project(tmp_path, with_tasks=True)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "exec",
                "tasks/002-implement.md",
                "--project-path",
                str(tmp_path),
            ],
        )
        assert result.exit_code != 0
        assert "blocked" in result.output

    def test_exec_unknown_file(self, tmp_path):
        _setup_project(tmp_path, with_tasks=True)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "exec",
                "tasks/999-nope.md",
                "--project-path",
                str(tmp_path),
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_status_after_completion(self, tmp_path):
        _setup_project(tmp_path, with_tasks=True)
        runner = CliRunner()
        # Start and complete task 1
        runner.invoke(cli, ["exec", "tasks/001-research.md", "--project-path", str(tmp_path)])
        runner.invoke(
            cli,
            [
                "exec",
                "tasks/001-research.md",
                "--complete",
                "--project-path",
                str(tmp_path),
            ],
        )
        # Check status
        result = runner.invoke(cli, ["status", "--project-path", str(tmp_path)])
        assert "1/2 done" in result.output

    def test_start_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["start", "--help"])
        assert result.exit_code == 0
        assert "Full agent workflow" in result.output

    def test_setup_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["setup", "--help"])
        assert result.exit_code == 0
        assert "Setup workflow" in result.output
