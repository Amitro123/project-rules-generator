# Known Issues

## Feature 4 & 5: `prg plan` / `prg design` Quality Problems

Discovered during session on 2026-03-30 by running `prg design` and `prg plan --from-design` on this project.

---

### Issue 1 — `prg design`: Success Criteria section generates empty bullets ✅ FIXED

**Command:** `prg design "Refactor remaining god-modules: rules_creator.py (864 LOC), agent.py (630 LOC)..."`

**Expected:** Each success criterion has a concrete, measurable description.

**Actual output (before fix):**
```markdown
## Success Criteria

- **Code Modularity**:
- **Testability**:
- **Maintainability**:
- **Reliability**:
```

**Root cause:** `_extract_bullets()` in `design_generator.py` used `re.finditer(r"^-\s+(.+)", text, re.MULTILINE)` — only captured the first line of each bullet. When the LLM writes multi-line criteria (label on one line, body indented below), only the label was captured.

**Fix (PR `fix/known-issues-plan-design`):** Replaced the regex with a line-by-line parser that accumulates continuation lines until the next bullet or heading starts.

**Severity:** Medium

---

### Issue 2 — `prg plan --from-design`: Generates only 1 subtask instead of ~5 ✅ FIXED

**Command:** `prg plan --from-design DESIGN.md`

**Expected:** Multiple concrete subtasks mapped to each architectural decision.

**Actual (before fix):**
```
Generated 1 subtasks
Estimated time: 5 minutes
```

**Root cause:** `_parse_response()` in `task_decomposer.py` used a single regex `r"###?\s*(\d+)\.\s*"` to split LLM output. When the LLM used `##`, `**1.**`, or `1)` heading styles instead of `### 1.`, the regex didn't match → fallback single-task was returned.

**Fix:** Pre-normalise all common LLM heading variants (`## N.`, `**N.**`, `N)`) to `### N.` before splitting.

**Severity:** High

---

### Issue 3 — `prg plan`: Generated task references wrong file path ✅ FIXED

**Actual output (before fix):**
```markdown
**Files:**
- `src/config.py` (new)
```

**Root cause:** `_build_design_prompt()` had no project tree injection. When `project_context=None` (CLI default), the LLM received no structural grounding and hallucinated a generic `src/` layout.

**Fix:** Inject `build_project_tree(project_path)` output directly into `_build_design_prompt()`. `project_path` is now derived from `design_path.parent` in `from_design()`.

**Severity:** High

---

### Issue 4 — `prg plan`: Task content truncated mid-sentence ✅ FIXED

**Actual output (before fix):**
```markdown
- Define a Pydantic `BaseModel` named `LLMConfig` with fields: `provider: str`, `model: str`, `api_key:
```

**Root cause:** `_call_llm()` set `max_tokens=3000` — far too low when generating 5-8 detailed subtasks with Goals, Files, Changes, Tests, Dependencies, and Estimated fields each.

**Fix:** Increased `max_tokens` from `3000` → `5000`.

**Severity:** High

---

## Summary Table

| # | Feature | Severity | Status | Fix |
|---|---------|----------|--------|-----|
| 1 | `prg design` | Medium | ✅ Fixed | Multi-line `_extract_bullets()` in `design_generator.py` |
| 2 | `prg plan` | High | ✅ Fixed | Normalise LLM heading variants in `_parse_response()` |
| 3 | `prg plan` | High | ✅ Fixed | Inject project tree into `_build_design_prompt()` |
| 4 | `prg plan` | High | ✅ Fixed | Raise `max_tokens` 3000 → 5000 in `_call_llm()` |
