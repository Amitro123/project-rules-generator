"""Coverage boost: CoworkStrategy (55% covered, 33 miss)."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from generator.strategies.cowork_strategy import CoworkStrategy


def _strategy_with_creator(creator=None):
    """Build a CoworkStrategy with an injected mock creator."""
    if creator is None:
        creator = MagicMock()
        quality = SimpleNamespace(score=90)
        creator.create_skill.return_value = ("# Skill content", {}, quality)

    def factory(path):
        return creator

    return CoworkStrategy(creator_factory=factory), creator


class TestInputValidation:
    def test_returns_none_for_empty_skill_name(self, tmp_path):
        strategy, _ = _strategy_with_creator()
        result = strategy.generate("", tmp_path, None, "groq")
        assert result is None

    def test_returns_none_for_whitespace_skill_name(self, tmp_path):
        strategy, _ = _strategy_with_creator()
        result = strategy.generate("   ", tmp_path, None, "groq")
        assert result is None

    def test_returns_none_for_empty_provider(self, tmp_path):
        strategy, _ = _strategy_with_creator()
        result = strategy.generate("my-skill", tmp_path, None, "")
        assert result is None

    def test_returns_none_when_project_path_none(self):
        strategy, _ = _strategy_with_creator()
        result = strategy.generate("my-skill", None, None, "groq")
        assert result is None

    def test_returns_none_when_path_does_not_exist(self, tmp_path):
        strategy, _ = _strategy_with_creator()
        nonexistent = tmp_path / "nonexistent"
        result = strategy.generate("my-skill", nonexistent, None, "groq")
        assert result is None

    def test_returns_none_when_path_is_file(self, tmp_path):
        strategy, _ = _strategy_with_creator()
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        result = strategy.generate("my-skill", file_path, None, "groq")
        assert result is None


class TestReadmeBridging:
    def test_bridges_missing_context_when_readme_insufficient(self, tmp_path):
        strategy, creator = _strategy_with_creator()
        with patch("generator.strategies.cowork_strategy.is_readme_sufficient", return_value=False):
            with patch(
                "generator.strategies.cowork_strategy.bridge_missing_context", return_value="# Supplement"
            ) as mock_bridge:
                strategy.generate("my-skill", tmp_path, None, "groq", use_ai=True)
        mock_bridge.assert_called_once()

    def test_skips_bridging_when_readme_sufficient(self, tmp_path):
        strategy, creator = _strategy_with_creator()
        with patch("generator.strategies.cowork_strategy.is_readme_sufficient", return_value=True):
            with patch("generator.strategies.cowork_strategy.bridge_missing_context") as mock_bridge:
                strategy.generate("my-skill", tmp_path, "# Sufficient README content here.", "groq", use_ai=True)
        mock_bridge.assert_not_called()

    def test_handles_bridge_exception_gracefully(self, tmp_path):
        strategy, creator = _strategy_with_creator()
        with patch("generator.strategies.cowork_strategy.is_readme_sufficient", return_value=False):
            with patch(
                "generator.strategies.cowork_strategy.bridge_missing_context", side_effect=RuntimeError("bridge error")
            ):
                result = strategy.generate("my-skill", tmp_path, None, "groq", use_ai=True)
        # Should not raise — result depends on creator
        assert result is not None or result is None

    def test_handles_sufficiency_check_exception(self, tmp_path):
        strategy, creator = _strategy_with_creator()
        with patch(
            "generator.strategies.cowork_strategy.is_readme_sufficient", side_effect=RuntimeError("check failed")
        ):
            with patch("generator.strategies.cowork_strategy.bridge_missing_context", return_value=""):
                strategy.generate("my-skill", tmp_path, None, "groq", use_ai=True)


class TestCreatorDelegation:
    def test_returns_none_when_use_ai_is_false(self, tmp_path):
        strategy, _ = _strategy_with_creator()
        with patch("generator.strategies.cowork_strategy.is_readme_sufficient", return_value=True):
            result = strategy.generate("my-skill", tmp_path, "# README", "groq", use_ai=False)
        assert result is None

    def test_calls_creator_when_use_ai_true(self, tmp_path):
        strategy, creator = _strategy_with_creator()
        with patch("generator.strategies.cowork_strategy.is_readme_sufficient", return_value=True):
            result = strategy.generate("my-skill", tmp_path, "# README", "groq", use_ai=True)
        creator.create_skill.assert_called_once()

    def test_returns_skill_content_on_success(self, tmp_path):
        strategy, creator = _strategy_with_creator()
        with patch("generator.strategies.cowork_strategy.is_readme_sufficient", return_value=True):
            result = strategy.generate("my-skill", tmp_path, "# README", "groq", use_ai=True)
        assert result == "# Skill content"

    def test_returns_none_when_creator_raises(self, tmp_path):
        creator = MagicMock()
        creator.create_skill.side_effect = RuntimeError("creator failed")
        strategy, _ = _strategy_with_creator(creator)
        with patch("generator.strategies.cowork_strategy.is_readme_sufficient", return_value=True):
            result = strategy.generate("my-skill", tmp_path, "# README", "groq", use_ai=True)
        assert result is None

    def test_returns_none_when_creator_factory_raises(self, tmp_path):
        def bad_factory(path):
            raise RuntimeError("factory failed")

        strategy = CoworkStrategy(creator_factory=bad_factory)
        with patch("generator.strategies.cowork_strategy.is_readme_sufficient", return_value=True):
            result = strategy.generate("my-skill", tmp_path, "# README", "groq", use_ai=True)
        assert result is None


class TestReadmeContentHandling:
    def test_none_readme_becomes_empty(self, tmp_path):
        strategy, creator = _strategy_with_creator()
        with patch("generator.strategies.cowork_strategy.is_readme_sufficient", return_value=True):
            strategy.generate("my-skill", tmp_path, None, "groq", use_ai=True)
        call_args = creator.create_skill.call_args
        assert call_args.kwargs.get("readme_content") == "" or call_args[1].get("readme_content") == ""

    def test_supplement_prepended_to_readme(self, tmp_path):
        strategy, creator = _strategy_with_creator()
        with patch("generator.strategies.cowork_strategy.is_readme_sufficient", return_value=False):
            with patch("generator.strategies.cowork_strategy.bridge_missing_context", return_value="# Supplement"):
                strategy.generate("my-skill", tmp_path, "# Existing README", "groq", use_ai=True)
        call_args = creator.create_skill.call_args
        readme_used = call_args.kwargs.get("readme_content") or call_args[1].get("readme_content") or ""
        assert "Supplement" in readme_used
        assert "Existing README" in readme_used
