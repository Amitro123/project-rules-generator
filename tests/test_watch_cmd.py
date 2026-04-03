"""Tests for prg watch command — debounce logic and file pattern matching."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from cli.watch_cmd import _PRGHandler, _should_trigger


# ---------------------------------------------------------------------------
# _should_trigger — pattern matching
# ---------------------------------------------------------------------------


class TestShouldTrigger:
    def test_readme_triggers(self, tmp_path):
        assert _should_trigger(str(tmp_path / "README.md"), tmp_path)

    def test_readme_rst_triggers(self, tmp_path):
        assert _should_trigger(str(tmp_path / "README.rst"), tmp_path)

    def test_pyproject_triggers(self, tmp_path):
        assert _should_trigger(str(tmp_path / "pyproject.toml"), tmp_path)

    def test_requirements_triggers(self, tmp_path):
        assert _should_trigger(str(tmp_path / "requirements.txt"), tmp_path)

    def test_package_json_triggers(self, tmp_path):
        assert _should_trigger(str(tmp_path / "package.json"), tmp_path)

    def test_dockerfile_triggers(self, tmp_path):
        assert _should_trigger(str(tmp_path / "Dockerfile"), tmp_path)

    def test_random_py_file_does_not_trigger(self, tmp_path):
        assert not _should_trigger(str(tmp_path / "utils.py"), tmp_path)

    def test_random_txt_does_not_trigger(self, tmp_path):
        assert not _should_trigger(str(tmp_path / "notes.txt"), tmp_path)

    def test_file_in_tests_dir_triggers(self, tmp_path):
        (tmp_path / "tests").mkdir()
        assert _should_trigger(str(tmp_path / "tests" / "test_foo.py"), tmp_path)

    def test_file_in_test_dir_triggers(self, tmp_path):
        (tmp_path / "test").mkdir()
        assert _should_trigger(str(tmp_path / "test" / "anything.py"), tmp_path)

    def test_test_prefixed_file_triggers(self, tmp_path):
        assert _should_trigger(str(tmp_path / "test_auth.py"), tmp_path)

    def test_test_suffixed_file_triggers(self, tmp_path):
        assert _should_trigger(str(tmp_path / "auth_test.py"), tmp_path)

    def test_outside_project_path_does_not_trigger(self, tmp_path):
        other = tmp_path.parent / "other_project" / "README.md"
        assert not _should_trigger(str(other), tmp_path)


# ---------------------------------------------------------------------------
# _PRGHandler — debounce and re-entry guard
# ---------------------------------------------------------------------------


class TestPRGHandlerDebounce:
    def _make_handler(self, tmp_path, delay=0.05):
        return _PRGHandler(project_path=tmp_path, delay=delay, extra_args=[], verbose=False)

    def test_single_change_triggers_analyze(self, tmp_path):
        handler = self._make_handler(tmp_path)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            handler.on_change(str(tmp_path / "README.md"))
            time.sleep(0.2)  # wait for debounce + subprocess mock
        assert mock_run.called

    def test_rapid_changes_coalesce_to_one_run(self, tmp_path):
        handler = self._make_handler(tmp_path, delay=0.1)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            # Fire 5 rapid changes
            for _ in range(5):
                handler.on_change(str(tmp_path / "README.md"))
                time.sleep(0.01)
            time.sleep(0.3)  # wait for final debounce
        assert mock_run.call_count == 1, f"Expected 1 call, got {mock_run.call_count}"

    def test_non_triggering_file_does_not_call_analyze(self, tmp_path):
        handler = self._make_handler(tmp_path)
        with patch("subprocess.run") as mock_run:
            handler.on_change(str(tmp_path / "notes.txt"))
            time.sleep(0.2)
        assert not mock_run.called

    def test_cancel_prevents_pending_trigger(self, tmp_path):
        handler = self._make_handler(tmp_path, delay=0.5)
        with patch("subprocess.run") as mock_run:
            handler.on_change(str(tmp_path / "README.md"))
            handler.cancel()
            time.sleep(0.7)
        assert not mock_run.called

    def test_extra_args_passed_to_subprocess(self, tmp_path):
        handler = _PRGHandler(tmp_path, delay=0.05, extra_args=["--ide", "cursor"], verbose=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            handler.on_change(str(tmp_path / "README.md"))
            time.sleep(0.2)
        assert mock_run.called
        cmd_args = mock_run.call_args[0][0]
        assert "--ide" in cmd_args
        assert "cursor" in cmd_args
        assert "--incremental" in cmd_args


# ---------------------------------------------------------------------------
# CLI integration — import and help
# ---------------------------------------------------------------------------


class TestWatchCommandRegistered:
    def test_watch_command_importable(self):
        from cli.watch_cmd import watch

        assert watch is not None

    def test_watch_help_text(self):
        from click.testing import CliRunner

        from cli.watch_cmd import watch

        runner = CliRunner()
        result = runner.invoke(watch, ["--help"])
        assert result.exit_code == 0
        assert "incremental" in result.output.lower() or "watch" in result.output.lower()

    def test_watch_missing_watchdog_gives_clear_error(self, tmp_path):
        """When watchdog is not importable, the command prints a helpful error."""
        from click.testing import CliRunner

        from cli.watch_cmd import watch

        runner = CliRunner()
        with patch.dict("sys.modules", {"watchdog": None, "watchdog.observers": None, "watchdog.events": None}):
            result = runner.invoke(watch, [str(tmp_path)])
        assert result.exit_code != 0 or "watchdog" in result.output.lower()
