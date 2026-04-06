"""Tests for cmd_review.py --tasks flag and _generate_tasks_from_review."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.cmd_review import _generate_tasks_from_review

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_report(action_plan=None, issues=None):
    """Build a minimal review report namespace."""
    return SimpleNamespace(
        verdict="Needs Revision",
        strengths=[],
        issues=issues or [],
        hallucinations=[],
        action_plan=action_plan or [],
    )


# ---------------------------------------------------------------------------
# _generate_tasks_from_review
# ---------------------------------------------------------------------------


class TestGenerateTasksFromReview:
    def test_creates_tasks_from_action_plan(self, tmp_path):
        """SubTask objects are built from report.action_plan items."""
        report = _make_report(action_plan=["Fix missing tests", "Remove dead code", "Add docstrings"])
        critique_path = tmp_path / "CRITIQUE.md"
        critique_path.write_text("# Critique")

        created_subtasks = []

        def fake_create(subtasks, plan_file, task_description, output_dir):
            created_subtasks.extend(subtasks)
            return MagicMock(entries=[])

        with patch("generator.planning.task_creator.TaskCreator") as MockCreator:
            MockCreator.return_value.create_from_subtasks.side_effect = fake_create
            _generate_tasks_from_review(report, critique_path, tmp_path, verbose=False)

        assert len(created_subtasks) == 3
        assert created_subtasks[0].title == "Fix missing tests"
        assert created_subtasks[1].id == 2
        assert created_subtasks[2].dependencies == [2]

    def test_falls_back_to_issues_when_no_action_plan(self, tmp_path):
        """When action_plan is empty, issues are used as fallback."""
        report = _make_report(action_plan=[], issues=["Broken import", "Missing type hint"])
        critique_path = tmp_path / "CRITIQUE.md"
        critique_path.write_text("# Critique")

        created_subtasks = []

        def fake_create(subtasks, plan_file, task_description, output_dir):
            created_subtasks.extend(subtasks)
            return MagicMock(entries=[])

        with patch("generator.planning.task_creator.TaskCreator") as MockCreator:
            MockCreator.return_value.create_from_subtasks.side_effect = fake_create
            _generate_tasks_from_review(report, critique_path, tmp_path, verbose=False)

        assert len(created_subtasks) == 2
        assert "Broken import" in created_subtasks[0].goal

    def test_skips_task_creation_when_nothing_to_act_on(self, tmp_path, capsys):
        """With no action_plan and no issues, no TaskCreator call is made."""
        report = _make_report(action_plan=[], issues=[])
        critique_path = tmp_path / "CRITIQUE.md"
        critique_path.write_text("# Critique")

        with patch("generator.planning.task_creator.TaskCreator") as MockCreator:
            _generate_tasks_from_review(report, critique_path, tmp_path, verbose=False)
            MockCreator.return_value.create_from_subtasks.assert_not_called()

    def test_long_action_item_is_truncated_in_title(self, tmp_path):
        """Title is capped at 80 chars; full text goes into goal."""
        long_item = "A" * 120
        report = _make_report(action_plan=[long_item])
        critique_path = tmp_path / "CRITIQUE.md"
        critique_path.write_text("# Critique")

        created_subtasks = []

        def fake_create(subtasks, **_):
            created_subtasks.extend(subtasks)
            return MagicMock(entries=[])

        with patch("generator.planning.task_creator.TaskCreator") as MockCreator:
            MockCreator.return_value.create_from_subtasks.side_effect = fake_create
            _generate_tasks_from_review(report, critique_path, tmp_path, verbose=False)

        assert len(created_subtasks[0].title) <= 80
        assert created_subtasks[0].goal == long_item

    def test_first_task_has_no_dependencies(self, tmp_path):
        """The first task must have an empty dependencies list."""
        report = _make_report(action_plan=["First action", "Second action"])
        critique_path = tmp_path / "CRITIQUE.md"
        critique_path.write_text("# Critique")

        created_subtasks = []

        def fake_create(subtasks, **_):
            created_subtasks.extend(subtasks)
            return MagicMock(entries=[])

        with patch("generator.planning.task_creator.TaskCreator") as MockCreator:
            MockCreator.return_value.create_from_subtasks.side_effect = fake_create
            _generate_tasks_from_review(report, critique_path, tmp_path, verbose=False)

        assert created_subtasks[0].dependencies == []
        assert created_subtasks[1].dependencies == [1]

    def test_creator_called_with_critique_filename(self, tmp_path):
        """plan_file argument must be the critique filename, not the original file."""
        report = _make_report(action_plan=["Do something"])
        critique_path = tmp_path / "CRITIQUE.md"
        critique_path.write_text("# Critique")

        with patch("generator.planning.task_creator.TaskCreator") as MockCreator:
            MockCreator.return_value.create_from_subtasks.return_value = MagicMock(entries=[])
            _generate_tasks_from_review(report, critique_path, tmp_path, verbose=False)

        call_kwargs = MockCreator.return_value.create_from_subtasks.call_args
        assert call_kwargs.kwargs.get("plan_file") == "CRITIQUE.md"

    def test_exception_in_creator_does_not_propagate(self, tmp_path):
        """Errors from TaskCreator must be caught and logged, not raised."""
        report = _make_report(action_plan=["Action item"])
        critique_path = tmp_path / "CRITIQUE.md"
        critique_path.write_text("# Critique")

        with patch("generator.planning.task_creator.TaskCreator") as MockCreator:
            MockCreator.return_value.create_from_subtasks.side_effect = RuntimeError("disk full")
            # Should not raise
            _generate_tasks_from_review(report, critique_path, tmp_path, verbose=False)
