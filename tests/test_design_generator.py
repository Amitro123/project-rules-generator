"""Tests for the design generator (Stage 1 of two-stage planning)."""

from unittest.mock import patch

from click.testing import CliRunner

from cli.cli import cli
from generator.design_generator import ArchitectureDecision, Design, DesignGenerator


class TestDesignModel:
    """Test the Design Pydantic model."""

    def test_basic_creation(self):
        d = Design(title="Auth System", problem_statement="Need secure access")
        assert d.title == "Auth System"
        assert d.architecture_decisions == []
        assert d.success_criteria == []

    def test_full_creation(self):
        d = Design(
            title="Auth System",
            problem_statement="Users need secure access to API endpoints.",
            architecture_decisions=[
                ArchitectureDecision(
                    title="Auth Method",
                    choice="JWT tokens",
                    alternatives=["sessions"],
                    pros=["Stateless", "Scales better"],
                    cons=["Token revocation complexity"],
                ),
            ],
            api_contracts=[
                "POST /auth/login -> {token, expires_at}",
                "GET /api/* -> requires Authorization header",
            ],
            data_models=["User: id, email, password_hash, created_at"],
            success_criteria=[
                "All endpoints require auth except /auth/*",
                "Tokens expire after 24h",
            ],
        )
        assert len(d.architecture_decisions) == 1
        assert d.architecture_decisions[0].choice == "JWT tokens"
        assert len(d.api_contracts) == 2
        assert len(d.success_criteria) == 2


class TestDesignToMarkdown:
    """Test Design.to_markdown() rendering."""

    def test_renders_title(self):
        d = Design(title="Rate Limiter", problem_statement="Too many requests")
        md = d.to_markdown()
        assert "# Design: Rate Limiter" in md

    def test_renders_problem_statement(self):
        d = Design(title="X", problem_statement="System overloaded")
        md = d.to_markdown()
        assert "## Problem Statement" in md
        assert "System overloaded" in md

    def test_renders_architecture_decisions(self):
        d = Design(
            title="X",
            problem_statement="P",
            architecture_decisions=[
                ArchitectureDecision(
                    title="Approach",
                    choice="Redis",
                    alternatives=["Memcached"],
                    pros=["Fast"],
                    cons=["Extra infra"],
                ),
            ],
        )
        md = d.to_markdown()
        assert "## Architecture Decisions" in md
        assert "**Approach**: Redis (vs Memcached)" in md
        assert "Pro: Fast" in md
        assert "Con: Extra infra" in md

    def test_renders_api_contracts(self):
        d = Design(title="X", problem_statement="P", api_contracts=["GET /health -> 200"])
        md = d.to_markdown()
        assert "## API Contracts" in md
        assert "GET /health -> 200" in md

    def test_renders_success_criteria(self):
        d = Design(title="X", problem_statement="P", success_criteria=["All tests pass"])
        md = d.to_markdown()
        assert "## Success Criteria" in md
        assert "All tests pass" in md

    def test_empty_sections_omitted(self):
        d = Design(title="X", problem_statement="P")
        md = d.to_markdown()
        assert "## Architecture Decisions" not in md
        assert "## API Contracts" not in md


class TestDesignFromMarkdown:
    """Test Design.from_markdown() parsing."""

    def test_roundtrip(self):
        original = Design(
            title="Auth System",
            problem_statement="Need secure access.",
            architecture_decisions=[
                ArchitectureDecision(
                    title="Auth Method",
                    choice="JWT tokens",
                    alternatives=["sessions"],
                    pros=["Stateless"],
                    cons=["Revocation complexity"],
                ),
            ],
            api_contracts=["POST /auth/login -> {token}"],
            data_models=["User: id, email, password_hash"],
            success_criteria=["All endpoints require auth"],
        )
        md = original.to_markdown()
        parsed = Design.from_markdown(md)

        assert parsed.title == "Auth System"
        assert "secure access" in parsed.problem_statement
        assert len(parsed.architecture_decisions) == 1
        assert parsed.architecture_decisions[0].choice == "JWT tokens"
        assert len(parsed.api_contracts) == 1
        assert len(parsed.data_models) == 1
        assert len(parsed.success_criteria) == 1

    def test_parse_minimal(self):
        md = "# Design: Quick Fix\n\n## Problem Statement\nBroken thing.\n"
        d = Design.from_markdown(md)
        assert d.title == "Quick Fix"
        assert "Broken" in d.problem_statement

    def test_parse_no_title_fallback(self):
        md = "## Problem Statement\nSomething.\n"
        d = Design.from_markdown(md)
        assert d.title == "Untitled Design"


class TestDesignGenerator:
    """Test DesignGenerator without AI (no API key)."""

    @patch("generator.design_generator.DesignGenerator._call_llm", return_value="")
    def test_generate_fallback(self, mock_llm):
        gen = DesignGenerator(api_key=None)
        d = gen.generate_design("Add rate limiting")
        assert d.title == "Add rate limiting"
        assert "Add rate limiting" in d.problem_statement
        assert len(d.success_criteria) >= 1

    @patch("generator.design_generator.DesignGenerator._call_llm", return_value="")
    def test_generate_with_context(self, mock_llm):
        ctx = {
            "metadata": {
                "project_type": "fastapi-api",
                "tech_stack": ["python", "fastapi"],
                "has_tests": True,
            },
            "structure": {"entry_points": ["app/main.py"]},
        }
        gen = DesignGenerator(api_key=None)
        d = gen.generate_design("Add caching", project_context=ctx)
        assert d.title == "Add caching"


from unittest.mock import patch


class TestDesignCLI:
    """Test the design CLI command."""

    def test_design_command_in_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["design", "--help"])
        assert result.exit_code == 0
        assert "DESCRIPTION" in result.output
        assert "--output" in result.output

    def test_design_in_group_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "design" in result.output

    def test_design_requires_api_key(self, tmp_path):
        """prg design must exit 1 with a clear error when no API key is set."""
        (tmp_path / "README.md").write_text("# Test Project\n\nA project.")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "design",
                "Add authentication to API",
                "--project-path",
                str(tmp_path),
                "--output",
                "DESIGN.md",
            ],
            env={"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "ANTHROPIC_API_KEY": "", "GROQ_API_KEY": "", "OPENAI_API_KEY": ""},
        )

        assert result.exit_code == 1
        assert "API key" in result.output

    @patch("cli.cmd_design._has_api_key", return_value=True)
    @patch("generator.design_generator.DesignGenerator._call_llm", return_value="")
    def test_design_generates_file(self, mock_llm, mock_key, tmp_path):
        (tmp_path / "README.md").write_text("# Test Project\n\nA project.")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "design",
                "Add authentication to API",
                "--project-path",
                str(tmp_path),
                "--output",
                "DESIGN.md",
                "--verbose",
            ],
        )

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}\n{result.exception}"
        design_path = tmp_path / "DESIGN.md"
        assert design_path.exists()
        content = design_path.read_text(encoding="utf-8")
        assert "# Design:" in content

    @patch("cli.cmd_design._has_api_key", return_value=True)
    @patch("generator.design_generator.DesignGenerator._call_llm", return_value="")
    def test_design_custom_output(self, mock_llm, mock_key, tmp_path):
        (tmp_path / "README.md").write_text("# Test\n\nDesc.")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "design",
                "Add caching",
                "--project-path",
                str(tmp_path),
                "--output",
                "docs/DESIGN.md",
            ],
        )

        assert result.exit_code == 0
        assert (tmp_path / "docs" / "DESIGN.md").exists()
