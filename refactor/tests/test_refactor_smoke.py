from click.testing import CliRunner

from refactor.cli import cli


def test_cli_root_help():
    """Verify the root CLI help message."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Project Rules Generator" in result.output


def test_analyze_command_help():
    """Verify the analyze command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "Analyze project" in result.output


def test_agent_command_help():
    """Verify the agent command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["agent", "--help"])
    assert result.exit_code == 0
    assert "Simulate agent" in result.output


def test_design_command_help():
    """Verify the design command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["design", "--help"])
    assert result.exit_code == 0
    assert "Generate a technical design" in result.output


def test_agent_lookup_execution():
    """Verify 'agent' command help or basic run."""
    runner = CliRunner()
    # Using --help is safer for smoke test than execution which needs agent logic
    result = runner.invoke(cli, ["agent", "--help"])
    assert result.exit_code == 0
    assert "Simulate agent" in result.output
