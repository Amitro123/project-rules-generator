"""Regression tests for Claude code-review fixes (CR score: 6.2 → 8.0).

Covers:
  1. detect_provider() returns None when no keys present
  2. detect_provider() priority ordering (no priority inversion)
  3. `prg review` exits cleanly (no traceback) when no provider is available
  4. _extract_features() fallback path doesn't truncate mid-word
  5. AgentExecutor.match_skill() produces no print() output
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cli.utils import detect_provider
from generator.analyzers.readme_parser import _extract_features
from generator.planning.agent_executor import AgentExecutor


# ---------------------------------------------------------------------------
# Fix 1 & 2 — detect_provider() correctness
# ---------------------------------------------------------------------------


class TestDetectProvider:
    def test_returns_none_when_no_keys_in_env(self):
        """detect_provider must return None when no API keys are set at all."""
        clean_env = {
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
        }
        with patch.dict(os.environ, clean_env, clear=False):
            # Force empty so 'os.environ.get' returns falsy
            for k in clean_env:
                os.environ.pop(k, None)
            result = detect_provider(None, None)
        assert result is None, f"Expected None but got {result!r}"

    def test_explicit_provider_flag_takes_precedence(self):
        """An explicit --provider flag is always returned as-is."""
        assert detect_provider("anthropic", None) == "anthropic"
        assert detect_provider("gemini", "gsk_somethign") == "gemini"

    def test_api_key_prefix_groq(self):
        assert detect_provider(None, "gsk_abc") == "groq"

    def test_api_key_prefix_anthropic(self):
        assert detect_provider(None, "sk-ant-abc") == "anthropic"

    def test_api_key_prefix_openai(self):
        assert detect_provider(None, "sk-abc") == "openai"

    def test_groq_env_preferred_over_gemini(self):
        """When both GROQ_API_KEY and GEMINI_API_KEY are set, GROQ is returned (first in priority)."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test", "GEMINI_API_KEY": "gai_test"}, clear=False):
            result = detect_provider(None, None)
        assert result == "groq"

    def test_gemini_returned_when_only_gemini_set(self):
        """GEMINI_API_KEY is picked up when no other key is present."""
        env = {
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
        }
        with patch.dict(os.environ, {**env, "GEMINI_API_KEY": "gai_test"}, clear=False):
            for k in env:
                os.environ.pop(k, None)
            result = detect_provider(None, None)
        assert result == "gemini"


# ---------------------------------------------------------------------------
# Fix 3 — prg review exits cleanly with no provider
# ---------------------------------------------------------------------------


class TestReviewNoneProviderGuard:
    def test_review_cmd_exits_with_error_when_no_keys(self, tmp_path):
        """prg review should exit non-zero with a helpful message, not a traceback."""
        from cli.cmd_review import review

        # Create a dummy file to review
        dummy = tmp_path / "rules.md"
        dummy.write_text("# Rules\n\nSome rules here.")

        runner = CliRunner()
        clean_env = {
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
        }
        with runner.isolated_filesystem():
            for k in clean_env:
                os.environ.pop(k, None)
            result = runner.invoke(
                review,
                [str(dummy), "--project-path", str(tmp_path)],
                catch_exceptions=False,
                env=clean_env,
            )

        assert result.exit_code != 0
        # Should mention "No AI provider" or similar — no ImportError traceback
        combined = (result.output or "") + (result.stderr if hasattr(result, "stderr") else "")
        assert "ImportError" not in combined
        assert "No AI provider" in combined or "api key" in combined.lower()


# ---------------------------------------------------------------------------
# Fix 4 — _extract_features fallback doesn't truncate mid-word
# ---------------------------------------------------------------------------


class TestExtractFeaturesTruncation:
    def test_no_mid_word_truncation_when_stack_near_midpoint(self):
        """
        When no Features section exists and the fallback path is taken, the
        content slice must snap to a newline so 'React 18, TypeScript' is never
        split to 'React 18, Typ'.
        """
        # Build a README where the interesting content sits just past the half-way mark
        intro = "# My App\n\nA short description.\n\n"
        padding = "Some intro text.\n" * 30  # push midpoint before Stack section
        stack = "## Stack\n\n- React 18, TypeScript, TailwindCSS\n- FastAPI\n- PostgreSQL\n"
        content = intro + padding + stack

        features = _extract_features(content)
        # Either we get features from the stack section, or the list is just empty
        # but we must NOT get a truncated item like "React 18, Typ"
        for feat in features:
            assert feat == feat.rstrip(), "Trailing whitespace in feature"
            # No feature should be a broken prefix of "React 18, TypeScript"
            if "React 18" in feat:
                assert "TypeScript" in feat, f"Feature appears truncated: {feat!r}"

    def test_short_readme_features_not_empty(self):
        """List items in the first half of a README should still be extracted."""
        # Make sure the list items appear before the midpoint
        content = (
            "# Project\n\n"
            "A description.\n\n"
            "- Feature A\n- Feature B\n- Feature C\n\n"
            + "End section.\n" * 20  # push midpoint after the list
        )
        features = _extract_features(content)
        assert len(features) > 0


# ---------------------------------------------------------------------------
# Fix 5 — AgentExecutor no longer produces print() output
# ---------------------------------------------------------------------------


class TestAgentExecutorNoPrints:
    def test_match_skill_no_debug_prints_when_no_triggers(self, tmp_path):
        """match_skill() must not call print() — debug output should use logger.debug()."""
        executor = AgentExecutor(project_path=tmp_path)

        with patch("builtins.print") as mock_print:
            result = executor.match_skill("fix a bug in auth module")

        mock_print.assert_not_called()
        assert result is None  # no triggers loaded

    def test_match_skill_no_debug_prints_with_triggers(self, tmp_path):
        """Even when triggers ARE loaded and matching runs, no print() calls occur."""
        triggers_dir = tmp_path / ".clinerules"
        triggers_dir.mkdir()
        triggers_file = triggers_dir / "auto-triggers.json"
        triggers_file.write_text('{"fix-bug": ["fix a bug", "there is a bug"]}', encoding="utf-8")

        executor = AgentExecutor(project_path=tmp_path)

        with patch("builtins.print") as mock_print:
            executor.match_skill("fix a bug in auth module")

        mock_print.assert_not_called()
