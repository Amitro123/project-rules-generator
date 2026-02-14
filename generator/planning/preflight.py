"""Pre-flight checklist — verify required artifacts exist before execution."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class CheckResult:
    """Result of a single pre-flight check."""

    name: str
    passed: bool
    path: Optional[str] = None
    fix_command: Optional[str] = None
    detail: str = ""


@dataclass
class PreflightReport:
    """Aggregated results of all pre-flight checks."""

    checks: List[CheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.passed]

    def format_report(self) -> str:
        """Render a human-readable report."""
        lines = ["Pre-flight Checklist", "=" * 40, ""]
        for c in self.checks:
            icon = "[PASS]" if c.passed else "[FAIL]"
            lines.append(f"  {icon} {c.name}")
            if c.detail:
                lines.append(f"        {c.detail}")
            if not c.passed and c.fix_command:
                lines.append(f"        Fix: {c.fix_command}")
        lines.append("")
        if self.all_passed:
            lines.append("All checks passed.")
        else:
            lines.append(f"{len(self.failed_checks)} check(s) failed.")
        return "\n".join(lines)


class PreflightChecker:
    """Run pre-flight checks for a project before task execution."""

    def __init__(
        self,
        project_path: Path,
        task_description: str = "",
    ):
        self.project_path = Path(project_path).resolve()
        self.task_description = task_description

    def run_checks(self) -> PreflightReport:
        """Run all pre-flight checks and return a report."""
        report = PreflightReport()
        report.checks.append(self._check_rules_json())
        report.checks.append(self._check_skills())
        report.checks.append(self._check_plan())
        report.checks.append(self._check_task_files())
        report.checks.append(self._check_design())
        return report

    # -- Individual checks ------------------------------------------------

    def _check_rules_json(self) -> CheckResult:
        """Check that rules.json exists in .clinerules/."""
        candidates = [
            self.project_path / ".clinerules" / "rules.json",
            self.project_path / "rules.json",
        ]
        for p in candidates:
            if p.exists():
                return CheckResult(
                    name="rules.json",
                    passed=True,
                    path=str(p),
                    detail="Project rules found.",
                )
        return CheckResult(
            name="rules.json",
            passed=False,
            fix_command="prg analyze .",
            detail="No rules.json found. Run analyze first.",
        )

    def _check_skills(self) -> CheckResult:
        """Check that at least 3 skill files exist."""
        skills_dir = self.project_path / ".clinerules" / "skills" / "learned"
        if not skills_dir.is_dir():
            return CheckResult(
                name="Skills (3+)",
                passed=False,
                fix_command="prg analyze .",
                detail="No skills directory found.",
            )
        md_files = list(skills_dir.glob("*.md"))
        count = len(md_files)
        if count >= 3:
            return CheckResult(
                name="Skills (3+)",
                passed=True,
                path=str(skills_dir),
                detail=f"{count} skill(s) found.",
            )
        return CheckResult(
            name="Skills (3+)",
            passed=False,
            fix_command="prg analyze .",
            detail=f"Only {count} skill(s) found (need 3+).",
        )

    def _check_plan(self) -> CheckResult:
        """Check that a PLAN.md exists."""
        plan_path = self._find_plan_file()
        if plan_path:
            return CheckResult(
                name="PLAN.md",
                passed=True,
                path=str(plan_path),
                detail="Plan file found.",
            )
        fix_cmd = (
            f'prg plan "{self.task_description}"'
            if self.task_description
            else "prg plan <task>"
        )
        return CheckResult(
            name="PLAN.md",
            passed=False,
            fix_command=fix_cmd,
            detail="No plan file found.",
        )

    def _check_task_files(self) -> CheckResult:
        """Check that tasks/001-*.md exists."""
        tasks_dir = self.project_path / "tasks"
        if not tasks_dir.is_dir():
            return CheckResult(
                name="Task files",
                passed=False,
                fix_command="prg setup <task>",
                detail="No tasks/ directory found.",
            )
        task_files = sorted(tasks_dir.glob("0*.md"))
        if task_files:
            return CheckResult(
                name="Task files",
                passed=True,
                path=str(tasks_dir),
                detail=f"{len(task_files)} task file(s) found.",
            )
        return CheckResult(
            name="Task files",
            passed=False,
            fix_command="prg setup <task>",
            detail="No task files in tasks/ directory.",
        )

    def _check_design(self) -> CheckResult:
        """Check that a DESIGN.md exists."""
        design_path = self._find_design_file()
        if design_path:
            return CheckResult(
                name="DESIGN.md",
                passed=True,
                path=str(design_path),
                detail="Design document found.",
            )
        fix_cmd = (
            f'prg design "{self.task_description}"'
            if self.task_description
            else "prg design <task>"
        )
        return CheckResult(
            name="DESIGN.md",
            passed=False,
            fix_command=fix_cmd,
            detail="No design document found.",
        )

    # -- Helpers ----------------------------------------------------------

    def _find_plan_file(self) -> Optional[Path]:
        """Find a PLAN.md file, trying slug-based name first."""
        if self.task_description:
            slug = self._slugify(self.task_description)
            candidate = self.project_path / f"{slug}-PLAN.md"
            if candidate.exists():
                return candidate

        for pattern in ["PLAN.md", "*-PLAN.md", "PLAN-*.md"]:
            matches = sorted(self.project_path.glob(pattern))
            if matches:
                return matches[0]
        return None

    def _find_design_file(self) -> Optional[Path]:
        """Find a DESIGN.md file, trying slug-based name first."""
        if self.task_description:
            slug = self._slugify(self.task_description)
            candidate = self.project_path / f"{slug}-DESIGN.md"
            if candidate.exists():
                return candidate

        for pattern in ["DESIGN.md", "*-DESIGN.md", "DESIGN-*.md"]:
            matches = sorted(self.project_path.glob(pattern))
            if matches:
                return matches[0]
        return None

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to a filename-friendly slug."""
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return slug[:60]
