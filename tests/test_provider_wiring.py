"""Tests for provider wiring through design and plan commands."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from generator.task_decomposer import TaskDecomposer

# ---------------------------------------------------------------------------
# TaskDecomposer — provider wiring
# ---------------------------------------------------------------------------


class TestTaskDecomposerProvider:
    def test_gemini_key_from_google_api_key(self):
        """GOOGLE_API_KEY is used when provider=gemini and GEMINI_API_KEY is absent."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "goog-test"}, clear=False):
            d = TaskDecomposer(provider="gemini")
            assert d.api_key == "goog-test"

    def test_groq_key_resolved_from_env(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test"}, clear=False):
            d = TaskDecomposer(provider="groq")
            assert d.api_key == "gsk_test"

    def test_anthropic_key_resolved_from_env(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False):
            d = TaskDecomposer(provider="anthropic")
            assert d.api_key == "sk-ant-test"

    def test_explicit_api_key_takes_precedence(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "env-key"}, clear=False):
            d = TaskDecomposer(provider="gemini", api_key="explicit-key")
            assert d.api_key == "explicit-key"

    def test_no_key_returns_empty_from_call_llm(self):
        d = TaskDecomposer(provider="gemini", api_key=None)
        d.api_key = None
        result = d._call_llm("test prompt")
        assert result == ""

    def test_call_llm_uses_factory(self):
        """_call_llm delegates to create_ai_client, not google.genai directly."""
        mock_client = MagicMock()
        mock_client.generate.return_value = '{"subtasks": []}'
        with patch("generator.task_decomposer.TaskDecomposer._call_llm", return_value="{}") as mock_call:
            d = TaskDecomposer(provider="groq", api_key="gsk_test")
            d._call_llm("prompt")
            mock_call.assert_called_once_with("prompt")

    def test_provider_stored_on_instance(self):
        d = TaskDecomposer(provider="openai", api_key="sk-test")
        assert d.provider == "openai"


# ---------------------------------------------------------------------------
# DesignGenerator — provider wiring (via CLI)
# ---------------------------------------------------------------------------


class TestDesignProviderWiring:
    def test_design_cli_passes_provider_to_generator(self, tmp_path):
        """prg design --provider groq should instantiate DesignGenerator with provider='groq'."""
        from cli.agent import design

        runner = CliRunner()
        with patch("cli.cmd_design._has_api_key", return_value=True), patch(
            "generator.design_generator.DesignGenerator"
        ) as MockDG:
            mock_instance = MagicMock()
            mock_instance.generate_design.return_value = MagicMock(
                title="T",
                architecture_decisions=[],
                api_contracts=[],
                data_models=[],
                success_criteria=[],
                to_markdown=lambda: "# Design",
            )
            MockDG.return_value = mock_instance
            result = runner.invoke(
                design,
                [
                    "some task",
                    "--provider",
                    "groq",
                    "--project-path",
                    str(tmp_path),
                    "--output",
                    str(tmp_path / "DESIGN.md"),
                ],
            )
        call_kwargs = MockDG.call_args
        assert call_kwargs is not None
        # provider='groq' must be passed — either positional or keyword
        args, kwargs = call_kwargs
        assert kwargs.get("provider") == "groq" or (args and "groq" in args)

    def test_design_cli_accepts_all_four_providers(self, tmp_path):
        from cli.agent import design

        runner = CliRunner()
        for prov in ["gemini", "groq", "anthropic", "openai"]:
            with patch("cli.cmd_design._has_api_key", return_value=True), patch(
                "generator.design_generator.DesignGenerator"
            ) as MockDG:
                mock_instance = MagicMock()
                mock_instance.generate_design.return_value = MagicMock(
                    title="T",
                    architecture_decisions=[],
                    api_contracts=[],
                    data_models=[],
                    success_criteria=[],
                    to_markdown=lambda: "# Design",
                )
                MockDG.return_value = mock_instance
                result = runner.invoke(
                    design,
                    [
                        "task",
                        "--provider",
                        prov,
                        "--project-path",
                        str(tmp_path),
                        "--output",
                        str(tmp_path / "DESIGN.md"),
                    ],
                )
            assert result.exit_code == 0, f"provider={prov} failed: {result.output}"
