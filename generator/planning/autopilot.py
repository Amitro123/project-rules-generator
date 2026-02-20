"""Autopilot orchestrator — manages the end-to-end discovery and execution loop."""


import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import click

from generator.planning.task_agent import TaskImplementationAgent
from generator.planning.task_creator import TaskManifest
from generator.planning.task_executor import TaskExecutor
from generator.planning.workflow import AgentWorkflow
from generator.task_decomposer import SubTask
from prg_utils import git_ops


class AutopilotOrchestrator:
    """Manages the full end-to-end autopilot workflow."""

    def __init__(
        self,
        project_path: Path,
        provider: str = "groq",
        api_key: Optional[str] = None,
        verbose: bool = True,
    ):
        self.project_path = Path(project_path).resolve()
        self.provider = provider
        self.api_key = api_key
        self.verbose = verbose
        self.workflow = None
        self.manifest_path = self.project_path / "tasks" / "TASKS.yaml"

    def discovery(self, task_description: str = "Complete project") -> TaskManifest:
        """PHASE 1: Discovery (rules + skills + plan + tasks)."""
        if self.verbose:
            click.echo(f"🔍 Discovery Phase: {task_description}")

        self.workflow = AgentWorkflow(
            project_path=self.project_path,
            task_description=task_description,
            provider=self.provider,
            api_key=self.api_key,
            verbose=self.verbose,
        )

        manifest = self.workflow.run_setup()
        return manifest

    def execution_loop(self, manifest: TaskManifest):
        """PHASE 2: Supervised Execution Loop.

        Per-task flow:
            1. Create git branch
            2. Agent implements changes
            3. Run tests → show results
            4. Show diff summary to user
            5. User: approve → merge | retry → redo | skip → next | stop → exit
        """
        if self.verbose:
            click.echo("🚀 Starting Supervised Execution Loop...")

        executor = TaskExecutor(manifest)
        agent = TaskImplementationAgent(provider=self.provider, api_key=self.api_key)

        main_branch = None
        try:
            main_branch = git_ops.get_current_branch(self.project_path)
        except Exception:
            if self.verbose:
                click.echo("⚠️  Not a git repository or git not found. Safety features disabled.")

        completed = 0
        skipped = 0

        while True:
            nxt = executor.get_next_task()
            if not nxt:
                self._print_summary(completed, skipped)
                break

            click.echo(f"\n{'='*60}")
            click.echo(f"🎯  Task #{nxt.id}: {nxt.title}")
            click.echo(f"{'='*60}")

            branch_name = f"autopilot/task-{nxt.id}"
            if main_branch:
                try:
                    git_ops.create_branch(branch_name, self.project_path)
                    click.echo(f"🌿 Branch: {branch_name}")
                except Exception as e:
                    click.echo(f"⚠️  Branch creation failed: {e}")

            try:
                executor.execute_single(nxt.id)
                subtask = self._load_subtask_details(nxt)

                click.echo("🤖 Agent implementing changes...")
                changes = agent.implement(
                    subtask,
                    project_context=self.workflow._get_project_context() if self.workflow else None,
                )

                for fpath, content in changes.items():
                    full_path = self.project_path / fpath
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    click.echo(f"   ✅ {fpath}")

                # Run tests after every implementation
                tests_passed, test_output = self._run_tests(subtask)
                self._print_test_results(tests_passed, test_output)

                # User decision loop
                action = self._ask_user(nxt.title, subtask.goal, tests_passed)

                if action == "approve":
                    executor.complete_task(nxt.id)
                    executor.save(self.manifest_path)
                    if main_branch:
                        git_ops.checkout(main_branch, self.project_path)
                        git_ops.merge_branch(branch_name, self.project_path)
                        git_ops.delete_branch(branch_name, force=True, repo_path=self.project_path)
                        click.echo(f"✅ Task #{nxt.id} merged.")
                    completed += 1

                elif action == "skip":
                    click.echo(f"⏭️  Skipping task #{nxt.id}.")
                    if main_branch:
                        git_ops.checkout(main_branch, self.project_path)
                        git_ops.delete_branch(branch_name, force=True, repo_path=self.project_path)
                    skipped += 1

                else:  # stop
                    click.echo("🛑 Autopilot stopped by user.")
                    if main_branch:
                        git_ops.checkout(main_branch, self.project_path)
                        git_ops.delete_branch(branch_name, force=True, repo_path=self.project_path)
                        git_ops.rollback_to_head(self.project_path)
                    self._print_summary(completed, skipped)
                    break

            except Exception as e:
                click.echo(f"❌ Task #{nxt.id} failed: {e}")
                if main_branch:
                    git_ops.checkout(main_branch, self.project_path)
                    git_ops.rollback_to_head(self.project_path)
                break

    # ── Private helpers ───────────────────────────────────────────────────────

    def _run_tests(self, subtask: SubTask) -> Tuple[bool, str]:
        """Run the project test suite and return (passed, output).

        Detects test runner from project config (pytest > jest > none).
        Scope: runs only tests related to subtask files when possible,
        otherwise falls back to full suite.
        """
        runner, args = self._detect_test_runner(subtask)
        if not runner:
            return True, "No test runner detected — skipping."

        click.echo(f"\n🧪 Running tests: {' '.join([runner] + args)}")
        try:
            result = subprocess.run(
                [runner] + args,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            passed = result.returncode == 0
            output = (result.stdout + result.stderr).strip()
            return passed, output
        except subprocess.TimeoutExpired:
            return False, "Tests timed out after 120s."
        except FileNotFoundError:
            return True, f"Test runner '{runner}' not found — skipping."
        except Exception as e:
            return False, f"Test execution error: {e}"

    def _detect_test_runner(self, subtask: SubTask) -> Tuple[Optional[str], list]:
        """Return (runner, args) based on project config and subtask files."""
        # pytest
        has_pytest = any(
            (self.project_path / f).exists()
            for f in ["pytest.ini", "pyproject.toml", "setup.cfg", "conftest.py"]
        )
        if has_pytest:
            args = ["-x", "-q"]
            # Narrow scope to affected test files if available
            test_files = [
                f for f in (subtask.files or [])
                if "test" in f
            ]
            if test_files:
                args += test_files
            return "pytest", args

        # jest
        if (self.project_path / "package.json").exists():
            return "npx", ["jest", "--passWithNoTests", "--bail"]

        return None, []

    def _print_test_results(self, passed: bool, output: str) -> None:
        """Print a concise test result block."""
        icon = "✅" if passed else "❌"
        label = "Tests passed" if passed else "Tests FAILED"
        click.echo(f"\n{icon} {label}")
        # Show last 15 lines — enough to see failures without flooding terminal
        lines = output.splitlines()
        if lines:
            click.echo("\n".join(lines[-15:]))

    def _ask_user(self, title: str, goal: str, tests_passed: bool) -> str:
        """Interactive prompt after implementation + test run.

        Returns: 'approve' | 'skip' | 'stop'
        """
        click.echo(f"\n📋 Task: {title}")
        click.echo(f"   Goal: {goal}")
        if not tests_passed:
            click.echo("   ⚠️  Tests failed — review changes before approving.")

        click.echo("\nWhat would you like to do?")
        click.echo("  [a] Approve & merge")
        click.echo("  [s] Skip this task")
        click.echo("  [q] Stop autopilot")

        while True:
            choice = click.prompt("Choice", default="a").strip().lower()
            if choice in ("a", "approve", "y", "yes"):
                return "approve"
            if choice in ("s", "skip"):
                return "skip"
            if choice in ("q", "quit", "stop", "n", "no"):
                return "stop"
            click.echo("Please enter a, s, or q.")

    def _print_summary(self, completed: int, skipped: int) -> None:
        """Print end-of-run summary."""
        click.echo(f"\n{'='*60}")
        click.echo("🎉 Autopilot run complete")
        click.echo(f"   ✅ Completed : {completed}")
        click.echo(f"   ⏭️  Skipped   : {skipped}")
        click.echo(f"{'='*60}")

    def _load_subtask_details(self, entry) -> SubTask:
        """Load full SubTask details from the task file."""
        task_file = self.project_path / "tasks" / entry.file
        content = task_file.read_text(encoding="utf-8")

        goal_match = re.search(r"\*\*Goal:\*\*\s*(.+)", content)
        goal = goal_match.group(1).strip() if goal_match else entry.title

        files = []
        files_section = re.search(r"## Files\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if files_section:
            files = re.findall(r"-\s+`(.+?)`", files_section.group(1))

        changes = []
        changes_section = re.search(r"## Changes\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if changes_section:
            changes = re.findall(r"-\s+(.+)", changes_section.group(1))

        tests = []
        tests_section = re.search(r"## Tests\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if tests_section:
            tests = re.findall(r"-\s+(.+)", tests_section.group(1))

        return SubTask(
            id=entry.id,
            title=entry.title,
            goal=goal,
            files=files,
            changes=changes,
            tests=tests,
            dependencies=entry.dependencies,
            estimated_minutes=entry.estimated_minutes,
            type=task_file.suffix.replace(".", ""),
        )
