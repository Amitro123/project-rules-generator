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
