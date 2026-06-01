"""Tests for CLI integration."""

from pathlib import Path

from click.testing import CliRunner

from cli.analyze_cmd import load_config
from cli.cli import cli

main = cli


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
        """Test --version flag outputs a version string."""
        from cli._version import __version__

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.output

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


class TestDefaultGroupRouting:
    """Lock in the CR §4.3 fix: the default command only swallows path/option
    first-args, so a mistyped sub-command errors loudly instead of silently
    becoming `prg analyze <typo>`.
    """

    def test_helper_routes_paths_and_options(self):
        """Path-like and option first-args route to the default command."""
        from cli.cli import _looks_like_default_target

        assert _looks_like_default_target(".") is True
        assert _looks_like_default_target("..") is True
        assert _looks_like_default_target("--ide") is True
        assert _looks_like_default_target("-v") is True
        assert _looks_like_default_target("some/nested/path") is True
        assert _looks_like_default_target("some\\win\\path") is True

    def test_helper_rejects_bare_words(self):
        """A bare unknown word is NOT treated as a default-command argument."""
        from cli.cli import _looks_like_default_target

        assert _looks_like_default_target("analyse") is False  # typo of `analyze`
        assert _looks_like_default_target("definitelynotacommand") is False

    def test_helper_accepts_existing_path(self, tmp_path):
        """An existing file/dir on disk is unambiguously a path argument."""
        from cli.cli import _looks_like_default_target

        existing = tmp_path / "myproject"
        existing.mkdir()
        with CliRunner().isolated_filesystem(temp_dir=tmp_path):
            # Relative name that exists on disk → path argument.
            (Path.cwd() / "exists-here").mkdir()
            assert _looks_like_default_target("exists-here") is True

    def test_typo_subcommand_errors_instead_of_routing(self):
        """`prg analyse` (typo) errors with 'No such command', not silent routing."""
        runner = CliRunner()
        result = runner.invoke(cli, ["definitely-not-a-command"])

        assert result.exit_code != 0
        assert "No such command" in result.output


class TestCLISurfaceCuration:
    """Lock in the CR §4.5 fix: `prg --help` lists only the stable core; the
    rest are hidden but still invocable.
    """

    STABLE = {"init", "analyze", "create-rules", "quality", "skills", "plan", "providers", "status"}
    EXPERIMENTAL_SAMPLE = ["ralph", "feature", "manager", "gaps", "spec", "agent"]

    def test_help_lists_only_stable_commands(self):
        """The group --help advertises the 8 stable commands and hides the rest."""
        result = CliRunner().invoke(cli, ["--help"])
        assert result.exit_code == 0

        # Parse the actual command names from the Commands: section. Matching the
        # leading token per line avoids false positives like "spec" inside the
        # word "Inspect" in another command's description.
        commands_section = result.output.split("Commands:", 1)[-1]
        listed = {line.split()[0] for line in commands_section.splitlines() if line.startswith("  ") and line.strip()}

        assert self.STABLE <= listed, f"missing stable commands: {self.STABLE - listed}"
        leaked = listed & set(self.EXPERIMENTAL_SAMPLE)
        assert not leaked, f"experimental commands should be hidden: {leaked}"

    def test_hidden_commands_are_still_registered(self):
        """Hidden commands remain in the registry and are marked hidden."""
        for name in self.EXPERIMENTAL_SAMPLE:
            assert name in cli.commands, f"{name!r} must stay registered (just hidden)"
            assert cli.commands[name].hidden is True

    def test_hidden_command_still_invocable(self):
        """A hidden command still runs (hidden affects listing only, not dispatch)."""
        result = CliRunner().invoke(cli, ["ralph", "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
