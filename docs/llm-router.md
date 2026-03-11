# Dynamic AI Router — LLM Provider Guide

PRG v1.4.1 introduces a smart routing layer that selects the best available AI provider automatically, with graceful fallback to the next available one.

---

## Supported Providers

| Provider | Model | Quality | Speed | Env Variable |
|----------|-------|---------|-------|--------------|
| **Anthropic** | claude-3-5-sonnet-20241022 | 95/100 | 65/100 | `ANTHROPIC_API_KEY` |
| **OpenAI** | gpt-4o-mini | 90/100 | 70/100 | `OPENAI_API_KEY` |
| **Gemini** | gemini-2.0-flash | 85/100 | 85/100 | `GEMINI_API_KEY` |
| **Groq** | llama-3.1-8b-instant | 75/100 | 95/100 | `GROQ_API_KEY` |

---

## Quick Setup

Set at least one provider key:

```bash
# .env or shell profile
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
GROQ_API_KEY=gsk_...
```

Check what's ready:

```bash
prg providers list
```

```
╭──────────────────── AI Providers ─────────────────────╮
│ Provider    │ Status    │ Quality  │ Speed  │ Preferred │
│ anthropic   │ ✅ Ready  │ 95/100   │ 65/100 │ ⭐        │
│ groq        │ ✅ Ready  │ 75/100   │ 95/100 │ ⭐        │
│ gemini      │ ❌ No key │ 85/100   │ 85/100 │           │
│ openai      │ ❌ No key │ 90/100   │ 70/100 │           │
╰────────────────────────────────────────────────────────╯
```

---

## Routing Strategies

Pass `--strategy` to `prg analyze` or any AI command:

| Strategy | Ranking | Best for |
|----------|---------|----------|
| `auto` (default) | quality ÷ usage — load-balanced | everyday use |
| `quality` | anthropic → openai → gemini → groq | important skills |
| `speed` | groq → gemini → openai → anthropic | CI/CD, fast iteration |
| `provider:X` | always use provider X | testing / pinning |

```bash
# Use the highest-quality provider you have a key for
prg analyze . --create-skill "dom-manipulation" --ai --strategy quality

# Use the fastest (great for batch generation)
prg analyze . --create-skill "dom-manipulation" --ai --strategy speed

# Pin to a specific provider
prg analyze . --create-skill "dom-manipulation" --ai --strategy provider:anthropic

# Or use --provider directly (shorthand for provider:X)
prg analyze . --create-skill "dom-manipulation" --ai --provider anthropic
```

---

## Fallback Behaviour

If the first provider fails (no key, network error, rate limit), PRG silently tries the next ranked provider:

```
✨ Generating skill with AI (router:quality)...
⚠️  Anthropic failed: rate limit. Trying next provider...
⚠️  OpenAI failed: no key. Trying next provider...
✅ Generated with gemini
```

If **all** providers fail, PRG falls back to README-only skill generation (no LLM needed).

---

## Configuration File

`~/.prg/ai_strategy.yaml` is created automatically on first use:

```yaml
preferred:
  - anthropic
  - groq
  - gemini
  - openai

task_overrides:
  skills: anthropic   # Use anthropic for skill generation
  rules: groq         # Use groq (fast) for rules
```

Customise `preferred` to set your provider priority order. `task_overrides` lets you pin specific task types to specific providers.

---

## API Key Auto-Detection

PRG detects the provider from your API key prefix:

| Key prefix | Detected provider |
|------------|-------------------|
| `sk-ant-...` | anthropic |
| `sk-...` | openai |
| `gsk_...` | groq |
| (none matching) | read env vars |

```bash
# Pass key directly — provider auto-detected
prg analyze . --api-key sk-ant-mykeyhere --create-skill "dom" --ai
```

---

## `prg providers` Commands

### `prg providers list`
Rich table of all 4 providers with status, quality, speed, model, and env variable name.

```bash
prg providers list
```

### `prg providers test`
Send a test prompt to verify connectivity and measure latency.

```bash
prg providers test               # Test all providers with keys
prg providers test --provider groq  # Test a specific provider
```

### `prg providers benchmark`
Run 3 standard prompts, measure average latency, and rank by composite score (quality/latency).

```bash
prg providers benchmark            # 3 prompts (default)
prg providers benchmark --prompts 5  # More prompts for accuracy
```

Output:
```
╭─────────── Provider Benchmark Results ───────────╮
│ Rank │ Provider  │ Avg Latency │ Quality │ Speed  │ Composite ↑ │
│ 1    │ groq      │ 0.34s       │ 75      │ 95     │ 220.6       │
│ 2    │ anthropic │ 1.82s       │ 95      │ 65     │ 52.2        │
╰──────────────────────────────────────────────────╯
🏆 Recommended: groq
```

---

## Architecture

```
prg analyze . --ai --strategy quality
        │
        ▼
  AIStrategyRouter (strategy="quality")
        │
        ├── 1. anthropic  ✅ key set → try
        │        └── RuntimeError (rate limit)
        ├── 2. openai     ❌ no key → skip
        ├── 3. gemini     ✅ key set → try
        │        └── SUCCESS → return content
        └── (groq never reached)
```

Router lives in `generator/ai/ai_strategy_router.py`.
Clients in `generator/ai/providers/{anthropic,openai,groq,gemini}_client.py`.

---

## Extending with a New Provider

1. Add `my_provider_client.py` in `generator/ai/providers/`, subclassing `AIClient`
2. Register it in `generator/ai/factory.py`
3. Add quality/speed scores to `QUALITY_SCORES`/`SPEED_SCORES` in `ai_strategy_router.py`
4. Add its env key to `PROVIDER_ENV_KEYS`
5. Write tests in `tests/test_ai_router.py` following the existing pattern
