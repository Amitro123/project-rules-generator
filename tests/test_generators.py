"""Tests for rules and skills generators."""

from generator.rules_generator import generate_rules
# NOTE: skills_generator.py was removed in v1.1 cleanup.
# Skills generation is now done via SkillsManager.create_skill() or SkillGenerator.
# The TestSkillsGenerator tests below are kept for historical reference but
# are now integration tests via SkillsManager.
from generator.skills_manager import SkillsManager


class TestRulesGenerator:
    """Test suite for rules generation."""

    def test_generate_rules_structure(self, mock_config):
        """Test that generated rules has correct structure."""
        project_data = {
            "name": "test-project",
            "description": "A test project description",
            "tech_stack": ["python", "fastapi"],
            "features": ["Feature one", "Feature two", "Feature three"],
        }

        result = generate_rules(project_data, mock_config)

        # Check YAML frontmatter
        assert result.startswith("---")
        assert "project: test-project" in result

        # Check required sections
        assert "## CONTEXT" in result
        assert "## DO" in result
        assert "## DON'T" in result or "## DON'T" in result
        assert "## PRIORITIES" in result
        assert "## WORKFLOWS" in result

    def test_generate_rules_with_tech_stack(self, mock_config):
        """Test that tech stack is included in rules."""
        project_data = {
            "name": "test-project",
            "description": "A test project",
            "tech_stack": ["python", "django", "postgresql"],
            "features": [],
        }

        result = generate_rules(project_data, mock_config)

        assert "python, django, postgresql" in result
        assert "Use python, django, postgresql" in result

    def test_generate_rules_with_features_as_priorities(self, mock_config):
        """Test that features become priorities."""
        project_data = {
            "name": "test-project",
            "description": "A test project",
            "tech_stack": ["python"],
            "features": ["Fast processing", "Easy config", "Good tests"],
        }

        result = generate_rules(project_data, mock_config)

        assert "1. Fast processing" in result
        assert "2. Easy config" in result
        assert "3. Good tests" in result

    def test_generate_rules_default_priorities(self, mock_config):
        """Test default priorities when no features."""
        project_data = {
            "name": "test-project",
            "description": "A test project",
            "tech_stack": [],
            "features": [],
        }

        result = generate_rules(project_data, mock_config)

        # Should have default priorities
        assert "## PRIORITIES" in result
        assert "1." in result
        assert "2." in result
        assert "3." in result

    def test_generate_rules_description_truncation(self, mock_config):
        """Test that long descriptions are truncated."""
        long_desc = "A" * 300
        project_data = {
            "name": "test-project",
            "description": long_desc,
            "tech_stack": [],
            "features": [],
        }

        result = generate_rules(project_data, mock_config)

        # Description should be truncated with ...
        assert "..." in result


class TestSkillsGenerator:
    """Test suite for skills generation.
    
    NOTE: skills_generator.py was removed in v1.1 cleanup.
    These tests are preserved for documentation purposes.
    New skill generation is done via SkillsManager.create_skill().
    """

    def test_generate_skills_structure(self, mock_config):
        """Legacy test - skills_generator removed in v1.1."""
        import pytest
        pytest.skip("skills_generator.py removed in v1.1 - use SkillsManager.create_skill()")

    def test_generate_skills_domain_specific(self, mock_config):
        """Legacy test - skills_generator removed in v1.1."""
        import pytest
        pytest.skip("skills_generator.py removed in v1.1 - use SkillsManager.create_skill()")

    def test_generate_skills_usage_section(self, mock_config):
        """Legacy test - skills_generator removed in v1.1."""
        import pytest
        pytest.skip("skills_generator.py removed in v1.1 - use SkillsManager.create_skill()")

    def test_generate_skills_with_primary_domain(self, mock_config):
        """Legacy test - skills_generator removed in v1.1."""
        import pytest
        pytest.skip("skills_generator.py removed in v1.1 - use SkillsManager.create_skill()")

    def test_skills_manager_list(self, tmp_path):
        """New test: SkillsManager can list skills."""
        manager = SkillsManager(project_path=tmp_path)
        skills = manager.list_skills()
        # Should return a dict with categories
        assert isinstance(skills, dict)
