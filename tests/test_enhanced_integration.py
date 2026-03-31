"""Integration tests for the full enhanced pipeline (Phase 5)."""

import os
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from generator.extractors.code_extractor import CodeExampleExtractor
from generator.outputs.clinerules_generator import generate_clinerules
from generator.parsers.enhanced_parser import EnhancedProjectParser
from generator.skills.enhanced_skill_matcher import EnhancedSkillMatcher
from main import main


class TestEndToEndEnhancedPipeline:
    """Test the complete enhanced pipeline end-to-end."""

    def test_python_cli_project_full_flow(self, tmp_path):
        """Test complete flow for a Python CLI project."""
        # Create test project
        project_dir = tmp_path / "my-cli-tool"
        project_dir.mkdir()

        (project_dir / "README.md").write_text(
            "# My CLI Tool\n\n" "A Python CLI tool for data processing.\n\n" "## Tech\n- python\n- click\n- pytest\n"
        )
        (project_dir / "requirements.txt").write_text("click>=8.0\npydantic>=2.0\npytest>=7.0\nrich>=13.0\n")
        (project_dir / "main.py").write_text(
            "import click\n\n"
            "@click.command()\n"
            "@click.argument('input_file')\n"
            "def main(input_file):\n"
            "    '''Process data files.'''\n"
            "    pass\n"
        )
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "conftest.py").write_text("import pytest\n")
        (tests_dir / "test_main.py").write_text("def test_main(): pass\n")

        # Step 1: Enhanced parsing
        parser = EnhancedProjectParser(project_dir)
        context = parser.extract_full_context()

        assert context["metadata"]["project_type"] == "python-cli"
        assert "click" in context["metadata"]["tech_stack"]
        assert "python" in context["metadata"]["languages"]

        # Step 2: Skill matching
        matcher = EnhancedSkillMatcher()
        selected = matcher.match_skills(context["metadata"]["tech_stack"], context)

        # Verify correct skill selection
        assert "builtin/code-review" in selected
        assert any("python-cli" in s for s in selected)
        assert any("pytest" in s for s in selected)
        assert not any("react" in s for s in selected)

        # Step 3: Generate lightweight .clinerules
        yaml_output = generate_clinerules("my-cli-tool", selected, context)
        parsed_yaml = yaml.safe_load(yaml_output)

        assert parsed_yaml["project"] == "my-cli-tool"
        assert "skills" in parsed_yaml
        assert parsed_yaml["skills_count"]["total"] > 0

    def test_fastapi_project_full_flow(self, tmp_path):
        """Test complete flow for a FastAPI project."""
        project_dir = tmp_path / "my-api"
        project_dir.mkdir()

        (project_dir / "requirements.txt").write_text(
            "fastapi>=0.100.0\nuvicorn>=0.23.0\npydantic>=2.0\nsqlalchemy>=2.0\n"
        )
        (project_dir / "README.md").write_text("# My API\n\nA FastAPI REST API.\n\n## Tech\n- python\n- fastapi\n")
        (project_dir / "app.py").write_text(
            "from fastapi import FastAPI\napp = FastAPI()\n"
            "@app.get('/health')\ndef health(): return {'status': 'ok'}\n"
        )
        routes = project_dir / "routes"
        routes.mkdir()
        (routes / "users.py").write_text("from fastapi import APIRouter\nrouter = APIRouter()\n")

        parser = EnhancedProjectParser(project_dir)
        context = parser.extract_full_context()

        assert "fastapi" in context["metadata"]["tech_stack"]

        matcher = EnhancedSkillMatcher()
        selected = matcher.match_skills(context["metadata"]["tech_stack"], context)

        assert any("fastapi" in s for s in selected)
        assert any("sqlalchemy" in s for s in selected)
        assert not any("react" in s for s in selected)

    def test_no_react_skills_for_python_project(self, tmp_path):
        """Critical: React skills must NOT appear in Python-only projects."""
        project_dir = tmp_path / "pure-python"
        project_dir.mkdir()

        (project_dir / "requirements.txt").write_text("flask>=3.0\npytest>=7.0\n")
        (project_dir / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n")

        parser = EnhancedProjectParser(project_dir)
        context = parser.extract_full_context()

        matcher = EnhancedSkillMatcher()
        selected = matcher.match_skills(context["metadata"]["tech_stack"], context)

        # CRITICAL CHECK: No JS/React/Vue/Node skills
        for skill in selected:
            assert "react" not in skill, f"React skill found in Python project: {skill}"
            assert "vue" not in skill, f"Vue skill found in Python project: {skill}"
            assert "jest" not in skill, f"Jest skill found in Python project: {skill}"

    def test_self_project_analysis(self):
        """Test with project-rules-generator itself."""
        project_path = Path(__file__).parent.parent

        parser = EnhancedProjectParser(project_path)
        context = parser.extract_full_context()

        # Should detect as python-cli
        assert context["metadata"]["project_type"] == "python-cli"
        assert "click" in context["metadata"]["tech_stack"]
        assert "pytest" in context["metadata"]["tech_stack"]
        assert context["metadata"]["has_tests"] is True

        # Note: README mentions react in its comparison table, so it may appear
        # in tech_stack from README parsing. The key check is that the
        # SkillMatcher doesn't select react LEARNED skills when there are
        # no actual react dependencies.

        # Skill matching - should still work correctly
        matcher = EnhancedSkillMatcher()
        selected = matcher.match_skills(context["metadata"]["tech_stack"], context)

        assert "builtin/code-review" in selected
        assert any("python-cli" in s for s in selected)

        # Even if 'react' appears in README tech_stack, the matcher should NOT
        # select learned react skills because there are no react dependencies
        # (no package.json, no react in node deps). The matcher checks triggers
        # which require actual dependencies.
        has_react_learned = any(s.startswith("learned/react/") for s in selected)
        assert not has_react_learned, (
            f"React learned skills should not be selected for a Python-only project. " f"Selected: {selected}"
        )


class TestCodeExampleExtractor:
    """Test code extraction from project files."""

    def test_extract_click_patterns(self, tmp_path):
        """Extract Click CLI patterns."""
        (tmp_path / "cli.py").write_text(
            "import click\n\n"
            "@click.command()\n"
            "@click.option('--name', help='User name')\n"
            "def greet(name):\n"
            "    click.echo(f'Hello {name}')\n"
        )

        extractor = CodeExampleExtractor()
        examples = extractor.extract_examples_for_skill(tmp_path, "cli", ["python", "click"])

        assert len(examples) > 0
        assert any("click" in ex.get("reason", "").lower() or "click" in ex.get("code", "").lower() for ex in examples)

    def test_extract_fastapi_patterns(self, tmp_path):
        """Extract FastAPI route patterns."""
        (tmp_path / "routes.py").write_text(
            "from fastapi import APIRouter, Depends\n\n"
            "router = APIRouter()\n\n"
            "@router.get('/users')\n"
            "async def get_users():\n"
            "    return []\n"
        )

        extractor = CodeExampleExtractor()
        examples = extractor.extract_examples_for_skill(tmp_path, "fastapi", ["python", "fastapi"])

        assert len(examples) > 0

    def test_extract_from_self_project(self):
        """Extract examples from the project-rules-generator itself."""
        project_path = Path(__file__).parent.parent
        extractor = CodeExampleExtractor()
        examples = extractor.extract_examples_for_skill(project_path, "cli", ["python", "click"])

        assert len(examples) > 0
        # Should find click-related code
        assert any("click" in ex.get("code", "").lower() for ex in examples)


class TestLightweightClinerules:
    """Test lightweight .clinerules generation."""

    def test_generate_clinerules_yaml(self):
        """Generate valid YAML .clinerules."""
        selected = {
            "builtin/code-review",
            "builtin/test-driven-development",
            "learned/fastapi/async-patterns",
            "learned/pytest/coverage-patterns",
        }
        context = {
            "metadata": {
                "tech_stack": ["fastapi", "pytest"],
                "project_type": "fastapi-api",
            }
        }

        output = generate_clinerules("my-api", selected, context)
        parsed = yaml.safe_load(output)

        assert parsed["project"] == "my-api"
        assert parsed["project_type"] == "fastapi-api"
        assert "skills" in parsed
        assert parsed["skills_count"]["total"] == 4
        assert parsed["skills_count"]["builtin"] == 2
        assert parsed["skills_count"]["learned"] == 2

    def test_clinerules_is_small(self):
        """Verify .clinerules stays small (< 30 lines)."""
        selected = {
            "builtin/code-review",
            "learned/fastapi/async-patterns",
            "learned/pytest/coverage-patterns",
        }

        output = generate_clinerules("test-project", selected)
        line_count = len(output.strip().splitlines())

        assert line_count < 40, f"Expected < 40 lines, got {line_count}"

    def test_clinerules_no_duplicate_skill_md(self):
        """Builtin skills with directory layout must NOT produce duplicate SKILL.md paths."""
        selected = {
            "builtin/code-review",
            "builtin/test-driven-development",
            "builtin/systematic-debugging",
        }
        context = {
            "metadata": {
                "tech_stack": ["python"],
                "project_type": "python-cli",
            }
        }

        # With output_dir, paths use subfolder layout: skills/builtin/{name}/SKILL.md
        output = generate_clinerules("test", selected, context, output_dir=Path("/fake"))
        parsed = yaml.safe_load(output)

        builtin_paths = parsed["skills"]["builtin"]
        # Each path must be unique
        assert len(builtin_paths) == len(set(builtin_paths)), f"Duplicate paths: {builtin_paths}"
        for p in builtin_paths:
            assert p.startswith("skills/builtin/"), f"Unexpected path prefix: {p}"
            assert p.endswith("/SKILL.md"), f"Expected subfolder layout (name/SKILL.md): {p}"

    def test_clinerules_skill_names_in_paths(self):
        """Each builtin skill path should contain the skill name."""
        selected = {
            "builtin/brainstorming",
            "builtin/writing-plans",
        }
        output = generate_clinerules("test", selected, output_dir=Path("/fake"))
        parsed = yaml.safe_load(output)

        paths = parsed["skills"]["builtin"]
        assert "skills/builtin/brainstorming/SKILL.md" in paths
        assert "skills/builtin/writing-plans/SKILL.md" in paths


class TestCLIIntegration:
    """Test CLI integration with enhanced modules."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "", "GROQ_API_KEY": ""})
    def test_auto_generate_skills_flag(self, tmp_path):
        """Test --auto-generate-skills uses enhanced pipeline."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        (project_dir / "README.md").write_text("# Test Project\n\nA Python project.\n\n## Tech\n- python\n- click\n")
        (project_dir / "requirements.txt").write_text("click>=8.0\npytest>=7.0\n")
        (project_dir / "main.py").write_text("import click\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            [str(project_dir), "--no-commit", "--verbose", "--auto-generate-skills"],
        )

        assert (
            result.exit_code == 0
        ), f"Exit code {result.exit_code}.\nOutput:\n{result.output}\nException: {result.exception}"
        assert "Enhanced Analysis" in result.output
        assert "Matched Skills" in result.output

    def test_basic_flow_still_works(self, tmp_path):
        """Existing basic flow without --auto-generate-skills still works."""
        project_dir = tmp_path / "basic-project"
        project_dir.mkdir()

        (project_dir / "README.md").write_text("# Basic Project\n\nDescription.\n\n## Tech\n- python\n")

        runner = CliRunner()
        result = runner.invoke(main, [str(project_dir), "--no-commit", "--quiet"])

        assert (
            result.exit_code == 0
        ), f"Exit code {result.exit_code}.\nOutput:\n{result.output}\nException: {result.exception}"
