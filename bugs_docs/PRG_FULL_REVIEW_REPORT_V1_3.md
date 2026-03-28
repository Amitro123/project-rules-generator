# CR v1.3: Full Code Review — Planning, Tasks, Design, Autopilot & Rules

This document outlines the findings from the **v1.3 Full Code Review** following the skills-fix in Issue #17.

**Scope:**
- `generator/planning/`
- `generator/task_decomposer.py`
- `generator/design_generator.py`
- `generator/rules_generator.py`
- `generator/cowork_rules_creator.py`
- `cli/cli.py`

---

## 🔴 CRITICAL Bugs (break core workflows)

### BUG-C1 — PreflightChecker checks for rules.json but PRG writes rules.md
- **File:** `generator/planning/preflight.py` → `_check_rules_json()`
- **Problem:** The check looks for `.clinerules/rules.json`, but `RulesGenerator` / `CoworkRulesCreator` write `rules.md`. This causes the preflight "rules" check to always fail for any standard PRG run, triggering a bogus auto-fix loop.
- **Fix:** Rename the check to `_check_rules_md()` and look for `rules.md` (and optionally `rules.json` as a legacy fallback).

### BUG-C2 — PreflightChecker looks for tasks/0*.md but TaskCreator writes .py by default
- **File:** `generator/planning/preflight.py` → `_check_task_files()` & `generator/planning/task_creator.py` → `_subtask_to_filename()`
- **Problem:** `TaskCreator._subtask_to_filename()` uses `subtask.type` which defaults to `"py"`, so task files are `task001-foo.py`. But `_check_task_files()` globs `tasks/0*.md` — `.py` files are never found, so the preflight always reports failure.
- **Fix (Option A):** Change `SubTask.type` default to `"md"`.
- **Fix (Option B):** Update `_check_task_files()` to glob both `0*.md` and `0*.py`.

### BUG-C3 — TaskDecomposer hard-codes Gemini; bypasses provider abstraction entirely
- **File:** `generator/task_decomposer.py` → `__init__` + `_call_llm()`
- **Problem:** Direct hard-code to `genai.Client` instead of using `create_ai_client()`. If a user only has `GROQ_API_KEY` set, `TaskDecomposer` gets `None` for `api_key` and silently falls back to a stub plan with no error or warning.
- **Fix:** Route through `create_ai_client(provider, api_key)` the same way `ProjectPlanner` and `DesignGenerator` do.

### BUG-C4 — AgentWorkflow._generate_plan() passes a Groq key into the Gemini-only TaskDecomposer
- **File:** `generator/planning/workflow.py` → `_generate_plan()`
- **Problem:** When only `GROQ_API_KEY` is set, the Groq key is passed to `google.genai.Client`, which raises an authentication error. The fallback stub plan is used with no user-visible warning.
- **Fix:** Resolve after BUG-C3 — once `TaskDecomposer` respects provider, pass `provider=self.provider`.

---

## 🟠 HIGH-Priority Bugs

### BUG-H1 — PlanParser._parse_phases(): each task header becomes its own phase
- **File:** `generator/planning/plan_parser.py` → `_parse_phases()`
- **Problem:** The header-based branch (`## N. Task Name`) creates one `PhaseStatus` per task. A `PLAN.md` with 6 tasks produces 6 phases each with 1 task instead of 1 phase with 6 tasks, breaking progress %.
- **Fix:** Group consecutive numbered tasks into the same phase.

### BUG-H2 — TaskStatus.is_blocking property has inverted semantics
- **File:** `generator/planning/plan_parser.py`
- **Problem:** Logic describes a task where all subtasks are done but the parent is not, which implies it's stale—not blocking. The misleading name `blocking_tasks` creates confusing output.
- **Fix:** Rename to `is_stale` or fix the logic to actually detect dependencies.

### BUG-H3 — _ensure_minimum_tasks() only pads the single-task fallback; skips the 2-task case
- **File:** `generator/task_decomposer.py` → `_ensure_minimum_tasks()`
- **Problem:** Padding only happens for the single-stub case. If the AI returns 2 well-formed tasks, they are returned as-is even if the minimum is 3.
- **Fix:** Pad to minimum for any under-populated list.

### BUG-H4 — SelfReviewer._extract_section() silently drops items when AI adds a blank line
- **File:** `generator/planning/self_reviewer.py`
- **Problem:** The regex `rf"{header}:\s*\n((?:\s*-\s+.+\n?)+)"` requires bullet items immediately after the header. If the AI adds a blank line, the match fails.
- **Fix:** Change the pattern to allow optional blank lines: `rf"{header}:\s*\n(?:\s*\n)*((?:\s*-\s+.+\n?)+)"`.

---

## 🟡 MEDIUM Bugs

### BUG-M1 — _parse_plan_subtasks() uses api_key="dummy" as a parsing hack
- **File:** `generator/planning/workflow.py` → `_parse_plan_subtasks()`
- **Problem:** A dummy key is passed to suppress API calls.
- **Fix:** Extract `_parse_response` into a `@staticmethod` or a standalone `parse_plan_md(content, task)` function.

### BUG-M2 — TaskManifest timestamps use datetime.now() (local time, no timezone)
- **File:** `generator/planning/task_creator.py` → `TaskManifest.__post_init__`
- **Problem:** Produces timezone-naive local time, causing inconsistent CI/multi-user timestamps.
- **Fix:** Use `datetime.now(timezone.utc).isoformat()` everywhere.

### BUG-M3 — _extract_git_antipatterns() runs unbounded git log on large repos
- **File:** `generator/cowork_rules_creator.py`
- **Problem:** No `--max-count` limit on the `git log` command.
- **Fix:** Add `--max-count=200`.

### BUG-M4 — SelfReviewer defaults to provider="groq", rest of codebase defaults to "gemini"
- **File:** `generator/planning/self_reviewer.py` → `__init__`
- **Problem:** Different default providers in different classes.
- **Fix:** Standardize default to `"gemini"` or add a global `DEFAULT_PROVIDER`.

### BUG-M5 — CoworkRulesCreator deduplicates by rule .content text, may silently drop valid rules
- **File:** `generator/cowork_rules_creator.py` → `_generate_content()`
- **Problem:** Two rules from different technologies with the same concise wording (e.g., "Use type hints") will be silently dropped.
- **Fix:** Deduplicate by `(category, content)` tuple.

---

## 🔵 Design Issues

### DESIGN-1 — _detect_hallucinations() is duplicated
- **Problem:** Duplicated in `ProjectPlanner` and `SelfReviewer`.
- **Fix:** Extract to `generator/planning/utils.py`.

### DESIGN-2 — Provider selection is fragmented across 4 modules
- **Problem:** Fragmented selection strategies.
- **Fix:** Add `generator/ai/provider_resolver.py` -> `resolve_provider(preferred, api_key)`.

### DESIGN-3 — SubTask.type defaults to "py" but most tasks should be "md"
- **Problem:** Task files for documentation end up as `.py` files containing a giant markdown string docstring.
- **Fix:** Default type to `"md"`.

### DESIGN-4 — from_plan() in TaskDecomposer creates a linear dependency chain
- **Problem:** Every task depends on the previous one, serializing parallel tasks.
- **Fix:** Parse the plan's phase structure to preserve phases properly.

### DESIGN-5 — _extract_project_context() truncates README at 1,000 characters
- **Problem:** Removes most of the context for typical projects.
- **Fix:** Raise limit to at least 4,000 characters or use the `build_project_tree` + README hook pattern.

### DESIGN-6 — _fix_analyze() in AgentWorkflow assumes legacy signature
- **Problem:** Uses old functional signature for `generate_rules`.
- **Fix:** Instantiate `RulesGenerator(project_path)` and call `.create_rules(readme_content)`.

### DESIGN-7 — CoworkRulesCreator contains PRG-specific hardcoded directory rules
- **Problem:** Entries reference `.clinerules/`, `generator/`, and PRG-internal paths, which leak into other users' projects.
- **Fix:** Namespace PRG-specific rules to only apply if the project being analyzed is PRG itself.

---

## 📊 Fix Priority Order
1. BUG-C1, BUG-C2, BUG-C3, BUG-C4
2. BUG-H1, BUG-H2, DESIGN-2, DESIGN-6, BUG-H3
3. BUG-M1, DESIGN-4, BUG-H4, BUG-M3, DESIGN-1, DESIGN-5, BUG-M2, BUG-M4, BUG-M5
4. DESIGN-3, DESIGN-7
