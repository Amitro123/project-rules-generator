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

---

## Architectural Limitations (Comprehensive_CR_april — April 2026)

Second-pass review. Not bugs — design constraints acknowledged for future iterations.

---

### Issue 9 — Parsers: Broad `except Exception` blocks mask diagnostics

**Area:** `EnhancedProjectParser`, `DependencyParser`, `CodeExampleExtractor`

**Description:** Most file-reading and parsing paths catch bare `Exception` and log a warning before returning a fallback. This hides specific errors (TOML parse failures, encoding issues, permission errors) and makes debugging hard.

**Severity:** Low in production, High during development/debugging.

**Future fix:** Replace with specific exception types (`FileNotFoundError`, `tomllib.TOMLDecodeError`, `json.JSONDecodeError`) and surface actionable error messages.

---

### Issue 10 — `DependencyParser`: Regex brittleness for `requirements.txt`

**Area:** `generator/parsers/dependency_parser.py` — `parse_requirements_txt`

**Description:** Standard lines are parsed via `re.match` after using `packaging.requirements.Requirement`. Complex directives (environment markers, VCS URLs, `--index-url`) may not be handled correctly.

**Severity:** Low — most real-world `requirements.txt` files use simple name==version lines.

**Future fix:** Use `pip`'s `RequirementsFile` parser or `pip-requirements-parser` library.

---

### Issue 11 — `ReadmeSkillExtractor`: Core logic is fragile regex

**Area:** `generator/analyzers/readme_skill_extractor.py`

**Description:** `extract_purpose`, `extract_auto_triggers`, `extract_process_steps`, and `extract_anti_patterns` are almost entirely regex-driven over Markdown. Minor formatting changes break extraction silently.

**Severity:** Medium — README formatting varies widely across projects.

**Future fix:** Parse README to a Markdown AST (e.g., `mistletoe`, `markdown-it-py`) and traverse nodes rather than scanning raw text.

---

### Issue 12 — `CodeExampleExtractor`: Hardcoded relevance scores and limits

**Area:** `generator/extractors/code_extractor.py`

**Description:** Relevance scores (7 for decorated functions, 6 for classes, etc.) and the 10-example cap are arbitrary constants. Large codebases may have all critical examples excluded.

**Severity:** Low — affects skill quality on large projects, not correctness.

**Future fix:** Make limits configurable; derive relevance from actual usage frequency or test coverage data.

---

### Issue 13 — `ProjectTypeDetector`: Arbitrary heuristic scores and `lru_cache` staleness

**Area:** `generator/analyzers/project_type_detector.py`

**Description:** Classification weights (0.5 for LLM providers, 0.15 for keywords) lack empirical basis. The `@lru_cache` on `_detect_project_type_cached` can return stale results if project files change between calls within the same process.

**Severity:** Low — misclassification degrades skill quality but doesn't break functionality.

**Future fix:** Tune weights from a labelled dataset; invalidate cache on file-system changes or remove `lru_cache` in favour of instance-level caching.

---

### Issue 14 — Autopilot: No schema validation of LLM output before file writes

**Area:** `generator/planning/autopilot.py` and task execution pipeline

**Description:** LLM-generated file paths, code blocks, and commands are written to disk without validation. No check that paths stay within the project directory, no sanitization of shell commands.

**Severity:** Medium — mitigated by git-branch isolation, but bad LLM output requires manual triage.

**Future fix:** Define Pydantic schemas for all LLM outputs; validate before writing; reject paths outside project root.

| # | Feature | Severity | Area |
|---|---------|----------|------|
| 9 | Parsers | Low/High | Broad exception handling |
| 10 | `DependencyParser` | Low | `requirements.txt` regex brittleness |
| 11 | `ReadmeSkillExtractor` | Medium | Regex-based Markdown parsing |
| 12 | `CodeExampleExtractor` | Low | Hardcoded relevance scores |
| 13 | `ProjectTypeDetector` | Low | Arbitrary weights, `lru_cache` staleness |
| 14 | Autopilot | Medium | No LLM output validation before file writes |
