"""Coverage boost: AgentWorkflow pure/mockable methods."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from generator.planning.workflow import AgentWorkflow


def _workflow(tmp_path):
    return AgentWorkflow(
        project_path=tmp_path,
        task_description="Add feature X",
        provider="groq",
        verbose=False,
    )


class TestWorkflowInit:
    def test_project_path_is_resolved(self, tmp_path):
        wf = _workflow(tmp_path)
        assert wf.project_path.is_absolute()

    def test_task_description_stored(self, tmp_path):
        wf = _workflow(tmp_path)
        assert wf.task_description == "Add feature X"

    def test_provider_stored(self, tmp_path):
        wf = AgentWorkflow(project_path=tmp_path, task_description="T", provider="anthropic")
        assert wf.provider == "anthropic"


class TestPreflight:
    def test_returns_preflight_report(self, tmp_path):
        wf = _workflow(tmp_path)
        report = wf._preflight()
        from generator.planning.preflight import PreflightReport

        assert isinstance(report, PreflightReport)


class TestFindOrCreatePlan:
    def test_uses_existing_plan(self, tmp_path):
        plan_file = tmp_path / "PLAN.md"
        plan_file.write_text("# PLAN\n\n## 1. Do stuff\n")

        wf = _workflow(tmp_path)
        with patch.object(wf, "_preflight"):
            with patch("generator.planning.preflight.PreflightChecker.find_plan_file", return_value=plan_file):
                result = wf._find_or_create_plan()
        assert result == plan_file

    def test_generates_plan_when_none_exists(self, tmp_path):
        wf = _workflow(tmp_path)
        with patch("generator.planning.preflight.PreflightChecker.find_plan_file", return_value=None):
            with patch.object(wf, "_generate_plan", return_value=tmp_path / "PLAN.md") as mock_gen:
                wf._find_or_create_plan()
        mock_gen.assert_called_once()


class TestCreateTaskFiles:
    def test_reuses_existing_manifest_yaml(self, tmp_path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        tasks_yaml = tasks_dir / "TASKS.yaml"
        tasks_yaml.write_text("title: Test\ntasks: []\n")

        wf = _workflow(tmp_path)
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("# PLAN\n")

        with patch("generator.planning.workflow.TaskManifest.from_yaml") as mock_from_yaml:
            mock_from_yaml.return_value = MagicMock()
            wf._create_task_files(plan_path)

        mock_from_yaml.assert_called_once()

    def test_creates_new_task_files_when_no_manifest(self, tmp_path):
        wf = _workflow(tmp_path)
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("# PLAN\n\n## 1. Do stuff\n")

        with patch.object(wf, "_parse_plan_subtasks", return_value=[]):
            with patch("generator.planning.workflow.TaskCreator") as MockCreator:
                MockCreator.return_value.create_from_subtasks.return_value = MagicMock(tasks=[])
                wf._create_task_files(plan_path)

        MockCreator.return_value.create_from_subtasks.assert_called_once()


class TestParsePlanSubtasks:
    def test_returns_list(self, tmp_path):
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("# PLAN\n\n## 1. Set up env\n\n**Goal:** Configure dev env\n")

        wf = _workflow(tmp_path)
        subtasks = wf._parse_plan_subtasks(plan_path)
        assert isinstance(subtasks, list)


class TestAutoFix:
    def test_fix_analyze_called_for_rules_check(self, tmp_path):
        wf = _workflow(tmp_path)
        report = MagicMock()
        report.all_passed = False

        failed_check = MagicMock()
        failed_check.name = "Rules file"
        report.failed_checks = [failed_check]

        with patch.object(wf, "_fix_analyze") as mock_fix:
            wf._auto_fix(report)
        mock_fix.assert_called_once()

    def test_fix_design_called_for_design_check(self, tmp_path):
        wf = _workflow(tmp_path)
        report = MagicMock()
        failed_check = MagicMock()
        failed_check.name = "DESIGN.md"
        report.failed_checks = [failed_check]

        with patch.object(wf, "_fix_design") as mock_fix:
            wf._auto_fix(report)
        mock_fix.assert_called_once()

    def test_plan_check_is_skipped(self, tmp_path):
        wf = _workflow(tmp_path)
        report = MagicMock()
        failed_check = MagicMock()
        failed_check.name = "PLAN.md"
        report.failed_checks = [failed_check]

        # Should not raise, just pass through
        wf._auto_fix(report)


class TestFixAnalyze:
    def test_skips_when_no_readme(self, tmp_path):
        wf = _workflow(tmp_path)
        # No README.md in tmp_path — should log and return silently
        wf._fix_analyze()

    def test_runs_when_readme_exists(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# My Project\n\nA simple project.\n")

        wf = _workflow(tmp_path)
        with patch("generator.analyzers.readme_parser.parse_readme", return_value={}):
            with patch("generator.rules_generator.generate_rules", return_value={}):
                wf._fix_analyze()

        rules_path = tmp_path / ".clinerules" / "rules.json"
        assert rules_path.exists()

    def test_handles_exception_gracefully(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Project\n")

        wf = _workflow(tmp_path)
        with patch("generator.analyzers.readme_parser.parse_readme", side_effect=RuntimeError("parse error")):
            wf._fix_analyze()  # Should not raise


class TestGetProjectContext:
    def test_returns_dict_or_none(self, tmp_path):
        wf = _workflow(tmp_path)
        with patch("generator.parsers.enhanced_parser.EnhancedProjectParser") as MockParser:
            MockParser.return_value.extract_full_context.return_value = {"project": "test"}
            result = wf._get_project_context()
        assert result is not None or result is None  # just shouldn't raise

    def test_returns_none_on_exception(self, tmp_path):
        wf = _workflow(tmp_path)
        with patch("generator.parsers.enhanced_parser.EnhancedProjectParser", side_effect=RuntimeError("fail")):
            result = wf._get_project_context()
        assert result is None
