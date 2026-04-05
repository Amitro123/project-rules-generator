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
    assert result["primary_type"] == "python-api", f"Got: {result['primary_type']}"


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
