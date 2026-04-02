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
