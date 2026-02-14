"""Tests for enhanced skill matcher (Phase 2)."""

import pytest

from generator.skills.enhanced_skill_matcher import EnhancedSkillMatcher


class TestEnhancedSkillMatcher:
    """Test trigger-based skill matching."""

    @pytest.fixture
    def matcher(self):
        """Create a matcher with the default skill index."""
        return EnhancedSkillMatcher()

    @pytest.fixture
    def python_cli_context(self):
        """Context for a Python CLI project."""
        return {
            "dependencies": {
                "python": [
                    {"name": "click", "version": "8.0.0"},
                    {"name": "pydantic", "version": "2.0.0"},
                    {"name": "pytest", "version": "7.0.0"},
                ],
                "node": [],
                "python_dev": [],
                "node_dev": [],
            },
            "structure": {
                "type": "python-cli",
                "patterns": ["python-cli", "pytest-tests"],
                "entry_points": ["main.py", "cli.py"],
            },
            "test_patterns": {
                "framework": "pytest",
                "test_files": 10,
            },
            "metadata": {
                "tech_stack": ["click", "pydantic", "pytest", "python"],
                "project_type": "python-cli",
                "has_docker": False,
            },
        }

    @pytest.fixture
    def fastapi_context(self):
        """Context for a FastAPI project."""
        return {
            "dependencies": {
                "python": [
                    {"name": "fastapi", "version": "0.100.0"},
                    {"name": "pydantic", "version": "2.0.0"},
                    {"name": "uvicorn", "version": "0.23.0"},
                    {"name": "sqlalchemy", "version": "2.0.0"},
                    {"name": "pytest", "version": "7.0.0"},
                ],
                "node": [],
                "python_dev": [],
                "node_dev": [],
            },
            "structure": {
                "type": "fastapi-api",
                "patterns": ["fastapi-api"],
                "entry_points": ["app.py"],
            },
            "test_patterns": {
                "framework": "pytest",
                "test_files": 5,
            },
            "metadata": {
                "tech_stack": ["fastapi", "pydantic", "sqlalchemy", "pytest"],
                "project_type": "fastapi-api",
                "has_docker": True,
            },
        }

    @pytest.fixture
    def react_context(self):
        """Context for a React project (no Python)."""
        return {
            "dependencies": {
                "python": [],
                "node": [
                    {"name": "react", "version": "18.2.0"},
                    {"name": "react-dom", "version": "18.2.0"},
                    {"name": "next", "version": "13.4.0"},
                ],
                "python_dev": [],
                "node_dev": [
                    {"name": "jest", "version": "29.0.0"},
                    {"name": "typescript", "version": "5.0.0"},
                ],
            },
            "structure": {
                "type": "react-app",
                "patterns": ["react-app"],
                "entry_points": [],
            },
            "test_patterns": {
                "framework": "jest",
                "test_files": 3,
            },
            "metadata": {
                "tech_stack": ["react", "nextjs", "jest", "typescript"],
                "project_type": "react-app",
                "has_docker": False,
            },
        }

    def test_python_cli_gets_correct_skills(self, matcher, python_cli_context):
        """Python CLI project gets CLI and pytest skills."""
        tech = python_cli_context["metadata"]["tech_stack"]
        selected = matcher.match_skills(tech, python_cli_context)

        # Should have builtin code-review
        assert "builtin/code-review" in selected

        # Should have pytest skills
        assert any("pytest" in s for s in selected)

        # Should have python-cli skills
        assert any("python-cli" in s for s in selected)

        # Should NOT have react skills
        assert not any("react" in s for s in selected)

    def test_fastapi_gets_api_skills(self, matcher, fastapi_context):
        """FastAPI project gets API and database skills."""
        tech = fastapi_context["metadata"]["tech_stack"]
        selected = matcher.match_skills(tech, fastapi_context)

        # Should have fastapi skills
        assert any("fastapi" in s for s in selected)

        # Should have sqlalchemy skills
        assert any("sqlalchemy" in s for s in selected)

        # Should NOT have react skills
        assert not any("react" in s for s in selected)

    def test_react_project_no_python_skills(self, matcher, react_context):
        """React project should NOT get Python skills."""
        tech = react_context["metadata"]["tech_stack"]
        selected = matcher.match_skills(tech, react_context)

        # Should have react skills
        assert any("react" in s for s in selected)

        # Should have jest skills
        assert any("jest" in s for s in selected)

        # Should NOT have python-cli or fastapi skills
        assert not any("python-cli" in s for s in selected)
        assert not any("fastapi" in s for s in selected)
        assert not any("pytest" in s for s in selected)

    def test_docker_detected_from_context(self, matcher, fastapi_context):
        """Docker skills added when docker is in tech stack."""
        fastapi_context["metadata"]["tech_stack"].append("docker")
        tech = fastapi_context["metadata"]["tech_stack"]
        selected = matcher.match_skills(tech, fastapi_context)

        assert any("docker" in s for s in selected)

    def test_always_includes_code_review(self, matcher, python_cli_context):
        """Code review should always be included."""
        selected = matcher.match_skills([], python_cli_context)
        assert "builtin/code-review" in selected

    def test_empty_tech_stack(self, matcher):
        """Handles empty tech stack gracefully."""
        selected = matcher.match_skills([], {})
        assert "builtin/code-review" in selected
        assert len(selected) >= 1

    def test_skill_index_loads(self, matcher):
        """Skill index loads correctly."""
        assert matcher.index.get("version") == "1.0"
        assert "skills" in matcher.index
        assert "fastapi" in matcher.index["skills"]
        assert "react" in matcher.index["skills"]

    def test_normalize_tech_key(self, matcher):
        """Tech names normalize to index keys."""
        assert matcher._normalize_tech_key("pytorch") == "ml-pipeline"
        assert matcher._normalize_tech_key("click") == "python-cli"
        assert matcher._normalize_tech_key("express") == "node"
        assert matcher._normalize_tech_key("react") == "react"
