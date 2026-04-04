CR #5 — Comprehensive Review
Test Suite
745 passed, 0 failed ✅

All README Flows — Status
FlowResultNotesprg init .✅Cleanprg analyze .⚠️Tech detection weak — reads fastapi, react, typescript, redis, sqlalchemy from README but outputs "This project uses: python" onlyprg analyze . --incremental⚠️"Git commit failed" warning on second run — no-op commit attempt after nothing changedprg analyze . --constitution✅Fixed — now correctly detects pytestprg design "..." (offline)✅ improvedNow shows "template design" note. Still generic but honestprg plan "..." (offline)✅ improvedNow shows "generic template plan" note. Honestprg review PLAN.md (no key)✅Clean errorprg skills list --all✅Score/Hits columns workingprg skills validate✅100/100 passprg skills feedback✅Records useful votesprg skills stale✅Worksprg agent "..."⚠️"let's build a checkout page" → No match. README example shows prg agent "fix a bug" works but design/brainstorming triggers don't fire on natural languageprg providers list✅Cleanprg manager .⚠️Scaffolds tests/ and pytest.ini but says "Missing: spec.md" every run even when not neededprg verify .⚠️Still fails on "Task files" — requires tasks/ dir which no normal flow createsprg feature "..."✅Clean, branch createdprg ralph status✅Rich table outputprg ralph stop✅State persisted, branch checkout works

Bugs Found
B1 — Tech stack detection is broken in prg analyze
The README clearly lists fastapi, react, typescript, redis, sqlalchemy — prg init detects them correctly, but prg analyze outputs "This project uses: python" and the ARCHITECTURE section shows python-cli with no frontend/backend detected. The two commands use different detection paths and analyze loses most of the stack. A user running prg analyze after prg init gets a weaker result than init produced.
B2 — prg analyze --incremental emits a git error on unchanged projects
WARNING: Git commit failed: Git commit failed:
   Files were generated, you can commit manually
When nothing changed, the incremental run still tries to commit and fails on "nothing to commit." Should check git diff --cached --quiet before attempting a commit.
B3 — prg agent doesn't match natural brainstorming/design inputs
prg agent "let's build a checkout page" → "No matching skill found."
prg agent "can you review this?" → "No matching skill found."
The synonym table in agent_executor.py has "let's build" mapped, but the triggers JSON only has phrases that must substring-match. The skill brainstorming has triggers like "i want to add..." and requesting-code-review has "can you review?" — but neither fires. The auto-triggers.json in the project's .clinerules/ is either absent or missing these entries after prg analyze.
B4 — prg verify still fails on "Task files" with no clear path forward
After running prg manager + prg feature (the documented Ralph workflow), verify still fails:
[FAIL] Task files — No tasks/ directory found. Fix: prg setup <task>
prg setup is not documented in the README. The README flow is prg manager → prg verify → prg ralph but verify fails at this step with no way to pass using the documented commands.
B5 — prg init tech detection ≠ prg analyze tech detection
Init correctly reads the README and detects the full stack. Analyze misses it. This is a consistency gap — both should use the same detection pipeline.
B6 — prg manager says "Missing: spec.md" on every run
Even after running manager once, re-running it complains spec.md is missing and suggests prg spec --generate. For a project that doesn't want a spec, this is noise on every invocation.

What Was Fixed vs CR#5
CR#5 issueFixed?Constitution "no test framework"✅ FixedDesign offline filler — no disclaimer✅ Fixed — now says "template design"Plan offline filler — no disclaimer✅ Fixed — now says "generic template plan"Verify chicken-and-egg trap⚠️ Partially — PLAN.md/DESIGN.md now optional, but Task files still blocksBadge "706+ Passing" stale✅ FixedPyPI badge broken❌ Still present and erroring

Rating: 7.8/10
CategoryScoreΔCore flows (init/analyze/plan/design)7/10→ (tech detection regression)Error handling9/10↑Offline UX7/10↑ (honest disclaimers added)Ralph flow8.5/10↑Test suite9.5/10→First-run experience7/10→Overall7.8/10↑ from 7.5
The codebase is in genuinely good shape. The two issues worth fixing before going open source: tech detection inconsistency between init and analyze, and the prg verify task files block that stops the documented Ralph workflow from completing.



CR #5 Deep Dive — Root Cause Analysis
B1 — Tech detection gap: CONFIRMED & ROOT CAUSE FOUND
_validate_tech_with_deps in readme_parser.py strips the entire stack when a sparse pyproject.toml exists.
The logic is: if any dependency file exists → validate each README tech against it. A minimal pyproject.toml containing only [tool.pytest.ini_options] passes the "has deps" check, but contains none of fastapi/react/redis/sqlalchemy — so they all get stripped. Only python survives (detected from .py files on disk).
Fix: change the fallback logic. If dep content is present but contains fewer than N known frameworks, trust the README instead. Or simply union README-detected tech with dep-confirmed tech rather than intersecting.
B2 — Doubled error message: CONFIRMED & ROOT CAUSE FOUND
commit_changes() raises RuntimeError("Git commit failed: <stderr>"). analyze_cmd catches it and prints WARNING: Git commit failed: {e} — producing "Git commit failed: Git commit failed: ". Two fixes needed: strip the prefix from the RuntimeError message, or just print {e} not f"Git commit failed: {e}".
B3 — Agent doesn't match brainstorming/review triggers
prg analyze doesn't write auto-triggers.json in offline mode, so the triggers file either doesn't exist or is empty. The skill trigger matching has no fallback to the builtin trigger definitions — it only reads the project-level JSON file.
B4 — prg verify Task files check is wrong
The "Task files" check looks for tasks/ directory. The Ralph workflow creates features/FEATURE-001/PLAN.md and TASKS.yaml — not a tasks/ directory. The check is testing for an artifact from the old Autopilot workflow that no longer exists. Should be removed or updated to check features/ instead.

Summary of actionable fixes:
#FileFixB1generator/analyzers/readme_parser.pyUnion README tech + dep tech, don't intersectB2cli/analyze_cmd.pyChange f"Git commit failed: {e}" → f"{e}"B3generator/planning/agent_executor.pyFall back to builtin trigger definitions when auto-triggers.json is absentB4generator/planning/preflight.pyRemove or fix "Task files" check — tasks/ dir no longer used