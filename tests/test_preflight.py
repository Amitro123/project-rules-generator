"""Tests for pre-flight checklist."""

from generator.planning.preflight import CheckResult, PreflightChecker, PreflightReport

# ---------------------------------------------------------------------------
# CheckResult / PreflightReport
# ---------------------------------------------------------------------------


class TestCheckResult:

    def test_passed(self):
        c = CheckResult(name="rules.json", passed=True, path="/a/b")
        assert c.passed
        assert c.path == "/a/b"

    def test_failed_with_fix(self):
        c = CheckResult(name="PLAN.md", passed=False, fix_command="prg plan x")
        assert not c.passed
        assert c.fix_command == "prg plan x"


class TestPreflightReport:

    def test_all_passed(self):
        r = PreflightReport(
            checks=[
                CheckResult(name="a", passed=True),
                CheckResult(name="b", passed=True),
            ]
        )
        assert r.all_passed
        assert len(r.failed_checks) == 0

    def test_some_failed(self):
        r = PreflightReport(
            checks=[
                CheckResult(name="a", passed=True),
                CheckResult(name="b", passed=False, fix_command="fix-b"),
            ]
        )
        assert not r.all_passed
        assert len(r.failed_checks) == 1
        assert r.failed_checks[0].name == "b"

    def test_format_report(self):
        r = PreflightReport(
            checks=[
                CheckResult(name="rules.json", passed=True, detail="Found."),
                CheckResult(
                    name="PLAN.md",
                    passed=False,
                    fix_command="prg plan x",
                    detail="Missing.",
                ),
            ]
        )
        text = r.format_report()
        assert "[PASS] rules.json" in text
        assert "[FAIL] PLAN.md" in text
        assert "Fix: prg plan x" in text
        assert "1 check(s) failed" in text


# ---------------------------------------------------------------------------
# PreflightChecker
# ---------------------------------------------------------------------------


class TestPreflightChecker:

    def _make_project(self, tmp_path, rules=True, skills=3, plan=True, tasks=True, design=True):
        """Create a minimal project structure for testing."""
        if rules:
            rules_dir = tmp_path / ".clinerules"
            rules_dir.mkdir(parents=True)
            (rules_dir / "rules.json").write_text("{}", encoding="utf-8")

        if skills > 0:
            skills_dir = tmp_path / ".clinerules" / "skills" / "learned"
            skills_dir.mkdir(parents=True, exist_ok=True)
            for i in range(skills):
                (skills_dir / f"skill-{i}.md").write_text(f"# Skill {i}", encoding="utf-8")

        if plan:
            (tmp_path / "PLAN.md").write_text("# PLAN\n", encoding="utf-8")

        if tasks:
            tasks_dir = tmp_path / "tasks"
            tasks_dir.mkdir(parents=True)
            (tasks_dir / "001-first.md").write_text("# Task 1", encoding="utf-8")

        if design:
            (tmp_path / "DESIGN.md").write_text("# Design\n", encoding="utf-8")

        return tmp_path

    def test_all_pass(self, tmp_path):
        proj = self._make_project(tmp_path)
        checker = PreflightChecker(proj, task_description="test")
        report = checker.run_checks()
        assert report.all_passed

    def test_no_rules(self, tmp_path):
        proj = self._make_project(tmp_path, rules=False)
        checker = PreflightChecker(proj)
        report = checker.run_checks()
        failed_names = [c.name for c in report.failed_checks]
        assert "Rules file" in failed_names

    def test_insufficient_skills(self, tmp_path):
        proj = self._make_project(tmp_path, skills=1)
        checker = PreflightChecker(proj)
        report = checker.run_checks()
        failed_names = [c.name for c in report.failed_checks]
        assert "Skills (3+)" in failed_names

    def test_no_skills_dir(self, tmp_path):
        proj = self._make_project(tmp_path, skills=0)
        checker = PreflightChecker(proj)
        report = checker.run_checks()
        failed_names = [c.name for c in report.failed_checks]
        assert "Skills (3+)" in failed_names

    def test_no_plan(self, tmp_path):
        proj = self._make_project(tmp_path, plan=False)
        checker = PreflightChecker(proj, task_description="Add cache")
        report = checker.run_checks()
        failed_names = [c.name for c in report.failed_checks]
        assert "PLAN.md" in failed_names

    def test_no_tasks(self, tmp_path):
        proj = self._make_project(tmp_path, tasks=False)
        checker = PreflightChecker(proj)
        report = checker.run_checks()
        failed_names = [c.name for c in report.failed_checks]
        assert "Task files" in failed_names

    def test_no_design(self, tmp_path):
        proj = self._make_project(tmp_path, design=False)
        checker = PreflightChecker(proj, task_description="Add cache")
        report = checker.run_checks()
        failed_names = [c.name for c in report.failed_checks]
        assert "DESIGN.md" in failed_names

    def test_fix_commands_present(self, tmp_path):
        proj = self._make_project(tmp_path, rules=False, plan=False, design=False, tasks=False, skills=0)
        checker = PreflightChecker(proj, task_description="Add cache")
        report = checker.run_checks()
        for c in report.failed_checks:
            assert c.fix_command is not None

    def test_slugify(self):
        assert PreflightChecker._slugify("Add Redis Cache") == "add-redis-cache"
        assert PreflightChecker._slugify("Hello World!!!") == "hello-world"

    def test_slug_based_plan_lookup(self, tmp_path):
        proj = self._make_project(tmp_path, plan=False)
        (tmp_path / "add-redis-PLAN.md").write_text("# Plan", encoding="utf-8")
        checker = PreflightChecker(proj, task_description="Add Redis")
        path = checker._find_plan_file()
        assert path is not None
        assert "add-redis" in path.name

    def test_slug_based_design_lookup(self, tmp_path):
        proj = self._make_project(tmp_path, design=False)
        (tmp_path / "add-redis-DESIGN.md").write_text("# Design", encoding="utf-8")
        checker = PreflightChecker(proj, task_description="Add Redis")
        path = checker._find_design_file()
        assert path is not None
        assert "add-redis" in path.name

    def test_rules_md_accepted(self, tmp_path):
        """prg init writes rules.md — preflight must accept it (CR0104 fix)."""
        proj = self._make_project(tmp_path, rules=False)
        clinerules = tmp_path / ".clinerules"
        clinerules.mkdir(parents=True, exist_ok=True)
        (clinerules / "rules.md").write_text("# Rules\n", encoding="utf-8")
        checker = PreflightChecker(proj)
        result = checker._check_rules_json()
        assert result.passed
        assert "rules.md" in result.detail

    def test_rules_json_still_accepted(self, tmp_path):
        """rules.json (from prg analyze) must still pass preflight."""
        proj = self._make_project(tmp_path)  # _make_project writes rules.json
        checker = PreflightChecker(proj)
        result = checker._check_rules_json()
        assert result.passed

    def test_no_rules_fix_command_points_to_init(self, tmp_path):
        """fix_command should suggest prg init when no rules file exists."""
        proj = self._make_project(tmp_path, rules=False)
        checker = PreflightChecker(proj)
        result = checker._check_rules_json()
        assert not result.passed
        assert "prg init" in result.fix_command
