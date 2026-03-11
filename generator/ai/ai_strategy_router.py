"""Dynamic AI Strategy Router — smart multi-provider selection for PRG.

Usage::

    router = AIStrategyRouter(strategy="auto")
    content, provider = router.smart_generate(prompt, task_type="skills")

Strategy values:
    auto             — quality/usage composite (auto load-balance)
    speed            — fastest provider first
    quality          — highest-quality provider first
    provider:<name>  — force a specific provider (e.g. "provider:anthropic")
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from generator.ai.factory import create_ai_client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

STRATEGY_CONFIG_PATH = Path.home() / ".prg" / "ai_strategy.yaml"

DEFAULT_PREFERRED: List[str] = ["anthropic", "groq", "gemini", "openai"]

# Intrinsic quality rankings (0-100)
QUALITY_SCORES: Dict[str, int] = {
    "anthropic": 95,   # Claude 3.5 Sonnet — best reasoning
    "openai": 90,      # GPT-4o-mini — strong general purpose
    "gemini": 85,      # Gemini 2.0 Flash — fast & capable
    "groq": 75,        # Llama 3.1 — fastest inference, lower quality
}

# Intrinsic speed rankings (0-100, higher = faster)
SPEED_SCORES: Dict[str, int] = {
    "groq": 95,        # Hardware-optimised inference
    "gemini": 85,
    "openai": 70,
    "anthropic": 65,   # Slower but thorough
}

# Environment variable names for each provider
PROVIDER_ENV_KEYS: Dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
}

# Default models
PROVIDER_DEFAULT_MODELS: Dict[str, str] = {
    "anthropic": "claude-3-5-sonnet-20241022",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "groq": "llama-3.1-8b-instant",
}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class AIStrategyRouter:
    """Smart router that selects the best available AI provider.

    Args:
        strategy: Routing strategy — "auto", "speed", "quality",
                  or "provider:<name>" to force a specific provider.
    """

    def __init__(self, strategy: str = "auto") -> None:
        self.strategy = strategy
        self.config: Dict = self._load_config()
        self._usage_counts: Dict[str, int] = {}
        self._latency_cache: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _load_config(self) -> Dict:
        """Load ~/.prg/ai_strategy.yaml, creating defaults if absent."""
        if STRATEGY_CONFIG_PATH.exists():
            try:
                return yaml.safe_load(STRATEGY_CONFIG_PATH.read_text(encoding="utf-8")) or {}
            except Exception:
                pass
        # Write default config on first use
        self._write_default_config()
        return {"preferred": DEFAULT_PREFERRED}

    @staticmethod
    def _write_default_config() -> None:
        """Write default ~/.prg/ai_strategy.yaml if it doesn't exist."""
        try:
            STRATEGY_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not STRATEGY_CONFIG_PATH.exists():
                default = {
                    "preferred": DEFAULT_PREFERRED,
                    "task_overrides": {
                        "skills": "anthropic",
                        "rules": "groq",
                    },
                }
                STRATEGY_CONFIG_PATH.write_text(
                    yaml.dump(default, default_flow_style=False), encoding="utf-8"
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Provider ranking
    # ------------------------------------------------------------------

    def _get_ranked_providers(self, task_type: str = "skills") -> List[str]:
        """Return providers in priority order for the current strategy."""
        # 1. Explicit provider override
        if self.strategy.startswith("provider:"):
            forced = self.strategy.split(":", 1)[1].strip()
            return [forced]

        # 2. Task-specific override from config
        task_override: Optional[str] = (
            self.config.get("task_overrides", {}).get(task_type)
        )
        if task_override:
            preferred = [task_override] + [
                p for p in self.config.get("preferred", DEFAULT_PREFERRED)
                if p != task_override
            ]
        else:
            preferred = self.config.get("preferred", DEFAULT_PREFERRED)

        # 3. Sort by strategy
        if self.strategy == "speed":
            return sorted(preferred, key=lambda p: -SPEED_SCORES.get(p, 50))
        elif self.strategy == "quality":
            return sorted(preferred, key=lambda p: -QUALITY_SCORES.get(p, 50))
        else:
            # auto: quality / usage_count → load-balances among available providers
            def _auto_score(p: str) -> float:
                return QUALITY_SCORES.get(p, 50) / (self._usage_counts.get(p, 0) + 1)

            return sorted(preferred, key=lambda p: -_auto_score(p))

    def _available_providers(self, candidates: List[str]) -> List[str]:
        """Filter to providers that have an API key set."""
        return [
            p for p in candidates
            if os.getenv(PROVIDER_ENV_KEYS.get(p, f"{p.upper()}_API_KEY"))
        ]

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def smart_generate(
        self,
        prompt: str,
        task_type: str = "skills",
        max_tokens: int = 2000,
    ) -> Tuple[str, str]:
        """Try providers in ranked order; return ``(content, provider_used)``.

        Falls back to the next provider on any error (missing key, network, etc.).

        Raises:
            RuntimeError: If ALL providers fail (with aggregated error messages).
        """
        ranked = self._get_ranked_providers(task_type)
        errors: List[str] = []

        for provider in ranked:
            env_key = PROVIDER_ENV_KEYS.get(provider, f"{provider.upper()}_API_KEY")
            if not os.getenv(env_key):
                errors.append(f"{provider}: no API key ({env_key} not set)")
                continue

            try:
                t0 = time.perf_counter()
                client = create_ai_client(provider)
                result = client.generate(prompt, max_tokens=max_tokens)
                self._latency_cache[provider] = time.perf_counter() - t0
                self._usage_counts[provider] = self._usage_counts.get(provider, 0) + 1
                return result, provider
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                continue

        raise RuntimeError(
            f"All providers failed for task_type={task_type!r}:\n"
            + "\n".join(f"  • {e}" for e in errors)
        )

    # ------------------------------------------------------------------
    # Status / reporting
    # ------------------------------------------------------------------

    def provider_status(self) -> List[Dict]:
        """Return a list of status dicts for all known providers.

        Used by ``prg providers list`` to populate the Rich table.
        """
        statuses = []
        preferred = self.config.get("preferred", DEFAULT_PREFERRED)

        for provider in ["anthropic", "groq", "gemini", "openai"]:
            env_key = PROVIDER_ENV_KEYS.get(provider, f"{provider.upper()}_API_KEY")
            has_key = bool(os.getenv(env_key))

            statuses.append(
                {
                    "provider": provider,
                    "status": "✅ Ready" if has_key else "❌ No key",
                    "has_key": has_key,
                    "env_key": env_key,
                    "quality": QUALITY_SCORES.get(provider, 0),
                    "speed": SPEED_SCORES.get(provider, 0),
                    "default_model": PROVIDER_DEFAULT_MODELS.get(provider, "unknown"),
                    "latency": (
                        f"{self._latency_cache[provider]:.2f}s"
                        if provider in self._latency_cache
                        else "—"
                    ),
                    "preferred": provider in preferred,
                }
            )

        return statuses
