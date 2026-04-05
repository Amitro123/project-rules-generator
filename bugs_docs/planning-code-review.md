# Code Review: `generator/planning/`

> Reviewed: 2026-04-05
> Reviewer: Claude Code (code-reviewer agent)
> Scope: All 10 `.py` files in `generator/planning/`

---

## Summary

| Severity | Count | Verdict |
|----------|-------|---------|
| CRITICAL | 0     | ✅ Pass |
| HIGH     | 4     | ⚠️ Fix before merge |
| MEDIUM   | 6     | ℹ️ Address in next pass |
| LOW      | 4     | 📝 Nice to have |

No security vulnerabilities found. Path sanitization in `task_agent.py` is solid; API keys come from env vars only. The 4 HIGH issues should be resolved before the next release.

---

## HIGH Issues

### [HIGH-1] Cross-boundary private method access ✅ 2026-04-05
**File:** `workflow.py`, lines 104, 173–174
**Issue:** `AgentWorkflow._find_or_create_plan()` calls `checker._find_plan_file()` (private on `PreflightChecker`). `_parse_plan_subtasks()` calls `decomposer._parse_response()` (private on `TaskDecomposer`). Private methods are implementation details — they can change without notice, breaking this code silently.
**Fix:**
- Promote `_find_plan_file` → `find_plan_file()` on `PreflightChecker`
- Extract `_parse_response` as a `@staticmethod` or standalone function so no instantiation is needed
**Resolution:** `PreflightChecker._find_plan_file` promoted to `find_plan_file()`. `TaskDecomposer.parse_response()` added as a `@classmethod`; `_parse_plan_subtasks` now calls it directly with no dummy instantiation.

---

### [HIGH-2] 7 bare `except Exception` without annotation ✅ 2026-04-05
**Files:**
- `workflow.py`: lines 206, 234, 246
- `self_reviewer.py`: line 99
- `agent_executor.py`: lines 126, 194
- `project_manager.py`: line 144

**Issue:** Project convention (evidenced in `project_planner.py:193`) is to annotate intentional broad catches with `# noqa: BLE001`. These 7 locations omit it, making the broad catch ambiguous. Some (e.g. `agent_executor.py:126` loading JSON) could mask real bugs by swallowing `TypeError` or `KeyError`.
**Fix:** Either narrow to specific types (`json.JSONDecodeError`, `OSError`, `ImportError`) or add `# noqa: BLE001` with a comment explaining why the broad catch is intentional.
**Resolution:** `agent_executor.py:126` narrowed to `(OSError, json.JSONDecodeError, ValueError)`. All other 6 annotated with `# noqa: BLE001` and explanatory comment.

---

### [HIGH-3] `assert` used as control flow in production code ✅ 2026-04-05
**Files:**
- `project_planner.py`: lines 439, 447
- `plan_parser.py`: lines 192, 205

**Issue:** These `assert` statements guard regex match results. Running with `python -O` strips all asserts — `match.group()` on `None` then raises `AttributeError`. This is production parsing code, not test code.
**Fix:** Replace with explicit guards:
```python
# Instead of: assert match
if match is None:
    continue
```
**Resolution:** All 4 `assert match is not None` replaced with `if match is None: continue`.

---

### [HIGH-4] f-strings in logger calls (8 occurrences) ✅ 2026-04-05
**File:** `workflow.py`, lines 68, 71, 72, 108, 137, 148, 163, 233
**Issue:** `logger.info(f"...")` defeats lazy evaluation — the string is always formatted even when the log level is disabled. The rest of the codebase correctly uses `logger.info("...", var)` style (e.g. `project_manager.py`, `agent_executor.py`).
**Fix:** Convert all f-string logger calls to `%s` format:
```python
# Before
logger.info(f"Running plan for {feature_id}")
# After
logger.info("Running plan for %s", feature_id)
```
**Resolution:** All 8 f-string logger calls in `workflow.py` converted to `%s` format args.

---

## MEDIUM Issues

### [MEDIUM-1] `project_planner.py` is a god class (559 lines)
**File:** `project_planner.py`
**Issue:** `ProjectPlanner` handles README parsing, prompt building, response parsing, hallucination detection, template generation, and markdown extraction — roughly 7 distinct responsibilities. At 559 lines it exceeds the project's typical ceiling.
**Fix:** Extract `_extract_phases_from_markdown` / `_extract_tasks_from_content` into a shared parser (logic is duplicated with `plan_parser.py`). Move template generation to its own module.

---

### [MEDIUM-2] Duplicated task/phase parsing logic
**Files:** `project_planner.py:401–454`, `plan_parser.py:123–213`
**Issue:** Both files independently implement markdown task extraction with regex for `- [ ]` / `- [x]` patterns. The implementations diverge: `plan_parser.py` checks indentation with `line.startswith(" ")` while `project_planner.py` uses `\s+` regex. A format accepted by one may be rejected by the other.
**Fix:** Extract a single shared markdown task parser used by both.

---

### [MEDIUM-3] API key read from env directly in `workflow.py`
**File:** `workflow.py`, line 120
**Issue:** `api_key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")` duplicates key resolution that the `create_ai_client` factory already handles. If env var names change, this diverges silently.
**Fix:** Rely on the AI client factory's own key resolution.

---

### [MEDIUM-4] `TaskDecomposer(api_key="dummy")` to access its parser
**File:** `workflow.py`, line 173
**Issue:** Instantiating `TaskDecomposer` with a fake key just to call `_parse_response` is a code smell. It creates a real AI client with an invalid key, which may raise confusing errors if the constructor validates keys.
**Fix:** Extract `_parse_response` as a `@staticmethod` or standalone function so it can be called without instantiation.

---

### [MEDIUM-5] `artifact_status()` called twice in `print_status()`
**File:** `project_manager.py`, lines 226–230
**Issue:** `self.artifact_status()` is called once for iteration and once for counting, performing duplicate filesystem checks.
**Fix:**
```python
status = self.artifact_status()
for artifact, exists in status.items():
    ...
count = sum(1 for v in status.values() if v)
```

---

### [MEDIUM-6] `SelfReviewer.__init__` missing AI client fallback
**File:** `self_reviewer.py`, line 68
**Issue:** Unlike `ProjectPlanner.__init__` (which catches client init failures and falls back to a stub), `SelfReviewer.__init__` lets `create_ai_client` exceptions propagate. If no API key is configured, constructing a `SelfReviewer` fails even though `_static_review` could handle it without AI.
**Fix:** Add the same stub fallback pattern used in `ProjectPlanner`.

---

## LOW Issues

### [LOW-1] Emoji in logger output
**Files:** `project_manager.py` (lines 78, 203, 225, 227), `plan_parser.py` (lines 245, 254, 263, 272)
**Issue:** Logger messages contain emoji characters. These may render poorly in some terminal environments and CI logs. `preflight.py` uses portable `[PASS]`/`[FAIL]` text markers instead.

---

### [LOW-2] `AgentExecutor` and `TaskAgent` missing from `__init__.py`
**File:** `generator/planning/__init__.py`
**Issue:** `AgentExecutor` and `TaskImplementationAgent` are not exported via `__all__`. Every other module in the package is exported — this is inconsistent.
**Fix:** Add them to `__init__.py` imports and `__all__`.

---

### [LOW-3] Mutable class-level constant
**File:** `project_manager.py`, line 40
**Issue:** `MEMORY_ARTIFACTS: List[str] = [...]` is a mutable class attribute. A tuple is safer and more idiomatic for constants.
**Fix:** `MEMORY_ARTIFACTS: Tuple[str, ...] = (...)`

---

### [LOW-4] Imprecise type annotation
**File:** `agent_executor.py`, line 12
**Issue:** `_SYNONYM_PATTERNS: List[tuple]` should be `List[Tuple[str, str]]` for clarity.
**Fix:** `_SYNONYM_PATTERNS: List[Tuple[str, str]] = [...]`

---

## Recommended Fix Order

1. **HIGH-3** — `assert` → explicit `if` guards (5 min, zero risk)
2. **HIGH-4** — f-strings in logger → `%s` args in `workflow.py` (10 min)
3. **HIGH-2** — annotate/narrow the 7 bare `except Exception` (15 min)
4. **HIGH-1** — expose private methods as public/static (20 min)
5. **MEDIUM-5** — double `artifact_status()` call (2 min)
6. **MEDIUM-6** — `SelfReviewer` fallback (10 min)
7. **MEDIUM-4** — `TaskDecomposer("dummy")` smell (15 min)
8. **LOW-2** — `__init__.py` exports (5 min)
