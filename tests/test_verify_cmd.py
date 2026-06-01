"""Tests for the ``prg verify`` command (cli/verify_cmd.py).

This command was at 45% coverage (CR §4.4). It is a thin wrapper around
``PreflightChecker``: it runs the checks, prints the report, and exits 1 when any
critical check fails. We mock the checker so both the ready and not-ready branches
are exercised without touching a real project.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cli.verify_cmd import verify


def _report(*, all_passed, failed=None):
    """Build a stand-in PreflightReport with the attributes verify() reads."""
    return SimpleNamespace(
        all_passed=all_passed,
        failed_checks=[SimpleNamespace(name=n) for n in (failed or [])],
        format_report=lambda: "PREFLIGHT REPORT BODY",
    )


class TestVerifyCommand:
    def test_ralph_ready_exits_zero(self, tmp_path):
        """All checks pass → report printed, success line, exit 0."""
        with patch("generator.planning.preflight.PreflightChecker") as checker_cls:
            checker_cls.return_value.run_checks.return_value = _report(all_passed=True)
            result = CliRunner().invoke(verify, [str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "PREFLIGHT REPORT BODY" in result.output
        assert "Ralph-ready" in result.output

    def test_failed_checks_exit_one(self, tmp_path):
        """A failing check → failed names surfaced on stderr and exit 1."""
        with patch("generator.planning.preflight.PreflightChecker") as checker_cls:
            checker_cls.return_value.run_checks.return_value = _report(all_passed=False, failed=["rules.md", "tests/"])
            result = CliRunner().invoke(verify, [str(tmp_path)])

        assert result.exit_code == 1
        assert "Failed checks: rules.md, tests/" in result.output
        assert "before `prg ralph`" in result.output

    def test_checker_built_with_resolved_path(self, tmp_path):
        """The checker is constructed against the resolved project path."""
        with patch("generator.planning.preflight.PreflightChecker") as checker_cls:
            checker_cls.return_value.run_checks.return_value = _report(all_passed=True)
            CliRunner().invoke(verify, [str(tmp_path)])

        kwargs = checker_cls.call_args.kwargs
        assert kwargs["project_path"] == tmp_path.resolve()
        assert "readiness check" in kwargs["task_description"]

    def test_quiet_flag_accepted(self, tmp_path):
        """--quiet flips logging level without changing the exit contract."""
        with patch("generator.planning.preflight.PreflightChecker") as checker_cls:
            checker_cls.return_value.run_checks.return_value = _report(all_passed=True)
            result = CliRunner().invoke(verify, [str(tmp_path), "--quiet"])

        assert result.exit_code == 0, result.output
        assert "Ralph-ready" in result.output

    def test_defaults_to_current_directory(self):
        """With no path argument the command defaults to '.' and still runs."""
        runner = CliRunner()
        with runner.isolated_filesystem(), patch("generator.planning.preflight.PreflightChecker") as checker_cls:
            checker_cls.return_value.run_checks.return_value = _report(all_passed=True)
            result = runner.invoke(verify, [])

        assert result.exit_code == 0, result.output
