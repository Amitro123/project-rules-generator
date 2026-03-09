"""Agent workflow orchestrator — ties plan, tasks, preflight, and execution together."""

import os
from pathlib import Path
from typing import Dict, Optional

import click

from .preflight import PreflightChecker, PreflightReport
from .task_creator import TaskCreator, TaskManifest
from .task_executor import TaskExecutor


class AgentWorkflow:
    """Top-level orchestrator for ``prg start``.

    Steps:
        1. Generate or locate PLAN.md  (``_find_or_create_plan``)
        2. Create task files            (``_create_task_files``)
        3. Run pre-flight checklist     (``_preflight``)
        4. Auto-fix missing artifacts   (``_auto_fix``)
        5. Return manifest for execution
    """

    def __init__(
        self,
        project_path: Path,
        task_description: str,
        provider: str = "groq",
        api_key: Optional[str] = None,
        verbose: bool = True,
    ):
        self.project_path = Path(project_path).resolve()
        self.task_description = task_description
        self.provider = provider
        self.api_key = api_key
        self.verbose = verbose

    # -- Public entry points ---------------------------------------------

    def run_setup(self) -> TaskManifest:
        """Steps 1-4: plan + tasks + preflight + auto-fix.

        Returns the manifest (with tasks/ directory populated).
        """
        plan_path = self._find_or_create_plan()
        manifest = self._create_task_files(plan_path)

        report = self._preflight()
        if not report.all_passed:
            self._auto_fix(report)
            # Re-check after fixes
            report = self._preflight()

        if self.verbose:
            click.echo(report.format_report())

        return manifest

    def run_full(self) -> TaskManifest:
        """Steps 1-5: setup + return manifest ready for execution."""
        manifest = self.run_setup()
        if self.verbose:
            executor = TaskExecutor(manifest)
            summary = executor.get_progress_summary()
            click.echo(f"\nReady: {summary['total']} tasks, ~{summary['est_remaining_minutes']} min estimated")
            nxt = executor.get_next_task()
            if nxt:
                click.echo(f"Next task: #{nxt.id} {nxt.title}")
                click.echo(f"  Run: prg exec tasks/{nxt.file}")
        return manifest

    # -- Internal steps ---------------------------------------------------

    def _preflight(self) -> PreflightReport:
        """Run the pre-flight checklist."""
        checker = PreflightChecker(
            self.project_path,
            task_description=self.task_description,
        )
        return checker.run_checks()

    def _auto_fix(self, report: PreflightReport) -> None:
        """Attempt to fix failed checks by invoking generators directly."""
        for check in report.failed_checks:
            if check.name == "rules.md":
                self._fix_analyze()
            elif check.name == "Skills (3+)":
                self._fix_analyze()
            elif check.name == "DESIGN.md":
                self._fix_design()
            elif check.name == "PLAN.md":
                # Plan is created in _find_or_create_plan; skip here
                pass
            elif check.name == "Task files":
                # Task files are created in _create_task_files; skip here
                pass

    def _find_or_create_plan(self) -> Path:
        """Find an existing PLAN.md or generate a new one."""
        checker = PreflightChecker(self.project_path, self.task_description)
        plan_path = checker._find_plan_file()

        if plan_path and plan_path.exists():
            if self.verbose:
                click.echo(f"Using existing plan: {plan_path.name}")
            return plan_path

        if self.verbose:
            click.echo("Generating plan...")

        return self._generate_plan()

    def _generate_plan(self) -> Path:
        """Generate PLAN.md via TaskDecomposer."""
        from generator.task_decomposer import TaskDecomposer

        api_key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")
        decomposer = TaskDecomposer(api_key=api_key, provider=self.provider)

        # Gather project context
        enhanced_context = self._get_project_context()

        subtasks = decomposer.decompose(
            self.task_description,
            project_context=enhanced_context,
            project_path=self.project_path,
        )

        plan_md = decomposer.generate_plan_md(subtasks, user_task=self.task_description)
        plan_path = self.project_path / "PLAN.md"
        plan_path.write_text(plan_md, encoding="utf-8")

        if self.verbose:
            click.echo(f"Plan generated: {len(subtasks)} subtasks -> {plan_path.name}")

        return plan_path

    def _create_task_files(self, plan_path: Path) -> TaskManifest:
        """Create tasks/ directory from an existing plan."""
        tasks_yaml = self.project_path / "tasks" / "TASKS.yaml"

        # Idempotent: reuse existing manifest
        if tasks_yaml.exists():
            if self.verbose:
                click.echo(f"Using existing task manifest: {tasks_yaml}")
            return TaskManifest.from_yaml(tasks_yaml)

        # Parse subtasks from the plan
        subtasks = self._parse_plan_subtasks(plan_path)

        creator = TaskCreator()
        manifest = creator.create_from_subtasks(
            subtasks=subtasks,
            plan_file=plan_path.name,
            task_description=self.task_description,
            output_dir=self.project_path / "tasks",
        )

        if self.verbose:
            click.echo(f"Created {len(manifest.tasks)} task files in tasks/")

        return manifest

    def _parse_plan_subtasks(self, plan_path: Path):
        """Extract SubTask objects from an existing PLAN.md (no AI call)."""
        from generator.task_decomposer import TaskDecomposer

        content = plan_path.read_text(encoding="utf-8")
        return TaskDecomposer._parse_response(content, self.task_description)

    # -- Auto-fix helpers -------------------------------------------------

    def _fix_analyze(self) -> None:
        """Run the analyze pipeline to generate rules + skills."""
        if self.verbose:
            click.echo("Auto-fixing: running analyze...")

        readme_path = self.project_path / "README.md"
        if not readme_path.exists():
            if self.verbose:
                click.echo("  Skipped: no README.md found for analyze.")
            return

        try:
            from generator.rules_generator import RulesGenerator

            output_dir = self.project_path / ".clinerules"
            output_dir.mkdir(parents=True, exist_ok=True)

            generator = RulesGenerator(self.project_path)
            output_path, _metadata, _quality = generator.create_rules(output_dir=output_dir)

            if self.verbose:
                click.echo(f"  Generated {output_path.name}")
        except Exception as exc:
            if self.verbose:
                click.echo(f"  Analyze auto-fix failed: {exc}")

    def _fix_design(self) -> None:
        """Generate a DESIGN.md for the task."""
        if self.verbose:
            click.echo("Auto-fixing: generating design...")

        try:
            from generator.design_generator import DesignGenerator

            generator = DesignGenerator(
                api_key=self.api_key,
                provider=self.provider,
            )
            enhanced_context = self._get_project_context()

            design_obj = generator.generate_design(
                self.task_description,
                project_context=enhanced_context,
                project_path=self.project_path,
            )

            design_path = self.project_path / "DESIGN.md"
            design_path.write_text(design_obj.to_markdown(), encoding="utf-8")

            if self.verbose:
                click.echo(f"  Generated DESIGN.md: {design_obj.title}")
        except Exception as exc:
            if self.verbose:
                click.echo(f"  Design auto-fix failed: {exc}")

    # -- Shared helpers ---------------------------------------------------

    def _get_project_context(self) -> Optional[Dict]:
        """Extract project context using EnhancedProjectParser."""
        try:
            from generator.parsers.enhanced_parser import EnhancedProjectParser

            parser = EnhancedProjectParser(self.project_path)
            return parser.extract_full_context()
        except Exception:
            return None
