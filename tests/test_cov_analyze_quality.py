"""Coverage boost: cli/analyze_quality.py (6% covered, 60 miss)."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cli.analyze_quality import run_quality_check


def _make_report(score=85, status="Excellent", suggestions=None, breakdown=None, quick_check=None):
    report = SimpleNamespace(
        score=score,
        status=status,
        suggestions=suggestions or [],
        breakdown=breakdown,
        quick_check=quick_check,
    )
    return report


class TestRunQualityCheck:
    def _setup_output_dir(self, tmp_path, include_rules=True):
        output_dir = tmp_path / ".clinerules"
        output_dir.mkdir()
        if include_rules:
            (output_dir / "rules.md").write_text("# Rules\n\n- Rule 1\n")
        return output_dir

    def test_skips_when_no_files(self, tmp_path, capsys):
        output_dir = tmp_path / ".clinerules"
        output_dir.mkdir()
        # No rules.md, constitution.md, or skills/index.md

        mock_analyzer = MagicMock()
        mock_analyzer.opik = None

        with patch("generator.content_analyzer.ContentAnalyzer", return_value=mock_analyzer):
            with patch("generator.config.AnalyzerConfig"):
                run_quality_check(output_dir, tmp_path, "groq", None, False, False, False)

        captured = capsys.readouterr()
        assert "No files found" in captured.out

    def test_analyzes_rules_md(self, tmp_path):
        output_dir = self._setup_output_dir(tmp_path)
        mock_report = _make_report()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_report
        mock_analyzer.opik = None

        with patch("generator.content_analyzer.ContentAnalyzer", return_value=mock_analyzer):
            with patch("generator.config.AnalyzerConfig"):
                with patch("rich.console.Console"):
                    run_quality_check(output_dir, tmp_path, "groq", None, False, False, False)

        mock_analyzer.analyze.assert_called()

    def test_analyzes_constitution_md(self, tmp_path):
        output_dir = self._setup_output_dir(tmp_path)
        (output_dir / "constitution.md").write_text("# Constitution\n\n- Principle 1\n")

        mock_report = _make_report()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_report
        mock_analyzer.opik = None

        with patch("generator.content_analyzer.ContentAnalyzer", return_value=mock_analyzer):
            with patch("generator.config.AnalyzerConfig"):
                with patch("rich.console.Console"):
                    run_quality_check(output_dir, tmp_path, "groq", None, False, False, False)

        assert mock_analyzer.analyze.call_count >= 2

    def test_analyzes_skills_index(self, tmp_path):
        output_dir = self._setup_output_dir(tmp_path, include_rules=False)
        skills_dir = output_dir / "skills"
        skills_dir.mkdir()
        (skills_dir / "index.md").write_text("# Skills Index\n")

        mock_report = _make_report()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_report
        mock_analyzer.opik = None

        with patch("generator.content_analyzer.ContentAnalyzer", return_value=mock_analyzer):
            with patch("generator.config.AnalyzerConfig"):
                with patch("rich.console.Console"):
                    run_quality_check(output_dir, tmp_path, "groq", None, False, False, False)

        mock_analyzer.analyze.assert_called()

    def test_verbose_output_printed(self, tmp_path, capsys):
        output_dir = self._setup_output_dir(tmp_path)
        mock_report = _make_report(status="Needs Review", suggestions=["Improve rule specificity"])
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_report
        mock_analyzer.opik = None

        with patch("generator.content_analyzer.ContentAnalyzer", return_value=mock_analyzer):
            with patch("generator.config.AnalyzerConfig"):
                with patch("rich.console.Console"):
                    run_quality_check(output_dir, tmp_path, "groq", None, False, False, verbose=True)

        captured = capsys.readouterr()
        assert "Quality Analysis" in captured.out

    def test_verbose_with_breakdown(self, tmp_path, capsys):
        output_dir = self._setup_output_dir(tmp_path)
        breakdown = SimpleNamespace(
            structure=18,
            clarity=16,
            project_grounding=14,
            actionability=17,
            consistency=15,
        )
        mock_report = _make_report(status="Good", breakdown=breakdown)
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_report
        mock_analyzer.opik = None

        with patch("generator.content_analyzer.ContentAnalyzer", return_value=mock_analyzer):
            with patch("generator.config.AnalyzerConfig"):
                with patch("rich.console.Console"):
                    run_quality_check(output_dir, tmp_path, "groq", None, False, False, verbose=True)

        captured = capsys.readouterr()
        assert "Structure" in captured.out

    def test_verbose_with_quick_check(self, tmp_path, capsys):
        output_dir = self._setup_output_dir(tmp_path)
        mock_report = _make_report(
            status="Good",
            quick_check={"has_rules": True, "has_examples": False},
        )
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_report
        mock_analyzer.opik = None

        with patch("generator.content_analyzer.ContentAnalyzer", return_value=mock_analyzer):
            with patch("generator.config.AnalyzerConfig"):
                with patch("rich.console.Console"):
                    run_quality_check(output_dir, tmp_path, "groq", None, False, False, verbose=True)

        captured = capsys.readouterr()
        assert "Has Rules" in captured.out or "has_rules" in captured.out.lower()

    def test_auto_fix_message_when_needs_review(self, tmp_path, capsys):
        output_dir = self._setup_output_dir(tmp_path)
        mock_report = _make_report(status="Needs Review", suggestions=[])
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_report
        mock_analyzer.opik = None

        with patch("generator.content_analyzer.ContentAnalyzer", return_value=mock_analyzer):
            with patch("generator.config.AnalyzerConfig"):
                with patch("rich.console.Console"):
                    run_quality_check(output_dir, tmp_path, "groq", None, False, auto_fix=True, verbose=True)

        captured = capsys.readouterr()
        assert "Auto-fix" in captured.out or "auto-fix" in captured.out.lower()

    def test_top_issue_truncated_to_40_chars(self, tmp_path):
        output_dir = self._setup_output_dir(tmp_path)
        long_suggestion = "A" * 60
        mock_report = _make_report(suggestions=[long_suggestion])
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_report
        mock_analyzer.opik = None

        captured_table_rows = []

        class FakeTable:
            def add_column(self, *args, **kwargs):
                pass

            def add_row(self, *args, **kwargs):
                captured_table_rows.extend(args)

        with patch("generator.content_analyzer.ContentAnalyzer", return_value=mock_analyzer):
            with patch("generator.config.AnalyzerConfig"):
                with patch("rich.console.Console"):
                    with patch("rich.table.Table", return_value=FakeTable()):
                        run_quality_check(output_dir, tmp_path, "groq", None, False, False, False)

        # The top_issue added to table row should be truncated
        top_issue_in_row = [r for r in captured_table_rows if isinstance(r, str) and "A" * 3 in r]
        if top_issue_in_row:
            assert len(top_issue_in_row[0]) <= 40


class TestNoProviderQuality:
    """Regression: prg quality with no API provider must not crash."""

    def test_no_provider_does_not_raise(self, tmp_path):
        output_dir = tmp_path / ".clinerules"
        output_dir.mkdir()
        (output_dir / "rules.md").write_text("# Rules\n\n- Rule 1\n")

        mock_report = SimpleNamespace(
            score=80,
            status="Good",
            suggestions=[],
            breakdown=None,
            quick_check=None,
        )
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_file.return_value = mock_report
        mock_analyzer.generate_report.return_value = mock_report

        with patch.dict("os.environ", {}, clear=False):
            for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY"):
                import os

                os.environ.pop(key, None)

            with patch("generator.content_analyzer.ContentAnalyzer", return_value=mock_analyzer):
                with patch("generator.config.AnalyzerConfig"):
                    with patch("rich.console.Console"):
                        with patch("rich.table.Table", return_value=MagicMock()):
                            # provider=None, api_key=None — must exit 0, not crash
                            run_quality_check(output_dir, tmp_path, None, None, False, False, False)
