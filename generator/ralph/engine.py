"""RalphEngine — autonomous feature-scoped iteration loop."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from generator.exceptions import SecurityError
from generator.ralph.state import FeatureState
from generator.ralph.tasks import _load_tasks, _pending_tasks, _save_tasks
from prg_utils import git_ops  # noqa: F401 — kept for downstream consumers
from prg_utils.logger import ensure_utf8_streams

# Library consumers (pytest, programmatic callers) import this module directly
# without going through cli/cli.py, so the Windows UTF-8 reconfigure has to
# happen here too. Idempotent and a no-op on non-Windows.
ensure_utf8_streams()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds and timeouts
# ---------------------------------------------------------------------------

REVIEW_SCORE_EMERGENCY_STOP = 60  # Loop halts; human intervention required
REVIEW_SCORE_TASK_COMPLETE = 70  # Minimum score to mark a task done
REVIEW_SCORE_SUCCESS_GATE = 85  # Minimum score to declare the feature complete
CONSECUTIVE_FAILURE_LIMIT = 3  # Max consecutive agent/test failures before stopping

VERDICT_SCORE_PASS = 100  # SelfReviewer "Pass" verdict
VERDICT_SCORE_MAJOR = 40  # SelfReviewer "Major issues" verdict
VERDICT_SCORE_NEEDS_REVISION = 65  # SelfReviewer "Needs Revision" (below task-complete threshold)

REVIEW_SCORE_NEUTRAL = 70  # Fallback score when self-review cannot run

TIMEOUT_GIT = 10  # seconds — git log / diff
TIMEOUT_SUBPROCESS = 30  # seconds — git commit / gh pr create
TIMEOUT_TESTS = 120  # seconds — full test suite


class RalphEngine:
    """Autonomous feature-scoped iteration loop.

    Usage::

        engine = RalphEngine(
            feature_id="FEATURE-001",
            project_path=Path("."),
            provider="gemini",
        )
        engine.run_loop(max_iterations=20)
    """

    def __init__(
        self,
        feature_id: str,
        project_path: Path,
        provider: str = "groq",
        api_key: Optional[str] = None,
        verbose: bool = True,
    ):
        self.feature_id = feature_id
        self.project_path = Path(project_path).resolve()
        self.provider = provider
        self.api_key = api_key
        self.verbose = verbose

        self.feature_dir = self.project_path / "features" / feature_id
        self.state_path = self.feature_dir / "STATE.json"
        self.tasks_yaml = self.feature_dir / "TASKS.yaml"
        self.plan_md = self.feature_dir / "PLAN.md"
        self.critiques_dir = self.feature_dir / "CRITIQUES"

        self.state = self.load_state()
        self._last_tests_passed: Optional[bool] = None  # cached by execute_iteration()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_loop(self, max_iterations: Optional[int] = None) -> None:
        """Run the autonomous iteration loop until an exit condition is met."""
        if max_iterations is not None:
            self.state.max_iterations = max_iterations

        self.state.status = "running"
        self.save_state()

        if self.verbose:
            logger.info(
                "🚀 Ralph Loop starting — %s (%d max iterations)",
                self.feature_id,
                self.state.max_iterations,
            )

        while not self.should_exit():
            self.state.iteration += 1
            if self.verbose:
                logger.info(
                    "\n%s\n🔄  Iteration %d/%d\n%s",
                    "=" * 60,
                    self.state.iteration,
                    self.state.max_iterations,
                    "=" * 60,
                )
            try:
                self.execute_iteration()
            except Exception as exc:  # noqa: BLE001 — top-level loop guard; logs and re-raises
                logger.error("💥 Unhandled exception in iteration %d: %s", self.state.iteration, exc)
                self.state.status = "stopped"
                self.state.exit_condition = "unhandled_exception"
                self.save_state()
                raise

            # Skip verify_success() when execute_iteration() triggered an emergency stop
            # — avoids a redundant full test suite run after the loop is already halted.
            if self.state.status in ("stopped",):
                continue

            if self.verify_success():
                self.state.status = "success"
                self.state.exit_condition = "all_checks_passed"
                self.save_state()
                if self.verbose:
                    logger.info("Feature complete — all success checks passed.")
                self._create_pr()
                break

        else:
            # should_exit() returned True without verify_success()
            if self.state.status == "running":
                self.state.status = "max_iterations"
                self.state.exit_condition = "max_iterations_reached"
                self.save_state()
                if self.verbose:
                    logger.info(
                        "⚠️  Max iterations (%d) reached — creating PR with findings.",
                        self.state.max_iterations,
                    )
                self._create_pr()

        if self.verbose:
            self._print_summary()

    def execute_iteration(self) -> None:
        """Orchestrate one Ralph iteration: context → skill → agent → commit → review → tests."""
        result = self._step_context()
        if result is None:
            return
        context, next_task_title = result

        skill = self._step_skill(context)

        changes = self._step_agent(context, skill, next_task_title)
        if changes is None:
            return

        if not self._step_commit(changes, next_task_title):
            return

        review_score = self._step_review()
        if review_score is None:
            return

        tests_passed = self._step_tests(next_task_title, review_score)
        if tests_passed is None:
            return

        if self.verbose:
            logger.info(
                "📊 Iter %d complete — review=%d, tests=%s, tasks=%d/%d",
                self.state.iteration,
                review_score,
                "✅" if tests_passed else "❌",
                self.state.tasks_complete,
                self.state.tasks_total,
            )

    # ------------------------------------------------------------------
    # execute_iteration() step methods — one responsibility each
    # ------------------------------------------------------------------

    def _step_context(self) -> Optional[Tuple[str, str]]:
        """Step 1: build context and find next task.

        Returns (context, next_task_title), or None when no pending tasks
        remain (marks complete + saves state before returning None).
        """
        context = self.build_context()
        next_task_title = self._next_task_title()
        if not next_task_title:
            logger.info("No pending tasks found — marking all complete.")
            self.state.tasks_complete = self.state.tasks_total
            self.save_state()
            return None
        if self.verbose:
            logger.info("Next task: %s", next_task_title)
        return context, next_task_title

    def _step_skill(self, context: str) -> Optional[str]:
        """Step 2: match a skill from the context string."""
        skill = self._match_skill(context)
        if self.verbose and skill:
            logger.info("🧩 Matched skill: %s", skill)
        return skill

    def _step_agent(self, context: str, skill: Optional[str], next_task_title: str) -> Optional[dict]:
        """Step 3: run the agent and return its changes dict.

        Returns None on SecurityError (state is set to stopped before returning).
        """
        try:
            return self._agent_execute(context, skill, next_task_title)
        except SecurityError as sec_exc:
            logger.error(
                "🚨 Security violation — LLM attempted path traversal: %s. Stopping loop for manual review.",
                sec_exc,
            )
            self.state.status = "stopped"
            self.state.exit_condition = f"security_violation:{sec_exc}"
            self.save_state()
            return None

    def _step_commit(self, changes: dict, next_task_title: str) -> bool:
        """Step 4: commit changes and track consecutive agent failures.

        Returns False when the loop should stop (agent_fail_3x), True otherwise.
        """
        if changes:
            self.state.consecutive_agent_failures = 0
            self._git_commit(
                f"ralph iter {self.state.iteration}: {next_task_title[:60]}",
                files=list(changes.keys()),
            )
        else:
            self.state.consecutive_agent_failures += 1
            if self.verbose:
                logger.info("No changes produced by agent this iteration.")
            if self.state.consecutive_agent_failures >= CONSECUTIVE_FAILURE_LIMIT:
                self.state.status = "stopped"
                self.state.exit_condition = "agent_fail_3x"
                self.save_state()
                logger.error(
                    "🚨 Agent produced no changes 3× in a row — stopping for human intervention. "
                    "Check your provider/API key configuration. "
                    "Run `prg ralph resume %s` after fixing.",
                    self.feature_id,
                )
                return False
        return True

    def _step_review(self) -> Optional[int]:
        """Step 5: run self-review and enforce score thresholds.

        Returns the review score, or None when the loop should stop (score < 60).
        """
        review_score = self._run_self_review()
        self.state.last_review_score = review_score
        self.save_state()

        if review_score < REVIEW_SCORE_EMERGENCY_STOP:
            self.state.status = "stopped"
            self.state.exit_condition = f"review_score_too_low:{review_score}"
            self.save_state()
            logger.error(
                "🚨 Emergency stop — review score %d < %d. State saved. "
                "Run `prg ralph resume %s` after manual fixes.",
                review_score,
                REVIEW_SCORE_EMERGENCY_STOP,
                self.feature_id,
            )
            return None

        if review_score < REVIEW_SCORE_TASK_COMPLETE and self.verbose:
            logger.info("Review score %d — fixing issues before next iteration.", review_score)
        return review_score

    def _step_tests(self, next_task_title: str, review_score: int) -> Optional[bool]:
        """Step 6: run tests, cache result, track failures, mark task complete.

        Returns the tests_passed bool, or None when the loop should stop (test_fail_3x).
        """
        tests_passed, _ = self._run_tests()
        self.state.test_pass_rate = 1.0 if tests_passed else 0.0
        self._last_tests_passed = tests_passed

        if tests_passed:
            self.state.consecutive_test_failures = 0
        else:
            self.state.consecutive_test_failures += 1
            if self.state.consecutive_test_failures >= CONSECUTIVE_FAILURE_LIMIT:
                self.state.status = "stopped"
                self.state.exit_condition = "test_fail_3x"
                self.save_state()
                logger.error(
                    "🚨 Tests failed 3× in a row — stopping for human intervention. "
                    "Run `prg ralph resume %s` after fixes.",
                    self.feature_id,
                )
                return None

        if tests_passed and review_score >= REVIEW_SCORE_TASK_COMPLETE:
            self._mark_task_complete(next_task_title)
            self.state.tasks_complete = max(
                0, self.state.tasks_total - len(_pending_tasks(_load_tasks(self.tasks_yaml)))
            )
            self.save_state()

        return tests_passed

    def build_context(self) -> str:
        """Assemble loop context from project rules, feature plan, and git history."""
        rules_path = self.project_path / ".clinerules" / "rules.md"
        rules_content = rules_path.read_text(encoding="utf-8") if rules_path.exists() else "(no rules.md)"

        plan_content = self.plan_md.read_text(encoding="utf-8") if self.plan_md.exists() else "(no PLAN.md)"

        next_task = self._next_task_title() or "(all tasks complete)"

        git_log = self._git_log_oneline(5)
        changed_files = self._git_diff_names()

        return (
            f"PROJECT RULES:\n{rules_content[:2000]}\n\n"
            f"FEATURE PLAN:\n{plan_content[:3000]}\n\n"
            f"CURRENT TASK: {next_task}\n\n"
            f"RECENT COMMITS:\n{git_log}\n\n"
            f"FILES CHANGED SINCE LAST COMMIT:\n{changed_files}"
        )

    def should_exit(self) -> bool:
        """Return True when the loop should stop (without considering verify_success)."""
        if self.state.status in ("success", "stopped", "max_iterations"):
            return True
        if self.state.iteration >= self.state.max_iterations:
            return True
        tasks = _load_tasks(self.tasks_yaml)
        if tasks and len(_pending_tasks(tasks)) == 0:
            return True
        return False

    def verify_success(self) -> bool:
        """Return True when the feature is genuinely complete.

        Reuses the test result cached by execute_iteration() to avoid running
        the test suite twice per successful iteration.
        """
        if (self.state.last_review_score or 0) < REVIEW_SCORE_SUCCESS_GATE:
            return False
        tasks = _load_tasks(self.tasks_yaml)
        if tasks and len(_pending_tasks(tasks)) > 0:
            return False
        # Use cached result from execute_iteration() if available; otherwise run tests.
        if self._last_tests_passed is not None:
            return self._last_tests_passed
        tests_passed, _ = self._run_tests()
        return tests_passed

    def load_state(self) -> FeatureState:
        """Load STATE.json or return a minimal default state."""
        if self.state_path.exists():
            try:
                return FeatureState.load(self.state_path)
            except Exception as exc:  # noqa: BLE001 — STATE.json may have unknown keys or corrupt data
                logger.warning("Could not load STATE.json: %s — using defaults.", exc)
        return FeatureState(
            feature_id=self.feature_id,
            task="(unknown)",
            branch_name=f"ralph/{self.feature_id}",
        )

    def save_state(self) -> None:
        """Persist current state to STATE.json."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state.save(self.state_path)

    # ------------------------------------------------------------------
    # Score helpers
    # ------------------------------------------------------------------

    @staticmethod
    def review_score_from_verdict(verdict: str) -> int:
        """Map a SelfReviewer verdict string to a numeric score (0-100)."""
        v = verdict.strip().lower()
        if "pass" in v:
            return VERDICT_SCORE_PASS
        if "major" in v:
            return VERDICT_SCORE_MAJOR
        return VERDICT_SCORE_NEEDS_REVISION  # below REVIEW_SCORE_TASK_COMPLETE; triggers a fix-pass

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _match_skill(self, context: str) -> Optional[str]:
        from generator.planning.agent_executor import AgentExecutor

        executor = AgentExecutor(self.project_path)
        return executor.match_skill(context)

    def _agent_execute(self, context: str, skill: Optional[str], task_title: str) -> dict:
        """Delegate to the AI implementation agent.

        Returns a dict of {relative_path: content} for files to write.
        Falls back gracefully when no AI provider is available.
        """
        try:
            from generator.planning.task_agent import TaskImplementationAgent
            from generator.task_decomposer import SubTask

            agent = TaskImplementationAgent(provider=self.provider, api_key=self.api_key)
            subtask = SubTask(
                id=self.state.iteration,
                title=task_title,
                goal=task_title,
                files=[],
                changes=[],
                tests=[],
                dependencies=[],
                estimated_minutes=30,
            )
            changes: dict = agent.implement(subtask, project_context={"rules_context": context})
            # Write files to disk within project boundary
            for rel_path, content in changes.items():
                full = (self.project_path / rel_path).resolve()
                try:
                    full.relative_to(self.project_path)
                except ValueError:
                    logger.warning("Skipping unsafe path: %s", rel_path)
                    continue
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_text(content, encoding="utf-8")
                if self.verbose:
                    logger.info("   ✏️  %s", rel_path)
            return changes
        except SecurityError:
            # Path traversal attempt from LLM — must not be silently swallowed.
            raise
        except Exception as exc:  # noqa: BLE001 — agent failures must not crash the loop
            logger.warning("Agent execution failed (iteration %d): %s", self.state.iteration, exc)
            return {}

    def _git_commit(self, message: str, files: Optional[List[str]] = None) -> None:
        try:
            if files:
                subprocess.run(
                    ["git", "add", "--"] + files,
                    cwd=self.project_path,
                    check=True,
                    capture_output=True,
                    timeout=TIMEOUT_SUBPROCESS,
                )
            else:
                subprocess.run(
                    ["git", "add", "."],
                    cwd=self.project_path,
                    check=True,
                    capture_output=True,
                    timeout=TIMEOUT_SUBPROCESS,
                )
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.project_path,
                check=True,
                capture_output=True,
                timeout=TIMEOUT_SUBPROCESS,
            )
            if self.verbose:
                logger.info("💾 Committed: %s", message)
        except subprocess.CalledProcessError as e:
            logger.warning("Git commit failed: %s", e.stderr.decode(errors="replace").strip())

    def _run_self_review(self) -> int:
        """Run SelfReviewer on PLAN.md and return a numeric score."""
        if not self.plan_md.exists():
            return REVIEW_SCORE_NEUTRAL  # Can't review without a plan — neutral score

        try:
            from generator.planning.self_reviewer import SelfReviewer

            reviewer = SelfReviewer(provider=self.provider, api_key=self.api_key)
            report = reviewer.review(self.plan_md, project_path=self.project_path)

            score = self.review_score_from_verdict(report.verdict)
            # Save critique for traceability
            self.critiques_dir.mkdir(parents=True, exist_ok=True)
            critique_path = self.critiques_dir / f"iter-{self.state.iteration:03d}.md"
            critique_path.write_text(report.to_markdown(), encoding="utf-8")

            if self.verbose:
                logger.info("📝 Review: %s (score=%d)", report.verdict, score)
            return score
        except Exception as exc:  # noqa: BLE001 — self-review is best-effort; neutral fallback keeps loop running
            logger.warning("Self-review failed: %s — using neutral score.", exc)
            return REVIEW_SCORE_NEUTRAL

    def _run_tests(self) -> Tuple[bool, str]:
        """Run project tests; returns (passed, output)."""
        runner, args = self._detect_test_runner()
        if not runner:
            return True, "No test runner detected."

        try:
            result = subprocess.run(
                [runner] + args,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_TESTS,
            )
            passed = result.returncode == 0
            output = (result.stdout + result.stderr).strip()
            if self.verbose:
                icon = "✅" if passed else "❌"
                logger.info("%s Tests %s", icon, "passed" if passed else "FAILED")
            return passed, output
        except subprocess.TimeoutExpired:
            return False, f"Tests timed out after {TIMEOUT_TESTS}s."
        except FileNotFoundError:
            return True, f"Test runner '{runner}' not found — skipping."
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"Test execution error: {exc}"

    def _detect_test_runner(self) -> Tuple[Optional[str], list]:
        # Strong indicators: presence of these files always means pytest
        strong_indicators = ["pytest.ini", "setup.cfg", "conftest.py"]
        has_pytest = any((self.project_path / f).exists() for f in strong_indicators)
        # pyproject.toml alone is not sufficient (Rust/Node projects use it too);
        # only count it if it actually references pytest
        if not has_pytest:
            pyproject = self.project_path / "pyproject.toml"
            if pyproject.exists():
                try:
                    content = pyproject.read_text(encoding="utf-8", errors="replace")
                    has_pytest = "pytest" in content
                except OSError:
                    pass
        if has_pytest:
            return "pytest", ["-x", "-q"]
        if (self.project_path / "package.json").exists():
            return "npx", ["jest", "--passWithNoTests", "--bail"]
        return None, []

    def _next_task_title(self) -> Optional[str]:
        tasks = _load_tasks(self.tasks_yaml)
        pending = _pending_tasks(tasks)
        if not pending:
            return None
        return pending[0].get("title") or pending[0].get("description") or "(unnamed task)"

    def _mark_task_complete(self, title: str) -> None:
        tasks = _load_tasks(self.tasks_yaml)
        for t in tasks:
            if (t.get("title") or t.get("description")) == title and t.get("status") != "done":
                t["status"] = "done"
                break
        _save_tasks(self.tasks_yaml, tasks)

    def _git_log_oneline(self, n: int = 5) -> str:
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", f"-{n}"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_GIT,
            )
            return result.stdout.strip() or "(no commits yet)"
        except Exception:  # noqa: BLE001 — git may not be available; informational only
            return "(git log unavailable)"

    def _git_diff_names(self) -> str:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_GIT,
            )
            return result.stdout.strip() or "(no uncommitted changes)"
        except (OSError, subprocess.SubprocessError):
            return "(git diff unavailable)"

    def _create_pr(self) -> None:
        """Attempt to create a GitHub PR via gh CLI (best-effort)."""
        state = self.state
        title = f"Ralph: {state.task}"
        body = (
            f"Feature: {state.feature_id}\n"
            f"Status: {state.status}\n"
            f"Iterations: {state.iteration}/{state.max_iterations}\n"
            f"Tasks: {state.tasks_complete}/{state.tasks_total}\n"
            f"Last review score: {state.last_review_score}\n"
        )
        try:
            subprocess.run(
                ["gh", "pr", "create", "--title", title, "--body", body, "--head", state.branch_name],
                cwd=self.project_path,
                capture_output=True,
                timeout=TIMEOUT_SUBPROCESS,
            )
            if self.verbose:
                logger.info("📬 PR created for branch %s", state.branch_name)
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError) as exc:
            if self.verbose:
                logger.info("ℹ️  gh CLI unavailable — skipping auto-PR (%s).", exc)

    def _print_summary(self) -> None:
        s = self.state
        logger.info("\n%s", "=" * 60)
        logger.info("Ralph Loop: %s", self.feature_id)
        logger.info("   Status    : %s", s.status)
        logger.info("   Iterations: %d/%d", s.iteration, s.max_iterations)
        logger.info("   Tasks     : %d/%d complete", s.tasks_complete, s.tasks_total)
        logger.info("   Review    : %s", s.last_review_score)
        logger.info("   Exit      : %s", s.exit_condition or "—")
        logger.info("%s", "=" * 60)
