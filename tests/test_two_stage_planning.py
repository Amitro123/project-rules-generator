"""Integration tests for the two-stage planning workflow (design -> plan)."""

from click.testing import CliRunner

from generator.design_generator import ArchitectureDecision, Design, DesignGenerator
from generator.task_decomposer import TaskDecomposer
from main import cli


class TestTwoStageWorkflow:
    """Test the full design -> plan -> verify workflow."""

    def test_design_then_plan(self, tmp_path):
        """Stage 1: design, Stage 2: plan from design."""
        (tmp_path / "README.md").write_text("# My API\n\nA FastAPI project.")

        runner = CliRunner()

        # Stage 1: Generate design
        result1 = runner.invoke(
            cli,
            [
                "design",
                "Add rate limiting middleware",
                "--project-path",
                str(tmp_path),
                "--output",
                "DESIGN.md",
                "--verbose",
            ],
        )
        assert result1.exit_code == 0, f"Design failed: {result1.output}\n{result1.exception}"

        design_path = tmp_path / "DESIGN.md"
        assert design_path.exists()
        design_content = design_path.read_text(encoding="utf-8")
        assert "# Design:" in design_content

        # Stage 2: Generate plan from design
        result2 = runner.invoke(
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
        assert result2.exit_code == 0, f"Plan failed: {result2.output}\n{result2.exception}"

        plan_path = tmp_path / "PLAN.md"
        assert plan_path.exists()
        plan_content = plan_path.read_text(encoding="utf-8")
        assert "# PLAN" in plan_content
        assert "Subtasks" in plan_content or "subtask" in plan_content.lower()

    def test_design_roundtrip_preserves_decisions(self):
        """Design -> markdown -> parse -> tasks should preserve architecture decisions."""
        design = Design(
            title="Auth System",
            problem_statement="Secure the API.",
            architecture_decisions=[
                ArchitectureDecision(
                    title="Token Type",
                    choice="JWT",
                    alternatives=["sessions", "API keys"],
                    pros=["Stateless"],
                    cons=["Revocation hard"],
                ),
                ArchitectureDecision(
                    title="Storage",
                    choice="PostgreSQL",
                    alternatives=["MongoDB"],
                    pros=["ACID"],
                    cons=["Schema migrations"],
                ),
            ],
            api_contracts=[
                "POST /auth/login -> {token}",
                "POST /auth/refresh -> {token}",
            ],
            data_models=["User: id, email, password_hash"],
            success_criteria=["Login returns valid JWT", "Refresh extends session"],
        )

        # Render and reparse
        md = design.to_markdown()
        parsed = Design.from_markdown(md)

        assert parsed.title == "Auth System"
        assert len(parsed.architecture_decisions) == 2
        assert parsed.architecture_decisions[0].choice == "JWT"
        assert parsed.architecture_decisions[1].choice == "PostgreSQL"

        # Generate tasks from design
        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer._tasks_from_design(parsed)

        # Should have: 2 arch decisions + 1 data model + 2 API contracts + 1 verification = 6
        assert len(tasks) >= 5
        # Last task should be verification
        assert "verif" in tasks[-1].title.lower() or "criteria" in tasks[-1].title.lower()
        assert len(tasks[-1].tests) == 2  # two success criteria

    def test_plan_from_design_generates_coherent_plan(self, tmp_path):
        """Tasks generated from design should reference design content."""
        design = Design(
            title="Caching Layer",
            problem_statement="API responses are too slow.",
            architecture_decisions=[
                ArchitectureDecision(
                    title="Cache Backend",
                    choice="Redis",
                    alternatives=["Memcached"],
                    pros=["Rich data types"],
                    cons=["Extra infra"],
                ),
            ],
            api_contracts=["GET /api/cached/* -> cached response"],
            success_criteria=["Cache hit rate > 80%"],
        )

        design_path = tmp_path / "DESIGN.md"
        design_path.write_text(design.to_markdown(), encoding="utf-8")

        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer.from_design(design_path)

        plan_md = TaskDecomposer.generate_plan_md(tasks, user_task="Caching Layer")

        assert "# PLAN" in plan_md
        assert "Caching Layer" in plan_md
        # Should reference Redis or cache somewhere
        all_text = " ".join(t.goal.lower() + " " + t.title.lower() for t in tasks)
        assert "redis" in all_text or "cache" in all_text

    def test_empty_design_still_produces_plan(self, tmp_path):
        """Even a minimal design produces at least one task."""
        design_path = tmp_path / "DESIGN.md"
        design_path.write_text(
            "# Design: Quick Fix\n\n## Problem Statement\nFix it.\n",
            encoding="utf-8",
        )

        decomposer = TaskDecomposer(api_key=None)
        tasks = decomposer.from_design(design_path)
        assert len(tasks) >= 1

        plan_md = TaskDecomposer.generate_plan_md(tasks)
        assert "# PLAN" in plan_md


class TestDesignGeneratorIntegration:
    """Test DesignGenerator with project analysis."""

    def test_design_with_real_project(self, tmp_path):
        """Generate design using actual project context."""
        (tmp_path / "README.md").write_text("# My API\n\nA FastAPI REST API.\n\n## Tech\n- python\n- fastapi\n")
        (tmp_path / "requirements.txt").write_text("fastapi>=0.100\nuvicorn>=0.23\n")
        (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")

        from generator.parsers.enhanced_parser import EnhancedProjectParser

        parser = EnhancedProjectParser(tmp_path)
        context = parser.extract_full_context()

        gen = DesignGenerator(api_key=None)
        d = gen.generate_design("Add authentication", project_context=context)

        # Should produce a valid design even without AI
        assert "Authentication" in d.title
        assert "authentication" in d.problem_statement.lower()

    def test_full_cli_workflow(self, tmp_path):
        """End-to-end CLI: design -> plan from design."""
        (tmp_path / "README.md").write_text("# Project\n\nDescription.")

        runner = CliRunner()

        # Design
        r1 = runner.invoke(
            cli,
            [
                "design",
                "Add user notifications",
                "--project-path",
                str(tmp_path),
            ],
        )
        assert r1.exit_code == 0

        # Plan from design
        r2 = runner.invoke(
            cli,
            [
                "plan",
                "--from-design",
                str(tmp_path / "DESIGN.md"),
                "--project-path",
                str(tmp_path),
            ],
        )
        assert r2.exit_code == 0

        # Both files should exist
        assert (tmp_path / "DESIGN.md").exists()
        assert (tmp_path / "PLAN.md").exists()

        # Plan should reference the design title
        plan_content = (tmp_path / "PLAN.md").read_text(encoding="utf-8")
        assert "# PLAN" in plan_content
