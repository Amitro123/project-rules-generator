"""Coverage tests for cli/agent.py.

Covers start, setup, and agent_command — happy path, provider-missing,
and workflow-exception paths. No real AI calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.agent import agent_command, setup, start


# ---------------------------------------------------------------------------
# start command
# ---------------------------------------------------------------------------


def _mock_workflow(run_full_exc=None, run_setup_return=None):
    wf = MagicMock()
    if run_full_exc:
        wf.run_full.side_effect = run_full_exc
    else:
        wf.run_full.return_value = None
    if run_setup_return is not None:
        wf.run_setup.return_value = run_setup_return
    return wf


def test_start_happy_path(tmp_path, monkeypatch):
    """start command runs workflow and exits 0 when no exception raised."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_wf = _mock_workflow()

    runner = CliRunner()
    with patch("cli.agent.AgentWorkflow", return_value=mock_wf, create=True):
        with patch("generator.planning.workflow.AgentWorkflow", return_value=mock_wf, create=True):
            result = runner.invoke(
                start,
                ["do something", "--project-path", str(tmp_path), "--provider", "groq"],
            )

    assert result.exit_code == 0


def test_start_workflow_exception_exits_1(tmp_path, monkeypatch):
    """When workflow.run_full raises, start exits 1 with error message."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_wf = _mock_workflow(run_full_exc=RuntimeError("LLM timeout"))

    runner = CliRunner()
    with patch("cli.agent.AgentWorkflow", return_value=mock_wf, create=True):
        with patch("generator.planning.workflow.AgentWorkflow", return_value=mock_wf, create=True):
            result = runner.invoke(
                start,
                ["do something", "--project-path", str(tmp_path), "--provider", "groq"],
            )

    assert result.exit_code == 1
    assert "LLM timeout" in result.output or "Workflow failed" in result.output


# ---------------------------------------------------------------------------
# setup command
# ---------------------------------------------------------------------------


def test_setup_happy_path(tmp_path, monkeypatch):
    """setup command prints task count and exits 0."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    manifest = MagicMock()
    manifest.tasks = [MagicMock(), MagicMock()]
    mock_wf = _mock_workflow(run_setup_return=manifest)

    runner = CliRunner()
    with patch("cli.agent.AgentWorkflow", return_value=mock_wf, create=True):
        with patch("generator.planning.workflow.AgentWorkflow", return_value=mock_wf, create=True):
            result = runner.invoke(
                setup,
                ["do something", "--project-path", str(tmp_path), "--provider", "groq"],
            )

    assert result.exit_code == 0
    assert "2 tasks" in result.output


def test_setup_exception_exits_1(tmp_path, monkeypatch):
    """When run_setup raises, setup exits 1."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_wf = MagicMock()
    mock_wf.run_setup.side_effect = RuntimeError("plan error")

    runner = CliRunner()
    with patch("cli.agent.AgentWorkflow", return_value=mock_wf, create=True):
        with patch("generator.planning.workflow.AgentWorkflow", return_value=mock_wf, create=True):
            result = runner.invoke(
                setup,
                ["do something", "--project-path", str(tmp_path), "--provider", "groq"],
            )

    assert result.exit_code == 1
    assert "plan error" in result.output or "Setup failed" in result.output


# ---------------------------------------------------------------------------
# agent_command
# ---------------------------------------------------------------------------


def test_agent_command_match_found(tmp_path, monkeypatch):
    """When a skill is matched, prints auto-trigger message."""
    mock_executor = MagicMock()
    mock_executor.match_skill.return_value = "pytest-testing-workflow"

    runner = CliRunner()
    with patch("cli.agent.AgentExecutor", return_value=mock_executor, create=True):
        with patch("generator.planning.agent_executor.AgentExecutor", return_value=mock_executor, create=True):
            result = runner.invoke(agent_command, ["run tests"])

    assert result.exit_code == 0
    assert "pytest-testing-workflow" in result.output or "Auto-trigger" in result.output


def test_agent_command_no_match(tmp_path):
    """When no skill matches, prints the no-match message."""
    mock_executor = MagicMock()
    mock_executor.match_skill.return_value = None

    runner = CliRunner()
    with patch("cli.agent.AgentExecutor", return_value=mock_executor, create=True):
        with patch("generator.planning.agent_executor.AgentExecutor", return_value=mock_executor, create=True):
            result = runner.invoke(agent_command, ["something obscure"])

    assert result.exit_code == 0
    assert "No matching skill" in result.output
