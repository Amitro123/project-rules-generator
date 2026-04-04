CR #4 — Production Stability Review
Baseline
740 passed, 1 failed — the only failure is a stale version string in a test (test_cli.py expects 0.2.2, got 0.3.0). Trivial to fix: update the assertion or use prg --version substring matching instead of hardcoding.
Autopilot: fully gone — confirmed no remnants in any .py file.

Bugs Found
1. STATE.json non-atomic write — data loss on interrupt
FeatureState.save() calls write_text() directly, which truncates then writes. If the process is killed mid-write (Ctrl+C, OOM, power loss), STATE.json ends up as empty or partial JSON. FeatureState.load() then throws json.JSONDecodeError, which load_state() catches with a broad except and returns a blank default state — silently losing all iteration history. Fix: write to a .tmp file first, then os.replace() (atomic on all POSIX systems and Windows Vista+):
pythondef save(self, state_path: Path) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
    os.replace(tmp, state_path)  # atomic
2. --allow-empty commits on every git commit
_git_commit() passes --allow-empty unconditionally. If the agent produces no file changes (which is logged as a warning), it still creates an empty commit. Over 20 iterations, you could get 20 empty commits polluting the branch history. The flag should only be used when intentionally needed, not as a default. Remove it — the if changes: guard before _git_commit() already handles the no-changes case.
3. Tests run twice per successful iteration
execute_iteration() calls _run_tests() at step 6. Then run_loop() calls verify_success() immediately after, which calls _run_tests() again. On a 741-test suite that takes 40 seconds, this is 80 seconds of redundant test running per "good" iteration. Fix: cache the last test result on self.state and reuse it in verify_success().
4. review_score_from_verdict has a dead zone — "Needs Revision" always passes
The scoring maps "Needs Revision" → 70, which exactly meets the 70-threshold for marking a task complete. This means a reviewer that consistently says "needs revision" will never trigger the fix-pass or emergency-stop — the loop will mark every task done regardless. The three-bucket scoring (40/70/100) is too coarse for meaningful quality gating. At minimum, "Needs Revision" should return 65 so it falls into the fix-pass range (60–69).
5. prg ralph discover --run has no timeout
The subprocess.run(["prg", "ralph", f], cwd=proj) call in ralph_discover has no timeout= parameter. If a feature loop hangs (e.g., waiting on a stalled AI API call), discover --run blocks indefinitely with no escape except kill -9. Since each feature can run up to 20 iterations × 120s test timeout = ~40 min, a full discover run could hang for hours with no user feedback.
6. Branch creation in ralph_go has no timeout
subprocess.run(["git", "checkout", "-b", branch_name], ...) in ralph_go has no timeout. On a slow network-mounted filesystem or a large repo, this can hang the whole flow silently.
7. prg ralph stop doesn't check if you're on the right branch
ralph_stop sets STATE.json to stopped but doesn't verify git branch --show-current matches the feature's branch_name. If a user accidentally runs prg ralph stop FEATURE-001 while on a different branch, the state is saved correctly but the branch checkout at the end may land on an unexpected state. Low severity but confusing.
8. prg ralph approve silently succeeds even if gh is missing
pythonsubprocess.run(["gh", "pr", "create", ...], capture_output=True)
No check=True, no handling of non-zero returncode. If gh isn't installed, the PR is never created but the state is already saved as success. The user sees 📬 PR created (if gh CLI is available) — but it wasn't. This should log a clear warning or check result.returncode.
9. _sanitize_env_from_dotenv regex over-matches
In cli.py, the .env parser regex is:
pythonr"""^\s*([\w]+)\s*[:=]\s*['"](.*?)['"]\s*$"""
The .*? is non-greedy but the outer quotes are optional — so MY_KEY=foo=bar would match with value="foo=bar" correctly, but MY_KEY='foo'bar' would match with value="foo" and silently drop bar'. Edge case, but .env parsers are a common source of subtle auth failures.
10. Version test hardcodes 0.2.2 — already broken
pythonassert "0.2.2" in result.output  # actual output: "cli, version 0.3.0"
The test should assert prg --version exits 0 and contains a version string, not a hardcoded one. Either assert result.exit_code == 0 or check __version__ dynamically.

Summary Scorecard
CategoryCR #3CR #4Core functionality8.5/108.5/10Error handling8/107/10 ↓ (STATE.json, approve silent fail)Ralph loop correctnessN/A6/10 (double tests, scoring dead zone, allow-empty)Git safety8/107/10 (no atomicity, no branch check on stop)Test suite9/108.5/10 (1 stale assertion)Overall8/107.5/10
The score dips slightly because Ralph introduced several new correctness issues. None are showstoppers, but the STATE.json write and the scoring dead zone are the ones most likely to cause user-visible failures in production.
Fix priority:

Atomic STATE.json write (os.replace)
Remove --allow-empty from _git_commit
Fix version test assertion
review_score_from_verdict — return 65 for "Needs Revision"
Add timeout to discover --run subprocess call



CR #4 Continued — Additional Bugs Found
Bug #11: SecurityError is silently swallowed — path traversal becomes a no-op
The security chain has a contradiction: _parse_response() raises SecurityError on a bad LLM path (e.g. ../../etc/passwd), but _agent_execute() wraps the entire agent.implement() call in except Exception — so SecurityError is caught, logged as a warning, and returns {}. The loop continues as if nothing happened. The docstring even contradicts itself: it says "silently dropped" but the code raises. The net result is correct (no files written) but for the wrong reason, and there's zero user-visible indication that an LLM tried path traversal. SecurityError should be re-raised through the except Exception guard, or at minimum logged at logger.error level.
Bug #12: next_feature_id() has a race condition
next_feature_id() lists the features/ directory, finds the max, and returns max + 1. If two processes call it simultaneously before either creates the directory, both return FEATURE-001. The second feature_dir.mkdir() then fails (or silently succeeds if exist_ok=True). Fix: use mkdir() atomically inside next_feature_id() with a retry loop, or use a file lock.
Bug #13: Task matching by title — duplicate titles cause silent stall
_mark_task_complete() finds the first task matching by title string. If the task decomposer generates two tasks with the same title (e.g. "Add tests"), the second one is never marked done. _pending_tasks() always returns it, so should_exit() never returns True on task completion grounds, and the loop runs to max_iterations instead of completing naturally.
Bug #14: _RalphGroup typo-routing — any misspelled subcommand becomes a feature
prg ralph staus (typo for status) doesn't match any subcommand and doesn't start with -, so _RalphGroup.parse_args prepends go — it becomes prg ralph go staus, creating a feature named "staus". This is user-hostile. The group should suggest known commands on unknown input rather than silently routing to go.
Bug #15: slugify('') produces an empty branch name
Empty or whitespace-only task descriptions produce slug = '', giving a branch name of ralph/FEATURE-001-. Git accepts this but it's broken. next_feature_id + slugify should validate that the slug is non-empty before using it.
Bug #16: Ralph silently "works" on non-git repos
If prg ralph go is run in a non-git directory, branch creation fails with a logged warning and the loop continues. All git operations (_git_commit, _git_log_oneline, _git_diff_names) silently no-op or return fallback strings. The user sees iterations running but nothing is committed. There should be an upfront is_git_repo() check with a hard exit — Ralph's entire value proposition (branch per feature, PR creation) requires git.
Bug #17: prg ralph approve silent PR failure
After merging the branch, subprocess.run(["gh", "pr", "create", ...]) runs with no check=True and no returncode inspection. The message "📬 PR created (if gh CLI is available)" is printed regardless of outcome. If gh isn't installed, isn't authenticated, or the branch doesn't exist on remote, the PR is never created but the state is saved as success. A result.returncode != 0 check + explicit warning is needed.
Bug #18: merge_branch() uses default merge strategy (fast-forward)
git merge <branch> with no flags will fast-forward if possible, producing no merge commit. When reviewing history, the feature boundary disappears. Should use --no-ff to always create a merge commit, making it clear where each Ralph feature started and ended.
Cross-Provider Behavioral Differences
All four providers are functionally consistent — choices[0] in Groq/OpenAI is inside try/except Exception → RuntimeError, so an empty choices list surfaces as RuntimeError("Groq generation failed: list index out of range") to callers rather than a raw IndexError. Anthropic is the safest (uses next() with default). Gemini's response.text can raise ValueError on safety-blocked content, which is also caught by the broad except and re-raised as RuntimeError. Consistent behavior, but the error messages are generic. No cross-provider bugs.

Full Issue Registry (CR #4)
#SeverityLocationIssue10Lowtest_cli.py:81Hardcoded "0.2.2" version assertion, fails against 0.3.011Highralph_engine._agent_executeSecurityError swallowed by broad except Exception12Mediumralph_engine.next_feature_idRace condition — concurrent calls return duplicate IDs13Mediumralph_engine._mark_task_completeDuplicate task titles cause infinite loop to max_iterations14Mediumralph_cmd._RalphGroupTypo-routing sends misspelled subcommands to ralph go as features15Lowralph_engine.slugifyEmpty task description produces broken branch name16Highralph_cmd.ralph_goNo git repo check — loop runs silently producing no commits17Mediumralph_cmd.ralph_approvegh pr create returncode ignored, silent PR failure18Lowprg_utils.git_ops.merge_branchNo --no-ff, loses feature boundaries in history
Plus the 9 issues from CR #4's first pass. Combined with the green test suite (740/741), the underlying codebase is solid — these are all Ralph-specific issues in a component that's still new.
Fix priority order: #16 (git check upfront) → #11 (SecurityError escape) → #1 (atomic STATE.json write, from first pass) → #13 (duplicate titles) → #17 (approve silent failure) → #14 (typo routing) → #10 (test version string).