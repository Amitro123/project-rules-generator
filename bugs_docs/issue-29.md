# Regression: fresh-install test suite still has 9 failures (AI provider clients, AIStrategy kwarg mismatch, trigger parser drift)

**Issue:** [#29](https://github.com/Amitro123/project-rules-generator/issues/29)
**Author:** Amitro123
**State:** open
**Labels:** bug, code-review

---

## Summary

After a fresh clone and editable install (`pip install -e .`), the test suite does **not** pass cleanly.

Observed result on current `main` (`6272d195298574c78cd55f0b83ed395f5dd8a3a3`):
- `503 passed`
- `9 failed`
- `11 skipped`

## Reproduction

```bash
git clone https://github.com/Amitro123/project-rules-generator.git
cd project-rules-generator
pip install -e .
pytest -q
```

## Failures grouped by root cause

### 1) AI provider clients are hard-gated by import-time availability flags
Files:
- `generator/ai/providers/anthropic_client.py`
- `generator/ai/providers/openai_client.py`
- `generator/ai/providers/gemini_client.py`

Symptoms:
- `TestAnthropicClient::test_accepts_explicit_api_key`
- `TestAnthropicClient::test_generate_calls_messages_create`
- `TestOpenAIClient::test_accepts_explicit_api_key`
- `TestOpenAIClient::test_generate_calls_chat_completions`
- `TestEncodingFix::test_gemini_client_encoding_fix`

Problem:
- The modules set `ANTHROPIC_AVAILABLE` / `OPENAI_AVAILABLE` / `GEMINI_AVAILABLE` at import time.
- Constructors immediately raise if the optional package is absent, even when tests patch `_anthropic`, `_OpenAI`, or `genai.Client`.
- For Gemini, when import fails, `genai = None`, so patching `generator.ai.providers.gemini_client.genai.Client` crashes before the actual test logic runs.

Why this matters:
- Optional providers become hard to mock and hard to test.
- Fresh-install CI is brittle unless every optional SDK is installed.

Suggested fix:
- Avoid module-level availability flags as the sole gate.
- Defer the import/constructor check until instantiation and/or use the patched symbol directly.
- Consider treating Anthropic/OpenAI/Gemini as optional extras and making the tests resilient to their absence.

---

### 2) `SkillGenerator._run_strategy_chain()` passes an unsupported `use_ai` kwarg into `AIStrategy.generate()`
Files:
- `generator/skill_generator.py`
- `generator/strategies/ai_strategy.py`

Symptoms:
- `TestAISkillGeneration::test_create_skill_with_ai`
- `TestAISkillGeneration::test_create_skill_ai_missing_dependency`
- `TestAISkillGeneration::test_create_skill_ai_failure_fallback`

Current behavior:
- `SkillGenerator._run_strategy_chain()` calls:
  ```python
  strategy_obj.generate(..., strategy=strategy, use_ai=use_ai)
  ```
  for non-Cowork strategies.
- `AIStrategy.generate()` signature does **not** accept `use_ai`.
- Result: `TypeError: AIStrategy.generate() got an unexpected keyword argument 'use_ai'`

Impact:
- The AI skill-generation path is broken before any provider fallback can happen.
- The intended graceful fallback behavior never executes.

Suggested fix:
- Make strategy method signatures consistent across all strategy classes, or
- Branch explicitly when calling `AIStrategy`, or
- Accept `**kwargs` in `AIStrategy.generate()` and ignore unsupported extras.

---

### 3) `extract_auto_triggers()` no longer satisfies existing expected behavior
File:
- `generator/analyzers/readme_parser.py`

Symptom:
- `tests/test_smart_parser.py::test_extract_auto_triggers`

Observed mismatch:
- The test expects: `Working in backend code: *.py`
- Current implementation intentionally removed generic backend/frontend triggers and now returns only skill-name phrases plus domain-specific explicit-glob triggers.

This is either:
- a real regression in behavior, or
- an outdated test after a behavior change.

Suggested fix:
- Decide the intended contract and align code + tests.
- If the new behavior is correct, update the test suite/documentation.
- If backward compatibility matters, restore the expected generic trigger(s).

## Additional note

README currently advertises `Tests: 465 Passing`, but a fresh editable install on current `main` produces 9 failures. It may be worth updating the badge/claim once the suite status is reconciled.

## Expected outcome

A fresh-clone path should ideally succeed with:

```bash
pip install -e .
pytest -q
```

without requiring users to guess extra optional SDK installs or hit broken AI skill-generation flow.
