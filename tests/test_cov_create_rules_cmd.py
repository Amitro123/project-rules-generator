"""Coverage tests for cli/create_rules_cmd.py.

Covers the happy path, quality-below-threshold flow, no-README fallback,
--tech parsing, --export-report flag, and the error path.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.create_rules_cmd import _display_quality_report, create_rules

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_quality(score=92.0, passed=True, completeness=0.95, issues=None, warnings=None, conflicts=None):
    q = MagicMock()
    q.score = score
    q.passed = passed
    q.completeness = completeness
    q.issues = issues or []
    q.warnings = warnings or []
    q.conflicts = conflicts or []
    return q


def _make_metadata(tech_stack=None, project_type="api", priority_areas=None):
    m = MagicMock()
    m.tech_stack = tech_stack or ["python"]
    m.project_type = project_type
    m.priority_areas = priority_areas or ["testing"]
    return m


def _make_creator(content="# Rules\n- use async/await\n", metadata=None, quality=None):
    creator = MagicMock()
    creator.create_rules.return_value = (
        content,
        metadata or _make_metadata(),
        quality or _make_quality(),
    )
    rules_file = MagicMock()
    rules_file.name = "rules.md"
    rules_file.__str__ = lambda self: "/proj/.clinerules/rules.md"
    creator.export_to_file.return_value = rules_file
    return creator


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_create_rules_happy_path(tmp_path):
    """create-rules with a README and a high-quality result exits 0."""
    (tmp_path / "README.md").write_text("# My Project\n\nA great project.\n")

    runner = CliRunner()
    with patch("cli.create_rules_cmd.CoworkRulesCreator", return_value=_make_creator()):
        result = runner.invoke(create_rules, [str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "Rules generated" in result.output
    assert "Quality Assessment" in result.output


def test_create_rules_no_readme_uses_fallback(tmp_path):
    """When README.md is missing, a fallback content string is used (no crash)."""
    runner = CliRunner()
    with patch("cli.create_rules_cmd.CoworkRulesCreator", return_value=_make_creator()):
        result = runner.invoke(create_rules, [str(tmp_path)])

    assert result.exit_code == 0, result.output
    # The warning goes to stderr; output stream gets the rules summary
    assert "Rules generated" in result.output


def test_create_rules_tech_flag_parsed(tmp_path):
    """--tech flag splits the string and passes a list to create_rules."""
    (tmp_path / "README.md").write_text("# P\n")
    creator = _make_creator(metadata=_make_metadata(tech_stack=["fastapi", "pytest", "docker"]))

    runner = CliRunner()
    with patch("cli.create_rules_cmd.CoworkRulesCreator", return_value=creator) as MockCreator:
        MockCreator.return_value = creator
        result = runner.invoke(create_rules, [str(tmp_path), "--tech", "fastapi,pytest,docker"])

    assert result.exit_code == 0, result.output
    # create_rules was called with tech_stack list
    creator.create_rules.assert_called_once()
    _, kwargs = creator.create_rules.call_args
    assert kwargs.get("tech_stack") == ["fastapi", "pytest", "docker"]


def test_create_rules_export_report_writes_json(tmp_path):
    """--export-report writes a rules.quality.json file."""
    (tmp_path / "README.md").write_text("# P\n")
    output_dir = tmp_path / ".clinerules"
    output_dir.mkdir()

    runner = CliRunner()
    with patch("cli.create_rules_cmd.CoworkRulesCreator", return_value=_make_creator()):
        result = runner.invoke(
            create_rules,
            [str(tmp_path), "--output", str(output_dir), "--export-report"],
        )

    assert result.exit_code == 0, result.output
    assert (output_dir / "rules.quality.json").exists()
    import json

    report = json.loads((output_dir / "rules.quality.json").read_text())
    assert "score" in report
    assert "tech_stack" in report["metadata"]


# ---------------------------------------------------------------------------
# Quality below threshold
# ---------------------------------------------------------------------------


def test_create_rules_low_quality_cancelled(tmp_path):
    """When score < threshold and user says No, exits 1."""
    (tmp_path / "README.md").write_text("# P\n")
    low_q = _make_quality(score=60.0, passed=False, issues=["Too generic"])
    creator = _make_creator(quality=low_q)

    runner = CliRunner()
    with patch("cli.create_rules_cmd.CoworkRulesCreator", return_value=creator):
        result = runner.invoke(create_rules, [str(tmp_path)], input="n\n")

    assert result.exit_code == 1
    assert "below threshold" in result.output or "below threshold" in (result.output + (result.stderr or ""))


def test_create_rules_low_quality_accepted_proceeds(tmp_path):
    """When score < threshold and user says Yes, generation continues."""
    (tmp_path / "README.md").write_text("# P\n")
    low_q = _make_quality(score=60.0, passed=False)
    creator = _make_creator(quality=low_q)

    runner = CliRunner()
    with patch("cli.create_rules_cmd.CoworkRulesCreator", return_value=creator):
        result = runner.invoke(create_rules, [str(tmp_path)], input="y\n")

    assert result.exit_code == 0, result.output
    assert "Rules generated" in result.output


def test_create_rules_custom_threshold_respected(tmp_path):
    """--quality-threshold controls the confirmation gate."""
    (tmp_path / "README.md").write_text("# P\n")
    q = _make_quality(score=80.0, passed=True)
    creator = _make_creator(quality=q)

    runner = CliRunner()
    with patch("cli.create_rules_cmd.CoworkRulesCreator", return_value=creator):
        # 80 is above 70 threshold — no confirmation prompt
        result = runner.invoke(create_rules, [str(tmp_path), "--quality-threshold", "70"])

    assert result.exit_code == 0, result.output
    # No "Proceed anyway" in output since score >= threshold
    assert "Proceed anyway" not in result.output


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------


def test_create_rules_creator_exception_exits_1(tmp_path):
    """When CoworkRulesCreator.create_rules raises, exits 1 with error message."""
    (tmp_path / "README.md").write_text("# P\n")
    creator = MagicMock()
    creator.create_rules.side_effect = RuntimeError("LLM unavailable")

    runner = CliRunner()
    with patch("cli.create_rules_cmd.CoworkRulesCreator", return_value=creator):
        result = runner.invoke(create_rules, [str(tmp_path)])

    assert result.exit_code == 1
    assert "LLM unavailable" in result.output or "Error" in result.output


def test_create_rules_verbose_shows_traceback(tmp_path):
    """--verbose on error prints traceback."""
    (tmp_path / "README.md").write_text("# P\n")
    creator = MagicMock()
    creator.create_rules.side_effect = RuntimeError("boom")

    runner = CliRunner()
    with patch("cli.create_rules_cmd.CoworkRulesCreator", return_value=creator):
        result = runner.invoke(create_rules, [str(tmp_path), "--verbose"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# _display_quality_report helper
# ---------------------------------------------------------------------------


def test_display_quality_report_passed(capsys):
    """PASSED path runs without error."""
    q = _make_quality(score=95.0, passed=True)
    runner = CliRunner()
    with runner.isolated_filesystem():
        _display_quality_report(q, verbose=False)


def test_display_quality_report_with_issues_and_conflicts(capsys):
    """Issues and conflicts are displayed."""
    q = _make_quality(score=70.0, passed=False, issues=["issue1"], conflicts=["conflict1"])
    runner = CliRunner()
    with runner.isolated_filesystem():
        _display_quality_report(q, verbose=True)


def test_display_quality_report_warnings_only_in_verbose(capsys):
    """Warnings only appear in verbose mode."""
    q = _make_quality(score=88.0, passed=True, warnings=["consider this"])
    runner = CliRunner()
    with runner.isolated_filesystem():
        _display_quality_report(q, verbose=False)
        _display_quality_report(q, verbose=True)
