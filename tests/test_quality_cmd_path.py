"""Tests for ``prg quality`` path resolution (cli/quality_cmd.py).

The command takes PATH = project root and joins ``--output`` (default
``.clinerules``) onto it. Pointing PATH straight at the output dir
(``prg quality .clinerules``) used to double to ``.clinerules/.clinerules`` and
fail with a misleading "run analyze first" hint. The command now forgives that
when PATH itself holds generated rules. These tests pin both branches.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from cli.quality_cmd import quality_cmd


def _invoke(args):
    """Run quality_cmd with run_quality_check / provider lookups mocked out."""
    with (
        patch("cli.analyze_quality.run_quality_check") as run,
        patch("cli.utils.detect_provider", return_value="groq"),
        patch("cli.utils.set_api_key_env"),
    ):
        result = CliRunner().invoke(quality_cmd, args)
    return result, run


class TestQualityPathResolution:
    def test_path_at_project_root_uses_clinerules_subdir(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".clinerules").mkdir()
            Path(".clinerules/rules.md").write_text("# rules", encoding="utf-8")
            result, run = _invoke(["."])

        assert result.exit_code == 0, result.output
        called_output_dir = run.call_args.kwargs["output_dir"]
        assert called_output_dir.name == ".clinerules"
        assert called_output_dir.parent.name != ".clinerules"  # not doubled

    def test_path_pointed_at_output_dir_is_forgiven(self):
        """`prg quality .clinerules` resolves to that dir, not .clinerules/.clinerules."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".clinerules").mkdir()
            Path(".clinerules/rules.md").write_text("# rules", encoding="utf-8")
            result, run = _invoke([".clinerules"])

        assert result.exit_code == 0, result.output
        called_output_dir = run.call_args.kwargs["output_dir"]
        assert called_output_dir.name == ".clinerules"
        # The forgiving branch must not produce a nested .clinerules/.clinerules.
        assert called_output_dir.parent.name != ".clinerules"
        # Project path is corrected to the parent of the output dir.
        assert run.call_args.kwargs["project_path"] == called_output_dir.parent

    def test_missing_output_dir_still_errors(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("emptyproj").mkdir()  # no .clinerules, no rules.md
            result, _ = _invoke(["emptyproj"])

        assert result.exit_code == 1
        assert "Output directory not found" in result.output
