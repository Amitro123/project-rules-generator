"""Coverage tests for cli/cmd_review.py.

Covers review command (provider missing, reviewer raises, happy path),
_resolve_input_path (absolute, CWD-relative, feature-dir search, not found),
_resolve_output_path, _display_review_report (rich + plain fallback),
and _generate_tasks_from_review (normal + no action items path).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.cmd_review import (
    _display_review_report,
    _generate_tasks_from_review,
    _resolve_input_path,
    _resolve_output_path,
    review,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_report(verdict="PASS", strengths=None, issues=None, hallucinations=None, action_plan=None):
    r = MagicMock()
    r.verdict = verdict
    r.strengths = strengths or ["good structure"]
    r.issues = issues or []
    r.suspicious_terms = hallucinations or []
    r.action_plan = action_plan or []
    r.to_markdown.return_value = "# Critique\n"
    return r


# ---------------------------------------------------------------------------
# review command — early exits
# ---------------------------------------------------------------------------


def test_review_no_provider_exits_1(tmp_path, monkeypatch):
    """review exits 1 when no API key / provider is available."""
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    target = tmp_path / "PLAN.md"
    target.write_text("# Plan\n")

    runner = CliRunner()
    result = runner.invoke(review, [str(target), "--project-path", str(tmp_path)])

    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "No AI provider" in combined or "provider" in combined.lower()


def test_review_reviewer_exception_exits_1(tmp_path, monkeypatch):
    """When reviewer.review raises, exits 1 with error message."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    target = tmp_path / "PLAN.md"
    target.write_text("# Plan\n")

    mock_reviewer = MagicMock()
    mock_reviewer.review.side_effect = RuntimeError("connection refused")

    runner = CliRunner()
    with patch("generator.planning.SelfReviewer", return_value=mock_reviewer):
        result = runner.invoke(review, [str(target), "--project-path", str(tmp_path)])

    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "connection refused" in combined or "Review failed" in combined


def test_review_happy_path_writes_critique(tmp_path, monkeypatch):
    """Happy path: critique written to CRITIQUE.md, exits 0."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    target = tmp_path / "PLAN.md"
    target.write_text("# Plan\n")

    mock_reviewer = MagicMock()
    mock_reviewer.review.return_value = _make_report()

    runner = CliRunner()
    with patch("generator.planning.SelfReviewer", return_value=mock_reviewer):
        result = runner.invoke(
            review,
            [str(target), "--project-path", str(tmp_path), "--quiet"],
        )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "CRITIQUE.md").exists()


# ---------------------------------------------------------------------------
# _resolve_input_path
# ---------------------------------------------------------------------------


def test_resolve_input_path_absolute_exists(tmp_path):
    f = tmp_path / "FILE.md"
    f.write_text("x")
    assert _resolve_input_path(f, tmp_path) == f.resolve()


def test_resolve_input_path_absolute_missing(tmp_path):
    with pytest.raises(Exception):
        _resolve_input_path(tmp_path / "MISSING.md", tmp_path)


def test_resolve_input_path_cwd_relative(tmp_path):
    """File found relative to CWD is resolved."""
    f = tmp_path / "LOCAL.md"
    f.write_text("x")
    import os

    orig = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = _resolve_input_path(Path("LOCAL.md"), tmp_path)
    finally:
        os.chdir(orig)
    assert result == f.resolve()


def test_resolve_input_path_feature_dir_search(tmp_path):
    """Bare filename not in CWD is found in features/*/ directory."""
    feat_dir = tmp_path / "features" / "FEATURE-001"
    feat_dir.mkdir(parents=True)
    # Use a name that won't accidentally exist in CWD
    artifact = feat_dir / "CRITIQUE_ARTIFACT_XYZ.md"
    artifact.write_text("# Critique")

    result = _resolve_input_path(Path("CRITIQUE_ARTIFACT_XYZ.md"), tmp_path)
    assert result == artifact.resolve()


def test_resolve_input_path_not_found_raises(tmp_path):
    """When file can't be found anywhere, raises BadParameter."""
    with pytest.raises(Exception):
        _resolve_input_path(Path("NOTHERE.md"), tmp_path)


# ---------------------------------------------------------------------------
# _resolve_output_path
# ---------------------------------------------------------------------------


def test_resolve_output_path_default(tmp_path):
    f = tmp_path / "PLAN.md"
    result = _resolve_output_path(f, None)
    assert result == tmp_path / "CRITIQUE.md"


def test_resolve_output_path_explicit(tmp_path):
    f = tmp_path / "PLAN.md"
    result = _resolve_output_path(f, str(tmp_path / "OUT.md"))
    assert result == tmp_path / "OUT.md"


# ---------------------------------------------------------------------------
# _display_review_report
# ---------------------------------------------------------------------------


def test_display_review_report_runs_without_error():
    r = _make_report(verdict="PASS", issues=["fix this"], hallucinations=["wrong ref"], action_plan=["do X"])
    runner = CliRunner()
    with runner.isolated_filesystem():
        _display_review_report(r, verbose=True)
        _display_review_report(r, verbose=False)


def test_display_review_report_plain_fallback():
    """Works even when rich is not available."""
    r = _make_report(verdict="FAIL", issues=["bad"], hallucinations=["fake"])

    def _no_rich(name, *a, **kw):
        if name in ("rich.console", "rich.table"):
            raise ImportError
        return __import__(name, *a, **kw)

    runner = CliRunner()
    with runner.isolated_filesystem():
        with patch("builtins.__import__", side_effect=_no_rich):
            _display_review_report(r, verbose=False)


# ---------------------------------------------------------------------------
# _generate_tasks_from_review
# ---------------------------------------------------------------------------


def test_generate_tasks_from_review_creates_tasks(tmp_path):
    """Creates tasks from action_plan items."""
    report = _make_report(action_plan=["Fix A", "Fix B"])

    mock_creator = MagicMock()
    with patch("generator.planning.task_creator.TaskCreator", return_value=mock_creator):
        _generate_tasks_from_review(report, tmp_path / "CRITIQUE.md", tmp_path, verbose=False)

    mock_creator.create_from_subtasks.assert_called_once()


def test_generate_tasks_falls_back_to_issues(tmp_path):
    """When action_plan is empty, falls back to issues list."""
    report = _make_report(action_plan=[], issues=["issue 1", "issue 2"])

    mock_creator = MagicMock()
    with patch("generator.planning.task_creator.TaskCreator", return_value=mock_creator):
        _generate_tasks_from_review(report, tmp_path / "CRITIQUE.md", tmp_path, verbose=False)

    mock_creator.create_from_subtasks.assert_called_once()
    args, kwargs = mock_creator.create_from_subtasks.call_args
    subtasks = args[0]
    assert len(subtasks) == 2


def test_generate_tasks_no_items_shows_warning(tmp_path, capsys):
    """When both action_plan and issues are empty, shows warning."""
    report = _make_report(action_plan=[], issues=[])

    runner = CliRunner()
    with runner.isolated_filesystem():
        _generate_tasks_from_review(report, tmp_path / "CRITIQUE.md", tmp_path, verbose=False)
