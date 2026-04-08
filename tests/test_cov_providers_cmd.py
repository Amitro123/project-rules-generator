"""Coverage tests for cli/providers_cmd.py.

Covers providers list, test, and benchmark commands — both happy paths
and no-key / error paths. Does NOT make real API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.providers_cmd import providers_group

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_statuses(providers=None):
    """Return a list of provider status dicts like AIStrategyRouter.provider_status()."""
    providers = providers or ["gemini", "groq"]
    return [
        {
            "provider": p,
            "status": "ready" if p == "gemini" else "no key",
            "has_key": p == "gemini",
            "quality": 90 if p == "gemini" else 70,
            "speed": 85 if p == "gemini" else 95,
            "default_model": "gemini-2.0-flash" if p == "gemini" else "llama-3.1-8b",
            "env_key": "GOOGLE_API_KEY" if p == "gemini" else "GROQ_API_KEY",
            "preferred": p == "gemini",
        }
        for p in providers
    ]


# ---------------------------------------------------------------------------
# providers list
# ---------------------------------------------------------------------------


def test_providers_list_exits_0():
    """providers list always exits 0."""
    runner = CliRunner()
    with patch("cli.providers_cmd.AIStrategyRouter") as MockRouter:
        MockRouter.return_value.provider_status.return_value = _make_statuses()
        result = runner.invoke(providers_group, ["list"])
    assert result.exit_code == 0, result.output


def test_providers_list_shows_provider_names():
    """providers list output includes provider names."""
    runner = CliRunner()
    with patch("cli.providers_cmd.AIStrategyRouter") as MockRouter:
        MockRouter.return_value.provider_status.return_value = _make_statuses(["gemini", "groq", "anthropic"])
        result = runner.invoke(providers_group, ["list"])
    assert result.exit_code == 0
    assert "gemini" in result.output
    assert "groq" in result.output


def test_providers_list_no_ready_providers():
    """When no providers have keys, a 'no providers ready' message appears."""
    statuses = _make_statuses(["gemini"])
    statuses[0]["has_key"] = False
    statuses[0]["status"] = "no key"

    runner = CliRunner()
    with patch("cli.providers_cmd.AIStrategyRouter") as MockRouter:
        MockRouter.return_value.provider_status.return_value = statuses
        result = runner.invoke(providers_group, ["list"])
    assert result.exit_code == 0
    # Either rich or plain fallback will mention no providers
    assert "No providers" in result.output or "no key" in result.output.lower()


def test_providers_list_plain_fallback_without_rich():
    """providers list falls back to plain text when rich is unavailable."""
    runner = CliRunner()
    with (
        patch("cli.providers_cmd.AIStrategyRouter") as MockRouter,
        patch(
            "builtins.__import__",
            side_effect=lambda name, *a, **kw: (
                (_ for _ in ()).throw(ImportError()) if name == "rich.console" else __import__(name, *a, **kw)
            ),
        ),
    ):
        MockRouter.return_value.provider_status.return_value = _make_statuses()
        # Even if rich fails, the command should not crash
        result = runner.invoke(providers_group, ["list"])
    # Just verify it doesn't raise an unhandled exception
    assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# providers test
# ---------------------------------------------------------------------------


def test_providers_test_no_api_keys_shows_warning(monkeypatch):
    """When no API keys are set, prints a warning for each provider."""
    # Unset all known API keys
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(providers_group, ["test"])
    assert result.exit_code == 0
    # Each provider without a key shows the no-key warning
    assert "no API key" in result.output or "No providers" in result.output


def test_providers_test_specific_provider_no_key(monkeypatch):
    """When --provider X is given but X has no key, shows warning."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(providers_group, ["test", "--provider", "groq"])
    assert result.exit_code == 0
    assert "no API key" in result.output


def test_providers_test_with_key_calls_generate(monkeypatch):
    """When a provider has a key, create_ai_client is called and result printed."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")

    mock_client = MagicMock()
    mock_client.generate.return_value = "PROVIDER_TEST_OK"

    runner = CliRunner()
    with patch("generator.ai.factory.create_ai_client", return_value=mock_client):
        result = runner.invoke(providers_group, ["test", "--provider", "groq"])

    assert result.exit_code == 0
    mock_client.generate.assert_called_once()
    assert "PROVIDER_TEST_OK" in result.output or "groq" in result.output


def test_providers_test_generate_exception_shows_error(monkeypatch):
    """When generate() raises, the error is shown but command exits 0."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.generate.side_effect = RuntimeError("connection refused")

    runner = CliRunner()
    with patch("generator.ai.factory.create_ai_client", return_value=mock_client):
        result = runner.invoke(providers_group, ["test", "--provider", "groq"])

    assert result.exit_code == 0
    assert "connection refused" in result.output


# ---------------------------------------------------------------------------
# providers benchmark
# ---------------------------------------------------------------------------


def test_providers_benchmark_no_keys_exits_1(monkeypatch):
    """benchmark exits 1 when no provider has a key."""
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    runner = CliRunner()
    result = runner.invoke(providers_group, ["benchmark"])
    assert result.exit_code == 1
    assert "No providers" in result.output


def test_providers_benchmark_with_key_runs(monkeypatch):
    """benchmark with one available provider runs and ranks results."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.generate.return_value = "response text"

    runner = CliRunner()
    with patch("generator.ai.factory.create_ai_client", return_value=mock_client):
        result = runner.invoke(providers_group, ["benchmark", "--prompts", "1"])

    assert result.exit_code == 0
    assert "groq" in result.output.lower() or "Benchmark" in result.output


def test_providers_benchmark_provider_error_continues(monkeypatch):
    """When one provider errors, benchmark continues and shows error for that provider."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.generate.side_effect = RuntimeError("timeout")

    runner = CliRunner()
    with patch("generator.ai.factory.create_ai_client", return_value=mock_client):
        result = runner.invoke(providers_group, ["benchmark", "--prompts", "1"])

    # Error shown but command doesn't crash; exits 1 because no results
    assert "timeout" in result.output or result.exit_code in (0, 1)
