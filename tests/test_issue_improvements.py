"""Tests for fixes from the April 2026 improvement plan."""

import os
from pathlib import Path
from unittest.mock import patch


def test_gaps_no_api_key_exits_cleanly(tmp_path):
    """prg gaps without API key should print error and exit 1, not traceback."""
    from click.testing import CliRunner

    from cli.cli import cli

    runner = CliRunner()
    # Mock _has_api_key to return False regardless of env to isolate the gate logic
    with patch("cli.gaps_cmd._has_api_key", return_value=False):
        result = runner.invoke(cli, ["gaps", str(tmp_path)])
    assert result.exit_code == 1
    assert "API key" in result.output
    assert "ValueError" not in result.output
    assert "Traceback" not in result.output


def test_spec_generate_no_api_key_exits_cleanly(tmp_path):
    """prg spec --generate without API key should print error and exit 1."""
    from click.testing import CliRunner

    from cli.cli import cli

    runner = CliRunner()
    with patch("cli.gaps_cmd._has_api_key", return_value=False):
        result = runner.invoke(cli, ["spec", str(tmp_path), "--generate"])
    assert result.exit_code == 1
    assert "API key" in result.output
    assert "ValueError" not in result.output


def test_readme_conventions_appear_in_rules(tmp_path):
    """Explicit conventions in README should be extracted as rules."""
    from generator.analyzers.readme_parser import extract_conventions

    readme_text = """# My Project
A FastAPI app.
## Conventions
- Service layer owns business logic
- Use structlog for all logging
- Never catch bare Exception
"""
    rules = extract_conventions(readme_text)
    assert any("service layer" in r.lower() for r in rules), f"Expected service layer rule, got: {rules}"
    assert any("structlog" in r.lower() for r in rules), f"Expected structlog rule, got: {rules}"
    assert len(rules) <= 20


def test_readme_conventions_deduplication(tmp_path):
    """Duplicate conventions across sections should appear only once."""
    from generator.analyzers.readme_parser import extract_conventions

    readme_text = """# Proj
## Conventions
- Use structlog for logging
## Guidelines
- Use structlog for logging
"""
    rules = extract_conventions(readme_text)
    assert rules.count("Use structlog for logging") <= 1


def test_readme_no_convention_section_returns_empty():
    """README without conventions section returns empty list."""
    from generator.analyzers.readme_parser import extract_conventions

    readme_text = "# My Project\nA cool tool.\n## Installation\npip install foo\n"
    rules = extract_conventions(readme_text)
    assert rules == []


def test_test_framework_fallback_from_deps():
    """_build_test_section falls back to pytest when it's in python_deps but framework is empty."""
    from generator.rules_sections import _build_test_section

    result = _build_test_section("", 0, {}, python_deps=["pytest", "pytest-asyncio"])
    assert "pytest" in result.lower()
    assert "No test framework" not in result


def test_test_framework_no_false_negative_when_no_deps():
    """_build_test_section shows 'No test framework' when truly absent."""
    from generator.rules_sections import _build_test_section

    result = _build_test_section("", 0, {})
    assert "No test framework" in result


def test_project_type_detector_python_api(tmp_path):
    """FastAPI project should be classified as python-api, not python-cli."""
    from generator.analyzers.project_type_detector import detect_project_type

    result = detect_project_type(
        {
            "name": "my-api",
            "tech_stack": ["fastapi", "pydantic", "uvicorn"],
            "raw_readme": "A REST API server with FastAPI. Endpoints for user management.",
        },
        str(tmp_path),
    )
    # detect_project_type returns snake_case internal score keys; the
    # hyphenated form (`python-api`) is applied by EnhancedProjectParser
    # via TYPE_LABEL_MAP when reconciling with StructureAnalyzer.
    assert result["primary_type"] == "python_api", f"Got: {result['primary_type']}"


def test_project_type_detector_cli_still_works(tmp_path):
    """A plain CLI project (click only) should remain cli_tool."""
    from generator.analyzers.project_type_detector import detect_project_type

    result = detect_project_type(
        {
            "name": "my-cli",
            "tech_stack": ["click"],
            "raw_readme": "A command-line tool. Usage: cli run.",
        },
        str(tmp_path),
    )
    assert result["primary_type"] == "cli_tool"


def test_skill_trigger_blocklist():
    """Generic single-word triggers should be filtered out."""
    from pathlib import Path

    from generator.skill_metadata_builder import SkillMetadataBuilder

    builder = SkillMetadataBuilder(Path("."))
    triggers = builder._generate_triggers("fix-skill", "", [])
    blocklisted = {"skill", "fix"}
    for t in triggers:
        words = t.split()
        if len(words) == 1:
            assert words[0] not in blocklisted, f"Generic trigger '{t}' should have been filtered"


def test_skill_minimum_three_triggers():
    """Skill metadata builder should always produce at least 3 triggers."""
    from pathlib import Path

    from generator.skill_metadata_builder import SkillMetadataBuilder

    builder = SkillMetadataBuilder(Path("."))
    triggers = builder._generate_triggers("x", "", [])
    assert len(triggers) >= 1  # single char name can't always hit 3

    triggers = builder._generate_triggers("fastapi-auth", "", [])
    assert len(triggers) >= 3, f"Expected ≥3 triggers, got: {triggers}"


def test_project_type_skill_exclusions_defined():
    """PROJECT_TYPE_SKILL_EXCLUSIONS should cover all main project types."""
    from generator.skill_generator import SkillGenerator

    exclusions = SkillGenerator.PROJECT_TYPE_SKILL_EXCLUSIONS
    # Python projects should exclude frontend skills
    assert "react-components" in exclusions["python-api"]
    assert "jest-testing" in exclusions["python-cli"]
    # Frontend projects should exclude Python backend skills
    assert "fastapi-endpoints" in exclusions["react-app"]
    assert "pytest-testing" in exclusions["frontend-app"]


def test_generate_perfect_index_filters_by_project_type(tmp_path):
    """generate_perfect_index should omit skills excluded for the given project type."""
    from unittest.mock import MagicMock, patch

    from generator.skills_manager import SkillsManager

    mgr = SkillsManager(project_path=tmp_path)

    # Fake skill list that includes a frontend skill in a Python project
    fake_skills = {
        "pytest-testing": {"type": "learned", "content": "# Pytest"},
        "react-components": {"type": "learned", "content": "# React"},
        "systematic-debugging": {"type": "builtin", "content": "# Debug"},
    }

    with patch.object(mgr.discovery, "list_skills", return_value=fake_skills):
        with patch.object(mgr.discovery, "project_skills_root", tmp_path / ".clinerules" / "skills"):
            mgr.discovery.project_skills_root.mkdir(parents=True, exist_ok=True)
            # Python CLI project → react-components should be excluded
            index_path = mgr.generate_perfect_index(project_type="python-cli")
            content = index_path.read_text(encoding="utf-8")

    assert "pytest-testing" in content
    assert "systematic-debugging" in content
    assert "react-components" not in content, "Frontend skill should be filtered for python-cli"


def test_generate_perfect_index_no_filter_when_no_type(tmp_path):
    """Without project_type, generate_perfect_index includes all skills."""
    from unittest.mock import patch

    from generator.skills_manager import SkillsManager

    mgr = SkillsManager(project_path=tmp_path)

    fake_skills = {
        "react-components": {"type": "learned", "content": "# React"},
        "pytest-testing": {"type": "learned", "content": "# Pytest"},
    }

    with patch.object(mgr.discovery, "list_skills", return_value=fake_skills):
        with patch.object(mgr.discovery, "project_skills_root", tmp_path / ".clinerules" / "skills"):
            mgr.discovery.project_skills_root.mkdir(parents=True, exist_ok=True)
            index_path = mgr.generate_perfect_index()  # no project_type
            content = index_path.read_text(encoding="utf-8")

    assert "react-components" in content
    assert "pytest-testing" in content


def test_test_coverage_skill_mentions_all_frameworks():
    """test-coverage.md should mention pytest, jest, and vitest."""
    from pathlib import Path

    skill_path = Path(__file__).parent.parent / "generator" / "skills" / "builtin" / "test-coverage.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "pytest" in content
    assert "jest" in content.lower()
    assert "vitest" in content.lower()


def test_extract_readme_description_skips_headings():
    """_extract_readme_description returns first prose line, not the H1."""
    from generator.llm_skill_generator import _extract_readme_description

    readme = "# My Project\nA Python CLI tool that generates rules.\n## Usage\npip install x"
    assert _extract_readme_description(readme) == "A Python CLI tool that generates rules."


def test_extract_readme_description_empty():
    from generator.llm_skill_generator import _extract_readme_description

    assert _extract_readme_description("") == ""
    assert _extract_readme_description("# Only a heading") == ""


def test_parse_python_deps_from_requirements():
    from generator.llm_skill_generator import _parse_python_deps_from_files

    key_files = {"requirements.txt": "click>=8.0\npytest>=7\nrequests\n# comment\n"}
    deps = _parse_python_deps_from_files(key_files)
    assert "click" in deps
    assert "pytest" in deps
    assert "requests" in deps


def test_detect_test_framework_from_files():
    from generator.llm_skill_generator import _detect_test_framework_from_files

    assert _detect_test_framework_from_files({"pyproject.toml": "[tool.pytest.ini_options]"}) == "pytest"
    assert _detect_test_framework_from_files({"package.json": '{"devDependencies": {"jest": "^29"}}'}) == "jest"
    assert _detect_test_framework_from_files({}) == ""


def test_skill_doc_loader_finds_relevant_files(tmp_path):
    """_find_relevant_files should score .py files by token overlap with skill name."""
    from generator.skill_doc_loader import SkillDocLoader

    # High-relevance: imports the token AND mentions it in body
    (tmp_path / "git_ops.py").write_text("import git\nrepo = git.Repo('.')\n", encoding="utf-8")
    # No relevance: generic utils
    (tmp_path / "utils.py").write_text("import os\n", encoding="utf-8")

    loader = SkillDocLoader(tmp_path)
    key_files: dict = {}
    # "git-workflow" → tokens ["git", "workflow"]; "git" matches the import statement
    loader._find_relevant_files("git-workflow", key_files, max_files=3)

    assert "git_ops.py" in key_files
    assert "utils.py" not in key_files


def test_skill_doc_loader_relevant_files_body_signal(tmp_path):
    """_find_relevant_files picks up files that mention the skill tokens in body (no import)."""
    from generator.skill_doc_loader import SkillDocLoader

    (tmp_path / "fastapi_routes.py").write_text(
        "from fastapi import APIRouter\nrouter = APIRouter()\n", encoding="utf-8"
    )
    (tmp_path / "unrelated.py").write_text("x = 1\n", encoding="utf-8")

    loader = SkillDocLoader(tmp_path)
    key_files: dict = {}
    loader._find_relevant_files("fastapi-endpoints", key_files, max_files=3)

    assert "fastapi_routes.py" in key_files
    assert "unrelated.py" not in key_files


def test_skill_frontmatter_when_phrases():
    """render_frontmatter should include 'When the user mentions' phrases."""
    from pathlib import Path
    from unittest.mock import MagicMock

    from generator.skill_metadata_builder import SkillMetadataBuilder

    builder = SkillMetadataBuilder(Path("."))
    metadata = MagicMock()
    metadata.description = "Handles FastAPI auth patterns."
    metadata.auto_triggers = ["fastapi auth", "oauth2", "jwt token"]
    metadata.name = "fastapi-auth"
    metadata.negative_triggers = []
    metadata.tags = ["fastapi", "auth"]
    metadata.category = "Security"

    frontmatter = builder.render_frontmatter(metadata)
    assert "When the user mentions" in frontmatter
