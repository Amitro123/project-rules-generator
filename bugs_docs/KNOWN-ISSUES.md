# Known Issues

## Feature 4 & 5: `prg plan` / `prg design` Quality Problems

Discovered during session on 2026-03-30 by running `prg design` and `prg plan --from-design` on this project.

---

### Issue 1 — `prg design`: Success Criteria section generates empty bullets

**Command:** `prg design "Refactor remaining god-modules: rules_creator.py (864 LOC), agent.py (630 LOC)..."`

**Expected:** Each success criterion has a concrete, measurable description.

**Actual output:**
```markdown
## Success Criteria

- **Code Modularity**:
- **Testability**:
- **Maintainability**:
- **Reliability**:
```

Labels are correct but bodies are empty. The LLM prompt likely asks for criteria headings separately from their descriptions and one call returns nothing.

**Severity:** Medium — DESIGN.md is technically valid but not useful for planning.

---

### Issue 2 — `prg plan --from-design`: Generates only 1 subtask instead of ~5

**Command:** `prg plan --from-design DESIGN.md`

**Expected:** Multiple concrete subtasks mapped to each architectural decision.

**Actual:**
```
Generated 1 subtasks
Estimated time: 5 minutes
```

For a design with 4 architecture decisions and 13 API contracts, this is severely under-decomposed.

**Severity:** High — the core value of Feature 4 is task decomposition.

---

### Issue 3 — `prg plan`: Generated task references wrong file path

**Actual output:**
```markdown
**Files:**
- `src/config.py` (new)
```

This project uses `generator/` not `src/`. The planner hallucinated a generic Python project layout instead of grounding itself in the actual project tree.

**Severity:** High — hallucinated paths break agent handoffs downstream.

---

### Issue 4 — `prg plan`: Task content truncated mid-sentence

**Actual output:**
```markdown
- Define a Pydantic `BaseModel` named `LLMConfig` with fields: `provider: str`, `model: str`, `api_key:
```

The task description is cut off. Likely a token-budget or string-slicing bug in the task serializer.

**Severity:** High — incomplete tasks cannot be executed by `prg exec` or `prg next`.

---

## Summary Table

| # | Feature | Severity | Area |
|---|---------|----------|------|
| 1 | `prg design` | Medium | LLM prompt / success criteria generation |
| 2 | `prg plan` | High | Task decomposition (under-generates subtasks) |
| 3 | `prg plan` | High | Hallucinated file paths (not grounded in project tree) |
| 4 | `prg plan` | High | Task content truncated mid-sentence |

---

## Architectural Limitations (CR0104 — April 2026)

Identified in third-party code review CR0104. Not bugs — design constraints to address in future iterations.

---

### Issue 5 — SelfReviewer: Hallucination detection is narrow

**Area:** `generator/planning/self_reviewer.py` — `_detect_hallucinations()`

**Description:** Uses a regex to find "capitalized compound names" and checks them against the README. Won't catch hallucinated function names, logic errors, or subtle misinterpretations that don't follow that naming pattern.

**Nature:** Probabilistic check on probabilistic LLM output — adds latency without deterministic correctness guarantee.

**Severity:** Low — catches the most common class of hallucinations; full elimination requires AST-based cross-referencing.

**Future fix:** Cross-reference generated symbols against a real symbol table derived from the actual codebase.

---

### Issue 6 — TaskDecomposer: Structural fallback produces low-value plans

**Area:** `generator/task_decomposer.py` — `_tasks_from_design()`

**Description:** When the LLM fails to decompose tasks, the fallback generates one task per API contract / one per data model — purely structural, not semantic. Users get a generic low-value plan.

**Severity:** Medium — only triggered on LLM failure, but failure is not rare on large designs.

**Future fix:** Improve the LLM prompt with few-shot examples; add a retry loop before falling back.

---

### Issue 7 — Autopilot: Single-shot implementation with no reasoning phase

**Area:** `generator/planning/autopilot.py` — `TaskImplementationAgent`

**Description:** The agent is given a subtask and implements it in one LLM call with no intermediate "drafting" or "change plan" phase. Test failures are a binary pass/fail gate — the orchestrator cannot use failure output to guide a retry.

**Severity:** Medium — git branch isolation provides a safety net, but bad changes require manual triage.

**Future fix:** Add a "Change Plan" phase that produces a list of specific edits for review before any files are written.

---

### Issue 8 — Prompt engineering: Large prompts hit context limits on big projects

**Area:** `task_decomposer.py`, `self_reviewer.py`, `skill_generation.py`

**Description:** Every request sends large chunks of README, project tree, and previous artifacts. On large projects this becomes expensive and risks hitting context limits.

**Severity:** Low for small projects, High for large codebases.

**Future fix:** Implement selective context injection — send only the most relevant file excerpts rather than full documents.

| # | Feature | Severity | Area |
|---|---------|----------|------|
| 5 | `SelfReviewer` | Low | Hallucination detection coverage |
| 6 | `TaskDecomposer` | Medium | Fallback plan quality |
| 7 | `Autopilot` | Medium | Single-shot implementation |
| 8 | Prompts | Low–High | Context size on large projects |
