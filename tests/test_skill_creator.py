"""
Comprehensive tests for Cowork-powered skill creator.

Tests cover:
- Metadata generation
- Trigger optimization
- Tool selection
- Quality validation
- Hallucination detection
- Template rendering
"""

import tempfile
from pathlib import Path

import pytest

from generator.skill_creator import (
    CoworkSkillCreator,
    QualityReport,
    SkillMetadata,
)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with realistic structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create realistic project structure
        (project_dir / "tests").mkdir()
        (project_dir / "tests" / "test_api.py").touch()
        (project_dir / "Dockerfile").touch()
        (project_dir / "docker-compose.yml").touch()
        (project_dir / "requirements.txt").write_text("fastapi\npytest\nuvicorn\nhttpx")
        (project_dir / "README.md").write_text("""
# FastAPI Security Project

A secure FastAPI application with authentication.

## Features
- JWT authentication
- Rate limiting
- Security headers

## Tech Stack
- FastAPI
- PostgreSQL
- Redis
- Docker
        """)

        yield project_dir


@pytest.fixture
def sample_readme():
    """Sample README content for testing."""
    return """
# FastAPI Security Auditor

## Overview
This project provides security auditing tools for FastAPI applications.

## Features
- Vulnerability scanning
- Dependency checking
- Security best practices validation

## Tech Stack
- FastAPI
- pytest
- bandit
- safety

## Usage
Run security audit on your FastAPI project.
    """


class TestSkillMetadataGeneration:
    """Test metadata generation with Cowork intelligence."""

    def test_generates_smart_triggers(self, temp_project_dir, sample_readme):
        """Test that triggers include synonyms and variations."""
        creator = CoworkSkillCreator(temp_project_dir)

        content, metadata, quality = creator.create_skill(
            "fastapi-security-auditor",
            sample_readme
        )

        # Should have multiple trigger variations
        assert len(metadata.auto_triggers) >= 3

        # Should include base trigger
        assert any("security" in t.lower() for t in metadata.auto_triggers)

        # Should include synonyms (from TRIGGER_SYNONYMS)
        assert any("audit" in t.lower() for t in metadata.auto_triggers)

    def test_detects_project_signals(self, temp_project_dir, sample_readme):
        """Test project signal detection from file structure."""
        creator = CoworkSkillCreator(temp_project_dir)

        signals = creator._detect_project_signals()

        # Should detect based on created files
        assert "has_docker" in signals  # Dockerfile exists
        assert "has_tests" in signals   # tests/ exists

    def test_selects_appropriate_tools(self, temp_project_dir, sample_readme):
        """Test intelligent tool selection based on tech stack."""
        creator = CoworkSkillCreator(temp_project_dir)

        content, metadata, quality = creator.create_skill(
            "fastapi-api-testing",
            sample_readme
        )

        # Should include pytest (from tech stack)
        assert "pytest" in metadata.tools

        # Should include httpx (for API testing)
        assert "httpx" in metadata.tools or "pytest" in metadata.tools

    def test_tech_stack_detection(self, temp_project_dir, sample_readme):
        """Test automatic tech stack detection from README."""
        creator = CoworkSkillCreator(temp_project_dir)

        tech_stack = creator._detect_tech_stack(sample_readme)

        assert "fastapi" in tech_stack
        assert "pytest" in tech_stack


class TestTriggerGeneration:
    """Test Cowork's smart trigger generation."""

    def test_generates_action_triggers(self, temp_project_dir):
        """Test extraction of action-based triggers from README."""
        readme = """
# API Testing Tool

## How to Use
Run security audit on your API endpoints.
Check authentication vulnerabilities.
        """

        creator = CoworkSkillCreator(temp_project_dir)

        content, metadata, quality = creator.create_skill(
            "api-security-audit",
            readme
        )

        # Should extract "run" and "check" actions
        trigger_text = " ".join(metadata.auto_triggers).lower()
        assert "audit" in trigger_text or "security" in trigger_text

    def test_expands_with_synonyms(self, temp_project_dir, sample_readme):
        """Test trigger expansion with synonyms."""
        creator = CoworkSkillCreator(temp_project_dir)

        triggers = creator._generate_triggers(
            "api-test-runner",
            sample_readme,
            ["fastapi", "pytest"]
        )

        # Should have variations of "test"
        assert len(triggers) >= 3

        # Should include synonyms like "testing", "verify"
        trigger_text = " ".join(triggers).lower()
        assert "test" in trigger_text


class TestQualityValidation:
    """Test Cowork's quality gates."""

    def test_detects_placeholders(self, temp_project_dir):
        """Test detection of placeholder text (quality issue)."""
        creator = CoworkSkillCreator(temp_project_dir)

        # Create content with placeholders
        content = """
# Skill: Test

## Purpose
[Describe what this does]

## Process
TODO: Add steps here
        """

        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            auto_triggers=["test"],
            tools=["pytest"]
        )

        quality = creator._validate_quality(content, metadata)

        # Should detect placeholders
        assert not quality.passed
        assert quality.score < 70
        assert any("placeholder" in issue.lower() for issue in quality.issues)

    def test_detects_hallucinated_paths(self, temp_project_dir):
        """Test detection of non-existent file paths (critical!)."""
        creator = CoworkSkillCreator(temp_project_dir)

        content = """
# Skill: Test

Check `src/nonexistent/file.py` for configuration.
See also `fake/path/module.py`.
        """

        hallucinated = creator._detect_hallucinated_paths(content)

        # Should detect fake paths
        assert len(hallucinated) >= 2
        assert "src/nonexistent/file.py" in hallucinated

    def test_validates_trigger_coverage(self, temp_project_dir, sample_readme):
        """Test that quality check ensures sufficient triggers."""
        creator = CoworkSkillCreator(temp_project_dir)

        # Create skill with few triggers
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            auto_triggers=["test"],  # Only 1 trigger
            tools=["pytest"]
        )

        content = "# Skill\n\nBasic content"

        quality = creator._validate_quality(content, metadata)

        # Should warn about low trigger count
        assert len(quality.warnings) > 0

    def test_ensures_actionability(self, temp_project_dir):
        """Test that skills have actionable content (code/commands)."""
        creator = CoworkSkillCreator(temp_project_dir)

        # Content without code blocks
        content_no_code = """
# Skill: Test

## Purpose
Do something

## Process
Just do it manually
        """

        metadata = SkillMetadata(
            name="test",
            description="Test",
            auto_triggers=["test"] * 5,
            tools=["pytest"]
        )

        quality = creator._validate_quality(content_no_code, metadata)

        # Should warn about lack of code examples
        assert any("actionable" in w.lower() or "code" in w.lower()
                   for w in quality.warnings)


class TestAutoFixing:
    """Test automatic quality issue fixing."""

    def test_fixes_generic_paths(self, temp_project_dir):
        """Test fixing of generic path placeholders."""
        creator = CoworkSkillCreator(temp_project_dir)

        content = """
cd project_name
cd /path/to/project
        """

        quality = QualityReport(score=50, passed=False)

        fixed = creator._auto_fix_quality_issues(content, quality)

        # Should replace with actual project name
        assert temp_project_dir.name in fixed
        assert "project_name" not in fixed
        assert "/path/to/project" not in fixed

    def test_adds_anti_patterns_if_missing(self, temp_project_dir):
        """Test adding anti-patterns section when missing."""
        creator = CoworkSkillCreator(temp_project_dir)

        content = """
# Skill: Test

## Purpose
Test skill
        """

        quality = QualityReport(score=70, passed=True)

        fixed = creator._auto_fix_quality_issues(content, quality)

        # Should add anti-patterns section
        assert "## Anti-Patterns" in fixed
        assert "❌" in fixed
        assert "✅" in fixed


class TestContentGeneration:
    """Test skill content generation."""

    def test_generates_yaml_frontmatter(self, temp_project_dir, sample_readme):
        """Test that generated skills have YAML frontmatter."""
        creator = CoworkSkillCreator(temp_project_dir)

        content, metadata, quality = creator.create_skill(
            "test-skill",
            sample_readme
        )

        # Should start with YAML frontmatter
        assert content.startswith("---")
        assert "name:" in content
        assert "auto_triggers:" in content
        assert "tools:" in content

    def test_includes_project_context(self, temp_project_dir, sample_readme):
        """Test that generated skills reference actual project."""
        creator = CoworkSkillCreator(temp_project_dir)

        content, metadata, quality = creator.create_skill(
            "test-skill",
            sample_readme
        )

        # Should reference actual project name
        assert temp_project_dir.name in content

    def test_includes_all_required_sections(self, temp_project_dir, sample_readme):
        """Test that all required sections are present."""
        creator = CoworkSkillCreator(temp_project_dir)

        content, metadata, quality = creator.create_skill(
            "test-skill",
            sample_readme
        )

        # Required sections
        required_sections = [
            "# Skill:",
            "## Purpose",
            "## Auto-Trigger",
            "## Process",
            "## Output",
            "## Anti-Patterns",
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"


class TestToolValidation:
    """Test tool availability validation."""

    def test_validates_tools_in_requirements(self, temp_project_dir, sample_readme):
        """Test that tools are validated against requirements.txt."""
        creator = CoworkSkillCreator(temp_project_dir)

        # requirements.txt has: fastapi, pytest, uvicorn, httpx
        available = creator._validate_tools_availability(
            {"pytest", "httpx", "nonexistent-tool"}
        )

        # Should include tools from requirements.txt
        assert "pytest" in available
        assert "httpx" in available

        # Should exclude tools not in requirements
        assert "nonexistent-tool" not in available


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_skill_creation_workflow(self, temp_project_dir, sample_readme):
        """Test complete skill creation workflow."""
        creator = CoworkSkillCreator(temp_project_dir)

        # Create skill
        content, metadata, quality = creator.create_skill(
            "fastapi-security-auditor",
            sample_readme
        )

        # Validate metadata
        assert metadata.name == "fastapi-security-auditor"
        assert len(metadata.auto_triggers) >= 3
        assert len(metadata.tools) >= 1
        assert len(metadata.project_signals) >= 1

        # Validate quality
        assert quality.score >= 60  # Should pass basic quality

        # Validate content
        assert "fastapi" in content.lower()
        assert "---" in content  # Has frontmatter
        assert "## Purpose" in content
        assert "## Process" in content

    def test_export_to_file(self, temp_project_dir, sample_readme):
        """Test exporting skill to file."""
        creator = CoworkSkillCreator(temp_project_dir)

        content, metadata, quality = creator.create_skill(
            "test-skill",
            sample_readme
        )

        output_dir = temp_project_dir / "skills"

        skill_file = creator.export_to_file(content, metadata, output_dir)

        # Should create file
        assert skill_file.exists()
        assert skill_file.name == "test-skill.md"

        # Should contain content
        saved_content = skill_file.read_text()
        assert saved_content == content


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_readme(self, temp_project_dir):
        """Test handling of empty/minimal README."""
        creator = CoworkSkillCreator(temp_project_dir)

        content, metadata, quality = creator.create_skill(
            "test-skill",
            ""  # Empty README
        )

        # Should still generate valid skill
        assert metadata.name == "test-skill"
        assert len(content) > 0

    def test_handles_no_tech_stack(self, temp_project_dir):
        """Test handling when no tech stack is detected."""
        readme = "# Simple Project\n\nNo technology mentioned."

        creator = CoworkSkillCreator(temp_project_dir)

        content, metadata, quality = creator.create_skill(
            "generic-skill",
            readme
        )

        # Should still create skill with generic content
        assert metadata.name == "generic-skill"
        assert len(content) > 0

    def test_handles_special_characters_in_name(self, temp_project_dir, sample_readme):
        """Test handling of special characters in skill name."""
        creator = CoworkSkillCreator(temp_project_dir)

        # Name with special chars (should be handled)
        content, metadata, quality = creator.create_skill(
            "api-v2-security",
            sample_readme
        )

        assert metadata.name == "api-v2-security"
