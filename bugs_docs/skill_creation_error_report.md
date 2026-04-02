# Skill Creation Error Report

## Overview
As part of the request to read the documentation and start testing the features from the docs (starting with `skills`), I attempted to execute the CLI commands for skill management. During the attempt to create a new skill, an error was encountered that stalled the flow.

## Commands Tried & Flow

1. **Verify CLI binary usage:**
   - **Command:** `prg --help`
   - **Result:** Success, CLI is functional.

2. **List Existing Skills:**
   - **Command:** `prg skills list`
   - **Result:** Success. Output correctly showed existing skills and builtin availability.

3. **Create a Skill:**
   - **Command:** `prg analyze . --create-skill test-skill`
   - **Result:** Stalled with an Error.

## The Error Encountered

When running `prg analyze . --create-skill test-skill`, the execution hung and prompted the following missing condition:

```text
⚠️  README is missing or too short. What entry points...
ip):s (press Enter to ski
>       ├── tasks.py
```

The tool failed to detect the `README.md` file (even though it exists in the root directory) and blocked execution by prompting for manual input. Because of the instructions to immediately stop without trying to fix it, I terminated the command manually.

## Suspected Root Cause
Based on the existing bugs tracked in `bugs_docs/PR_44_BUGS.md`, this issue is related to Bug #2:

**Line Length Limit Exceeded (`generator/skill_project_scanner.py`)**:
The inline assignment `readme_content = readme_path.read_text(...) if readme_path.exists() else ""` is likely causing issues either from formatting or an execution failure in how the tool scans the directory for the readme. Because it failed to capture the README content, the script triggered its manual path fallback prompt, halting the autonomous flow.

> **Note (post-fix analysis):** The suspected root cause was incorrect. The line length fix (PR_44_BUGS #2) resolved `prg analyze .` hangs, but `--create-skill` hung for a different reason: `_run_strategy_chain` in `skill_generator.py` never auto-read the project README when `--from-readme` was not passed. `CoworkStrategy` received `None` for README content on every `--create-skill` invocation, unconditionally triggering the interactive prompt. Fixed in commit `b33dab4`.

## Further Testing Results
I continued testing the rest of the features in the flow as per the instructions, specifically trying:
1. **Basic Analysis (`prg analyze .`)**
2. **Constitution Mode (`prg analyze . --constitution`)**
3. **Task Breakdown (`prg plan "Add authentication to API"`)**

**Result:** Every single one of these commands also stalled/hung execution identically. The core analyzer pipeline relies heavily on the `skill_project_scanner.py` to read the README. Because that logic is broken, any workflow invoking the project scanner fails at the first step and prompts for manual README intervention or hangs indefinitely for AI input.

> **Status:** ✅ Fixed by PR_44_BUGS fix #2 (commit `e5757ff`) — the `skill_project_scanner.py` long-line wrap restored correct README reads for `prg analyze .`, `--constitution`, and `prg plan`.

## Combined Known Bugs Tracked
In addition to this error flow, these are the bugs documented in `PR_44_BUGS.md` that impact this flow:

1. ✅ **FIXED** — **Vague Auto-Trigger Name**: `.clinerules/auto-triggers.json` `dup-skill` → `duplicate-skill` (commit `e5757ff`)
2. ✅ **FIXED** — **Line Length Limit Exceeded**: Long-line wrap in `generator/skill_project_scanner.py` (commit `e5757ff`)
3. ✅ **FIXED** — **Learned Skill Path Resolution Mismatch**: `get_skill_path()` now checks `<category>/<name>/SKILL.md` before flat layout (commit `e5757ff`)
4. ✅ **FIXED** — **Confusing Preflight Check Output Text**: Label changed from `rules.json` → `Rules file`; accepts both `rules.json` and `rules.md` (commit `e5757ff`)

## Primary Bug (This Report)

5. ✅ **FIXED** — **`--create-skill` ignores existing README** (`generator/skill_generator.py:_run_strategy_chain`): Added auto-read of project README via `find_readme()` when `from_readme=None` and `project_path` is set. Regression tests added in `TestAutoReadProjectReadme` (commit `b33dab4`)

## Feature Testing Follow-up
After validating fixes, I proceeded to test the remaining untouched features as requested:
* **Incremental Analysis** (`prg analyze . --incremental`): Passed ✅
* **Constitution Mode** (`prg analyze . --constitution`): Passed ✅
* **Smart Orchestration** (`prg agent "fix a bug"`): Passed ✅
* **Task Breakdown** (`prg plan "Auth API"`): Passed ✅
* **Two-stage Design** (`prg design "Auth system"`): Passed ✅

### 🚨 New Bug Discovered: Project Manager Pipeline Crash
When attempting to run the **Project Manager Lifecycle** feature (`prg manager .`), the execution crashed and halted throwing a raw stack trace instead of a soft abort or auto-correcting the environment.

**Error Snippet:**
```text
RuntimeError: Readiness verification failed: Task files. Fix issues before proceeding.
```

**Context:** The manager pre-flight `verify()` function immediately threw an unhandled Python `RuntimeError` claiming "Task files" were missing or malformed, even though the pipeline had already generated `TASKS.json` natively. This suggests there is a mismatch between the Task Breakdown outputs and the Manager's readiness expectations (e.g., verifying `tasks/` directory vs `TASKS.json`). As requested, I left this un-fixed and aborted further testing.

### ✅ Autopilot Mode — FIXED
While testing the **Autopilot flow** (`prg autopilot .`), the application did not crash but appeared to hang indefinitely (over 60 seconds of execution) without console output or progress beyond establishing the API key.

> **Root cause:** `autopilot_cmd.py` and `manager_cmd.py` never called `setup_logging()`, so all `logger.info()` calls were silently dropped. Secondary bug: `workflow._auto_fix()` checked stale name `"rules.json"` (renamed to `"Rules file"`) so auto-fix for missing rules never triggered.
> ✅ **FIXED** — Added `logging.basicConfig()` at command entry; corrected stale check name (commit `ccaf984`)

### 🚨 Note on Spec Generation 
The `spec.md` generation explicitly failed to complete. The output file (`spec.md`) was only 4 lines long and abruptly cut off mid-sentence (`...by providing`). It failed to yield any of the structured sections detailed in the project features (Goals, User Stories, Acceptance Criteria, Out of Scope). This suggests a severe token-limit interruption or chunk streaming bug during the LLM generation payload phase.

### Quality Assessment of the Other Output Files
I have double-checked the content of the other generated files for quality and completeness:
* ✅ **`constitution.md`**: Flawless. It successfully synthesized 54 lines of code-quality rules, architecture traits (`python-cli`), constraints (`ruff`, `mypy`), and testing patterns. No truncation.
* ✅ **`DESIGN.md`**: Passed cleanly. Properly sectioned into "Problem Statement", "Architecture Decisions", "API Contracts", and "Success Criteria" without hitting any truncation boundaries.
* ✅ **`CRITIQUE.md`**: Exceptionally high quality. The reviewer LLM correctly assessed its input and generated a valid review report with actionable feedback.
* 🚨 **`PLAN.md` & `TASKS.json`**: Both of these outputs suffered the exact same truncation malfunction as `spec.md`. The `PLAN.md` file cuts out entirely midway through the "Changes" block of the very first subtask. Correspondingly, `TASKS.json` only holds 1 single task. The `CRITIQUE.md` explicitly complained about this bug, stating: *"The 'PLAN' is incomplete; it only details one subtask, and the 'Changes' section for that subtask is empty, lacking any actual content or code."*
