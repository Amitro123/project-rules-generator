---
name: exception-narrower
description: >-
  Use when user mentions "broad exception", "except Exception", "narrow catch",
  "exception handling", "failure masking", "swallowing errors", "catch-all".
  Do NOT activate for "try-except tutorial" or general Python questions.
allowed-tools:
  - Read
  - Edit
  - Grep
  - Bash
metadata:
  tags: [exception-handling, robustness, debugging, code-quality]
  priority: High
---

# Skill: Exception Narrower

## Purpose

Find and narrow over-broad `except Exception` blocks that mask real defects.
This pattern appears frequently in AI/provider code but spreads into core logic,
making debugging opaque. Replace blanket catches with specific, recoverable ones.

## CRITICAL

- Never remove exception handling at system boundaries (API calls, file I/O, subprocess)
- Never narrow exceptions in code paths that MUST NOT crash (final fallback, cleanup)
- Always add a comment explaining WHY a broad catch is intentional when kept

## Auto-Trigger

Activate when user asks to:
- "find all broad exception handlers"
- "narrow catch-all blocks"
- "stop swallowing exceptions"
- "make failures more visible"

## Process

### 1. Find all broad exception catches

```bash
# Find every broad except block
grep -rn "except Exception\|except BaseException\|except:\b" generator/ cli/ prg_utils/ \
    --include="*.py" | grep -v "# noqa\|# pragma"
```

### 2. Classify each catch block

For each match, classify into one of:
- **KEEP BROAD** — true system boundary: subprocess, network, file I/O in fallback paths
- **NARROW** — internal logic that should surface its real error type
- **DOCUMENT** — broad but justified (add `# noqa: BLE001 — <reason>` comment)

### 3. Narrow internal catches

```python
# BEFORE (masks real defects):
try:
    subtasks = decomposer.decompose(description, ...)
except Exception as exc:
    logger.warning("Failed: %s", exc)
    return []

# AFTER (surfaces real types):
try:
    subtasks = decomposer.decompose(description, ...)
except (ValueError, KeyError) as exc:
    logger.warning("Invalid input for decompose: %s", exc)
    return []
except (OSError, TimeoutError) as exc:
    logger.warning("I/O error during decompose: %s", exc)
    return []
# Let unexpected exceptions propagate — they are bugs
```

### 4. Handle AI/provider boundaries correctly

At true system boundaries (LLM API calls), broad catches ARE appropriate:
```python
# CORRECT — provider API can raise many unpredictable exceptions
try:
    response = self.client.generate(prompt, ...)
except Exception as exc:  # noqa: BLE001 — LLM providers raise diverse errors
    logger.warning("AI generation failed: %s. Falling back.", exc)
    return self._generate_template(...)
```

### 5. Verify after narrowing

```bash
pytest tests/ -x -q
# Run specific test that exercises the narrowed path
pytest tests/ -k "test_decompose or test_generate" -v
```

## Output

- Grep report of all broad catches with classification
- Narrowed exception types in internal logic paths
- Preserved (and documented) broad catches at system boundaries
- All tests still pass

## Anti-Patterns

❌ Narrowing exceptions at LLM API call sites (providers are unpredictable)
✅ Keep `except Exception` at provider/subprocess boundaries, narrow everything else

❌ Adding `except (ValueError, KeyError, TypeError, RuntimeError, ...)` — still too broad
✅ Add exactly the exceptions that YOUR code expects and can recover from

❌ Removing try/except entirely from fallback paths
✅ Keep safety nets at system edges, just make them more specific internally
