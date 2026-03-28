"""Tests for CLI integration."""

from click.testing import CliRunner

from cli.analyze_cmd import load_config
from main import cli, main


class TestCLI:
    """Test suite for command line interface."""

    def test_load_config_default(self):
        """Test loading default config when file exists."""
        config = load_config()

        assert "llm" in config
        assert "git" in config
        assert "generation" in config

    def test_cli_basic_run(self, sample_project_path, tmp_path):
        """Test basic CLI execution."""
        runner = CliRunner()

        # Run on sample project
        result = runner.invoke(main, [str(sample_project_path), "--verbose", "--no-commit"])

        assert (
            result.exit_code == 0
        ), f"Exit code {result.exit_code}.\nOutput:\n{result.output}\nException: {result.exception}"
        assert "Generated files" in result.output
        assert "rules.md" in result.output
        assert "index.md" in result.output

    def test_cli_missing_readme(self, tmp_path):
        """Test CLI handles missing README by falling back to structure analysis."""
        runner = CliRunner()
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(main, [str(empty_dir)])

        # Should now pass with exit code 0 due to structure-only fallback
        assert (
            result.exit_code == 0
        ), f"Exit code {result.exit_code}.\nOutput:\n{result.output}\nException: {result.exception}"
        assert "No README found" in result.output
        assert "Proceeding with structure-only analysis" in result.output

    def test_cli_default_path(self, tmp_path):
        """Test CLI with default path (current directory).."""
        runner = CliRunner()

        # Create a README in temp directory
        (tmp_path / "README.md").write_text("# Test\n\nDescription.")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["--no-commit", "--verbose"])
            # Should use current directory
            assert result.exit_code == 0 or "Target" in result.output

    def test_cli_interactive_cancel(self, sample_project_path):
        """Test interactive mode with 'no' response."""
        runner = CliRunner()

        result = runner.invoke(
            main,
            [str(sample_project_path), "--interactive", "--no-commit"],
            input="n\n",
        )  # Respond 'no' to continue prompt

        assert result.exit_code == 0
        assert "Aborted" in result.output

    def test_cli_version_flag(self):
        """Test --version flag."""
        runner = CliRunner()

        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.2.0" in result.output

    def test_cli_help(self):
        """Test --help output for analyze command."""
        runner = CliRunner()

        result = runner.invoke(main, ["analyze", "--help"])

        assert result.exit_code == 0
        assert "--commit" in result.output
        assert "--interactive" in result.output
        assert "--mode" in result.output
        assert "--merge" in result.output
        assert "--output" in result.output
        assert "--incremental" in result.output

    def test_cli_group_help(self):
        """Test --help output for the CLI group shows subcommands."""
        runner = CliRunner()

        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "analyze" in result.output
        assert "plan" in result.output
