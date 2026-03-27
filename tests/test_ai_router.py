"""Tests for AIStrategyRouter and related components (Phase 1 Dynamic Router)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from generator.ai.ai_strategy_router import (
    DEFAULT_PREFERRED,
    PROVIDER_ENV_KEYS,
    QUALITY_SCORES,
    SPEED_SCORES,
    AIStrategyRouter,
)
from generator.ai.factory import SUPPORTED_PROVIDERS, create_ai_client


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestFactory:
    """Verify the factory supports all 4 providers."""

    def test_supported_providers_constant(self):
        assert "anthropic" in SUPPORTED_PROVIDERS
        assert "openai" in SUPPORTED_PROVIDERS
        assert "groq" in SUPPORTED_PROVIDERS
        assert "gemini" in SUPPORTED_PROVIDERS

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown AI provider"):
            create_ai_client("foobar")

    def test_anthropic_missing_key_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises((ValueError, ImportError, RuntimeError)):
                create_ai_client("anthropic")

    def test_openai_missing_key_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises((ValueError, ImportError, RuntimeError)):
                create_ai_client("openai")


# ---------------------------------------------------------------------------
# Provider clients — construction with mock API key
# ---------------------------------------------------------------------------


class TestAnthropicClient:
    def test_accepts_explicit_api_key(self):
        from generator.ai.providers.anthropic_client import AnthropicClient

        with patch("generator.ai.providers.anthropic_client._anthropic") as mock_lib:
            mock_lib.Anthropic.return_value = MagicMock()
            client = AnthropicClient(api_key="sk-ant-test-key")
            assert client.api_key == "sk-ant-test-key"

    def test_default_model_set(self):
        from generator.ai.providers.anthropic_client import AnthropicClient

        assert "claude" in AnthropicClient.DEFAULT_MODEL

    def test_generate_calls_messages_create(self):
        from generator.ai.providers.anthropic_client import AnthropicClient

        mock_anthropic = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="Hello from Claude")]
        mock_anthropic.messages.create.return_value = mock_msg

        with patch("generator.ai.providers.anthropic_client._anthropic") as mock_lib:
            mock_lib.Anthropic.return_value = mock_anthropic
            client = AnthropicClient(api_key="sk-ant-fake")
            result = client.generate("test prompt")

        assert "Hello from Claude" in result
        mock_anthropic.messages.create.assert_called_once()


class TestOpenAIClient:
    def test_accepts_explicit_api_key(self):
        from generator.ai.providers.openai_client import OpenAIClient

        with patch("generator.ai.providers.openai_client._OpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = OpenAIClient(api_key="sk-test-openai-key")
            assert client.api_key == "sk-test-openai-key"

    def test_default_model_is_gpt4o_mini(self):
        from generator.ai.providers.openai_client import OpenAIClient

        assert "gpt" in OpenAIClient.DEFAULT_MODEL

    def test_generate_calls_chat_completions(self):
        from generator.ai.providers.openai_client import OpenAIClient

        mock_openai = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello from GPT"
        mock_openai.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        with patch("generator.ai.providers.openai_client._OpenAI") as mock_cls:
            mock_cls.return_value = mock_openai
            client = OpenAIClient(api_key="sk-fake")
            result = client.generate("test prompt")

        assert "Hello from GPT" in result


# ---------------------------------------------------------------------------
# Router ranking
# ---------------------------------------------------------------------------


class TestRouterRanking:
    def test_quality_strategy_ranks_anthropic_first(self):
        router = AIStrategyRouter(strategy="quality")
        ranked = router._get_ranked_providers()
        assert ranked[0] == "anthropic", f"Expected anthropic first, got {ranked}"

    def test_speed_strategy_ranks_groq_first(self):
        router = AIStrategyRouter(strategy="speed")
        ranked = router._get_ranked_providers()
        assert ranked[0] == "groq", f"Expected groq first, got {ranked}"

    def test_provider_override_returns_single_provider(self):
        router = AIStrategyRouter(strategy="provider:openai")
        ranked = router._get_ranked_providers()
        assert ranked == ["openai"]

    def test_auto_uses_quality_as_base(self):
        router = AIStrategyRouter(strategy="auto")
        ranked = router._get_ranked_providers()
        # anthropic should score highest with zero usage count
        assert ranked[0] == "anthropic"

    def test_auto_load_balances_after_usage(self):
        router = AIStrategyRouter(strategy="auto")
        router._usage_counts["anthropic"] = 100  # heavily used
        ranked = router._get_ranked_providers()
        # anthropic should drop in ranking after heavy usage
        assert ranked[0] != "anthropic"

    def test_quality_scores_are_ordered(self):
        assert QUALITY_SCORES["anthropic"] > QUALITY_SCORES["openai"]
        assert QUALITY_SCORES["openai"] > QUALITY_SCORES["gemini"]
        assert QUALITY_SCORES["gemini"] > QUALITY_SCORES["groq"]

    def test_speed_scores_are_ordered(self):
        assert SPEED_SCORES["groq"] > SPEED_SCORES["gemini"]


# ---------------------------------------------------------------------------
# Router smart_generate with fallback
# ---------------------------------------------------------------------------


class TestRouterSmartGenerate:
    def _mock_client(self, content: str = "generated content") -> MagicMock:
        client = MagicMock()
        client.generate.return_value = content
        return client

    def test_returns_content_and_provider_name(self):
        router = AIStrategyRouter(strategy="provider:groq")

        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"}):
            with patch("generator.ai.ai_strategy_router.create_ai_client") as mock_factory:
                mock_client = MagicMock()
                mock_client.generate.return_value = "skill content"
                mock_factory.return_value = mock_client
                content, provider = router.smart_generate("hello", task_type="skills")

        assert content == "skill content"
        assert provider == "groq"

    def test_falls_back_on_provider_failure(self):
        """If first provider fails, router tries next."""
        router = AIStrategyRouter(strategy="quality")  # anthropic → openai → gemini → groq

        call_count = 0

        def _factory(provider: str):
            nonlocal call_count
            call_count += 1
            if provider == "anthropic":
                raise RuntimeError("Anthropic down")
            mock_client = MagicMock()
            mock_client.generate.return_value = f"content from {provider}"
            return mock_client

        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "OPENAI_API_KEY": "sk-test",
        }):
            with patch("generator.ai.ai_strategy_router.create_ai_client", side_effect=_factory):
                content, provider = router.smart_generate("hello", task_type="skills")

        assert provider == "openai"
        assert "openai" in content

    def test_raises_when_all_providers_fail(self):
        router = AIStrategyRouter(strategy="quality")

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with patch("generator.ai.ai_strategy_router.create_ai_client") as mock_factory:
                mock_factory.side_effect = RuntimeError("All down")
                with pytest.raises(RuntimeError, match="All providers failed"):
                    router.smart_generate("hello")

    def test_skips_providers_without_keys(self):
        router = AIStrategyRouter(strategy="quality")

        # Only GROQ_API_KEY present, all others absent
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "GROQ_API_KEY": "gsk_test",
        }):
            with patch("generator.ai.ai_strategy_router.create_ai_client") as mock_factory:
                mock_client = MagicMock()
                mock_client.generate.return_value = "groq result"
                mock_factory.return_value = mock_client
                content, provider = router.smart_generate("hello")

        assert provider == "groq"

    def test_tracks_latency_after_successful_call(self):
        router = AIStrategyRouter(strategy="provider:groq")

        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"}):
            with patch("generator.ai.ai_strategy_router.create_ai_client") as mock_factory:
                mock_client = MagicMock()
                mock_client.generate.return_value = "ok"
                mock_factory.return_value = mock_client
                router.smart_generate("hello")

        assert "groq" in router._latency_cache
        assert router._latency_cache["groq"] >= 0


# ---------------------------------------------------------------------------
# provider_status()
# ---------------------------------------------------------------------------


class TestProviderStatus:
    def test_returns_all_four_providers(self):
        router = AIStrategyRouter()
        statuses = router.provider_status()
        providers = [s["provider"] for s in statuses]
        assert set(providers) == {"anthropic", "groq", "gemini", "openai"}

    def test_ready_when_env_key_set(self):
        router = AIStrategyRouter()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            statuses = {s["provider"]: s for s in router.provider_status()}
        assert statuses["anthropic"]["has_key"] is True
        assert "Ready" in statuses["anthropic"]["status"]

    def test_not_ready_when_no_key(self):
        router = AIStrategyRouter()
        env_without_anthropic = {k: "" for k in ["ANTHROPIC_API_KEY"]}
        with patch.dict(os.environ, env_without_anthropic):
            statuses = {s["provider"]: s for s in router.provider_status()}
        assert statuses["anthropic"]["has_key"] is False


# ---------------------------------------------------------------------------
# LLMSkillGenerator strategy mode
# ---------------------------------------------------------------------------


class TestLLMSkillGeneratorStrategyMode:
    def test_strategy_mode_does_not_create_client(self):
        from generator.llm_skill_generator import LLMSkillGenerator

        gen = LLMSkillGenerator(provider="groq", strategy="auto")
        assert gen.client is None
        assert gen.strategy == "auto"

    def test_direct_mode_has_no_strategy(self):
        from generator.llm_skill_generator import LLMSkillGenerator

        with pytest.raises(RuntimeError):  # GROQ_API_KEY not set → RuntimeError
            gen = LLMSkillGenerator(provider="groq", strategy=None)

    def test_generate_content_uses_router_in_strategy_mode(self):
        from generator.llm_skill_generator import LLMSkillGenerator

        gen = LLMSkillGenerator(provider="groq", strategy="auto")

        # Patch at the point of import inside generate_content
        with patch("generator.ai.ai_strategy_router.AIStrategyRouter") as mock_router_cls:
            mock_router = MagicMock()
            mock_router.smart_generate.return_value = ("router content", "anthropic")
            mock_router_cls.return_value = mock_router
            result = gen.generate_content("test prompt")

        assert result == "router content"
        assert gen.provider == "anthropic"  # updated to the actual provider used
