"""Tests for task decomposition (Feature 4)."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch

from generator.task_decomposer import SubTask, TaskDecomposer
from main import cli


class TestSubTaskModel:
    """Test the SubTask Pydantic model."""

    def test_basic_creation(self):
        task = SubTask(id=1, title="Create auth module", goal="Add JWT auth")
        assert task.id == 1
        assert task.title == "Create auth module"
        assert task.estimated_minutes == 5  # default

    def test_full_creation(self):
        task = SubTask(
            id=2,
            title="Write tests",
            goal="Cover auth endpoints",
            files=["tests/test_auth.py"],
            changes=["Add login test", "Add token refresh test"],
            tests=["pytest tests/test_auth.py"],
            dependencies=[1],
            estimated_minutes=3,
        )
        assert task.files == ["tests/test_auth.py"]
        assert task.dependencies == [1]
        assert task.estimated_minutes == 3

    def test_estimated_minutes_clamped(self):
        task = SubTask(id=1, title="T", goal="G", estimated_minutes=1)
        assert task.estimated_minutes == 1

        with pytest.raises(Exception):
            SubTask(id=1, title="T", goal="G", estimated_minutes=0)


class TestTaskDecomposer:
    """Test TaskDecomposer without AI (no API key)."""

    def test_decompose_fallback_no_api_key(self):
        """Without API key, should return a single fallback subtask."""
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer.decompose("Add authentication to the API")

        assert len(tasks) >= 1
        assert tasks[0].id == 1
        assert "authentication" in tasks[0].title.lower() or "authentication" in tasks[0].goal.lower()

    def test_decompose_with_project_context(self):
        """Context should not crash the decomposer."""
        ctx = {
            "metadata": {
                "project_type": "fastapi-api",
                "tech_stack": ["python", "fastapi"],
                "has_tests": True,
            },
            "structure": {
                "entry_points": ["app/main.py"],
            },
        }
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer.decompose("Add caching layer", project_context=ctx)

        assert len(tasks) >= 1


class TestGeneratePlanMd:
    """Test plan markdown generation."""

    def test_basic_plan(self):
        tasks = [
            SubTask(
                id=1,
                title="Create module",
                goal="New auth module",
                files=["auth.py"],
                changes=["Add JWT logic"],
                tests=["test auth"],
                estimated_minutes=5,
            ),
            SubTask(
                id=2,
                title="Write tests",
                goal="Cover auth",
                files=["tests/test_auth.py"],
                dependencies=[1],
                estimated_minutes=3,
            ),
        ]
        md = TaskDecomposer.generate_plan_md(tasks, user_task="Add auth")

        assert "# PLAN" in md
        assert "Add auth" in md
        assert "## 1. Create module" in md
        assert "## 2. Write tests" in md
        assert "`auth.py`" in md
        assert "#1" in md  # dependency reference
        assert "8 minutes" in md  # 5 + 3

    def test_plan_without_user_task(self):
        tasks = [SubTask(id=1, title="Do thing", goal="A goal", estimated_minutes=2)]
        md = TaskDecomposer.generate_plan_md(tasks)

        assert "# PLAN" in md
        # The header should not have a "> **Goal:**" blockquote when user_task is empty
        assert "> **Goal:**" not in md

    def test_plan_empty_tasks(self):
        md = TaskDecomposer.generate_plan_md([], user_task="Test")
        assert "# PLAN" in md
        assert "0" in md  # 0 subtasks

    def test_plan_skip_consequence_rendered(self):
        """generate_plan_md() must render **Skip consequence:** when the field is set."""
        tasks = [
            SubTask(
                id=1,
                title="Write tests",
                goal="Cover the feature",
                skip_consequence="Regressions ship undetected",
                estimated_minutes=3,
            )
        ]
        md = TaskDecomposer.generate_plan_md(tasks, user_task="Add feature")

        assert "**Skip consequence:**" in md
        assert "Regressions ship undetected" in md

    def test_plan_skip_consequence_omitted_when_empty(self):
        """generate_plan_md() must NOT emit the Skip consequence line when field is empty."""
        tasks = [
            SubTask(id=1, title="Do thing", goal="A goal", estimated_minutes=2)
        ]
        md = TaskDecomposer.generate_plan_md(tasks)

        assert "**Skip consequence:**" not in md


class TestParseResponse:
    """Test parsing of LLM-style responses."""

    def test_parse_well_formed_response(self):
        raw = """### 1. Set up database
Goal: Create database schema
Files: db/schema.py, db/models.py
Changes:
- Add User model
- Add migration script
Tests:
- Test model creation
Dependencies: none
Estimated: 3

### 2. Add API routes
Goal: Create CRUD endpoints
Files: routes/users.py
Changes:
- Add GET /users
- Add POST /users
Tests:
- Test endpoints
Dependencies: 1
Estimated: 4
"""
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer._parse_response(raw, "Set up user system")

        assert len(tasks) == 2
        assert tasks[0].id == 1
        assert tasks[0].title == "Set up database"
        assert "db/schema.py" in tasks[0].files
        assert tasks[1].dependencies == [1]
        assert tasks[1].estimated_minutes == 4

    def test_parse_empty_response_returns_fallback(self):
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer._parse_response("", "Some task")

        assert len(tasks) == 1
        assert tasks[0].goal == "Some task"

    def test_parse_malformed_response_returns_fallback(self):
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer._parse_response("Just some random text\nwith no structure", "Fallback task")

        assert len(tasks) >= 1

    def test_parse_skip_consequence_extracted(self):
        """_parse_response() must populate skip_consequence from SkipConsequence: field."""
        raw = """### 1. Add authentication middleware
Goal: Protect all API endpoints
SkipConsequence: All endpoints remain publicly accessible; security audit will fail
Files: middleware/auth.py
Changes:
- Add JWT validation
Tests:
- Test auth middleware
Dependencies: none
Estimated: 4
"""
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer._parse_response(raw, "Add auth")

        assert len(tasks) == 1
        assert "publicly accessible" in tasks[0].skip_consequence

    def test_parse_skip_consequence_empty_when_absent(self):
        """skip_consequence defaults to empty string when field not in response."""
        raw = """### 1. Create module
Goal: Build the core module
Files: core.py
Changes:
- Add main logic
Tests:
- pytest core
Dependencies: none
Estimated: 3
"""
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer._parse_response(raw, "Build module")

        assert tasks[0].skip_consequence == ""

    def test_parse_skip_consequence_multiple_tasks(self):
        """skip_consequence is extracted independently for each task in a response."""
        raw = """### 1. Write tests
Goal: Cover the new endpoint
SkipConsequence: Regressions go undetected in CI
Files: tests/test_api.py
Changes:
- Add endpoint tests
Tests:
- pytest tests/test_api.py
Dependencies: none
Estimated: 3

### 2. Implement endpoint
Goal: Add the POST /items route
Files: api/items.py
Changes:
- Add route handler
Tests:
- pytest tests/test_api.py
Dependencies: 1
Estimated: 4
"""
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer._parse_response(raw, "Add items endpoint")

        assert tasks[0].skip_consequence == "Regressions go undetected in CI"
        assert tasks[1].skip_consequence == ""


class TestFromDesign:
    """Test generating tasks from a DESIGN.md file."""

    @pytest.fixture(autouse=True)
    def mock_llm(self):
        """Prevent live Gemini calls regardless of env vars."""
        with patch.object(TaskDecomposer, "_call_llm", return_value=""):
            yield

    def _write_design(self, tmp_path):
        design_md = """# Design: Auth System

## Problem Statement
Users need secure access to API endpoints.

## Architecture Decisions
- **Auth Method**: JWT tokens (vs sessions)
  - Pro: Stateless
  - Con: Token revocation complexity

## API Contracts
- POST /auth/login -> {token, expires_at}
- GET /api/* -> requires Authorization header

## Data Models
- User: id, email, password_hash, created_at

## Success Criteria
- All endpoints require auth except /auth/*
- Tokens expire after 24h
"""
        path = tmp_path / "DESIGN.md"
        path.write_text(design_md, encoding="utf-8")
        return path

    def test_from_design_creates_tasks(self, tmp_path):
        design_path = self._write_design(tmp_path)
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer.from_design(design_path)

        assert len(tasks) >= 2
        # Should have tasks for architecture decision, data model, API contracts, verification
        titles = " ".join(t.title.lower() for t in tasks)
        assert "auth" in titles or "implement" in titles

    def test_from_design_includes_verification_task(self, tmp_path):
        design_path = self._write_design(tmp_path)
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer.from_design(design_path)

        # Last task should verify success criteria
        last = tasks[-1]
        assert "verif" in last.title.lower() or "criteria" in last.title.lower()
        assert len(last.tests) >= 1

    def test_from_design_tasks_have_dependencies(self, tmp_path):
        design_path = self._write_design(tmp_path)
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer.from_design(design_path)

        # Verification task depends on others
        last = tasks[-1]
        assert len(last.dependencies) >= 1

    def test_from_design_minimal(self, tmp_path):
        """A design with only a problem statement still produces at least one task."""
        (tmp_path / "DESIGN.md").write_text(
            "# Design: Quick Fix\n\n## Problem Statement\nFix the bug.\n",
            encoding="utf-8",
        )
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer.from_design(tmp_path / "DESIGN.md")
        assert len(tasks) >= 1


class TestPlanCLI:
    """Test the plan CLI command."""

    def test_plan_command_in_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["plan", "--help"])

        assert result.exit_code == 0
        assert "--from-design" in result.output
        assert "--output" in result.output

    def test_plan_generates_file(self, tmp_path):
        """Plan command should create a PLAN.md file."""
        (tmp_path / "README.md").write_text("# Test Project\n\nA project.")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "plan",
                "Add user authentication",
                "--project-path",
                str(tmp_path),
                "--output",
                "PLAN.md",
                "--verbose",
            ],
        )

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}\n{result.exception}"
        plan_path = tmp_path / "PLAN.md"
        assert plan_path.exists()
        content = plan_path.read_text(encoding="utf-8")
        assert "# PLAN" in content
        assert "authentication" in content.lower()

    def test_plan_custom_output(self, tmp_path):
        (tmp_path / "README.md").write_text("# Test\n\nDesc.")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "plan",
                "Refactor database",
                "--project-path",
                str(tmp_path),
                "--output",
                "docs/PLAN.md",
            ],
        )

        assert result.exit_code == 0
        assert (tmp_path / "docs" / "PLAN.md").exists()

    def test_plan_from_design_flag(self, tmp_path):
        """Plan from a DESIGN.md file."""
        (tmp_path / "README.md").write_text("# Test\n\nDesc.")
        design_md = (
            "# Design: Auth System\n\n"
            "## Problem Statement\nNeed auth.\n\n"
            "## Architecture Decisions\n"
            "- **Method**: JWT tokens (vs sessions)\n"
            "  - Pro: Stateless\n\n"
            "## Success Criteria\n"
            "- All endpoints require auth\n"
        )
        design_path = tmp_path / "DESIGN.md"
        design_path.write_text(design_md, encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "plan",
                "--from-design",
                str(design_path),
                "--project-path",
                str(tmp_path),
                "--output",
                "PLAN.md",
                "--verbose",
            ],
        )

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}\n{result.exception}"
        plan_path = tmp_path / "PLAN.md"
        assert plan_path.exists()
        content = plan_path.read_text(encoding="utf-8")
        assert "# PLAN" in content
        assert "Auth System" in content

    def test_plan_requires_task_or_design(self, tmp_path):
        """Plan without task or --from-design should fail."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "plan",
                "--project-path",
                str(tmp_path),
            ],
        )
        assert result.exit_code != 0
