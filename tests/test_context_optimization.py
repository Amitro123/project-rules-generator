"""Tests for context optimization features."""

import yaml

from generator.outputs.clinerules_generator import _build_context_config, generate_clinerules
from generator.prompts.skill_generation import _detect_relevant_files, build_skill_prompt
from generator.rules_generator import _build_context_strategy, generate_rules


def _make_enhanced_context(
    project_type="cli-tool",
    tech_stack=None,
    python_deps=None,
    node_deps=None,
    entry_points=None,
    patterns=None,
    test_framework="pytest",
    test_files=5,
    has_conftest=True,
):
    """Helper to build a realistic enhanced_context dict."""
    tech_stack = tech_stack or ["python"]
    python_deps = python_deps or []
    node_deps = node_deps or []
    entry_points = entry_points or ["main.py"]
    patterns = patterns or [project_type]

    return {
        "metadata": {
            "project_type": project_type,
            "tech_stack": tech_stack,
            "languages": ["python"],
            "has_tests": True,
        },
        "dependencies": {
            "python": [{"name": d, "version": "*"} for d in python_deps],
            "node": [{"name": d, "version": "*"} for d in node_deps],
        },
        "structure": {
            "type": project_type,
            "entry_points": entry_points,
            "patterns": patterns,
        },
        "test_patterns": {
            "framework": test_framework,
            "test_files": test_files,
            "has_conftest": has_conftest,
            "has_fixtures": False,
            "patterns": ["unit"],
        },
        "readme": {
            "description": "A test project.",
            "installation": "",
            "usage": "",
            "troubleshooting": "",
        },
    }


class TestRulesContextStrategy:
    """Test that rules.md contains CONTEXT STRATEGY section."""

    def test_context_strategy_present_in_enhanced_rules(self):
        project_data = {
            "name": "test-project",
            "description": "A test project",
            "tech_stack": ["python"],
            "features": ["Feature one"],
        }
        config = {"generation": {"max_description_length": 200}}
        ctx = _make_enhanced_context(python_deps=["click", "pytest"])

        result = generate_rules(project_data, config, enhanced_context=ctx)

        assert "## CONTEXT STRATEGY" in result

    def test_context_strategy_has_task_table(self):
        project_data = {
            "name": "test-project",
            "description": "A test project",
            "tech_stack": ["python"],
            "features": [],
        }
        config = {"generation": {"max_description_length": 200}}
        ctx = _make_enhanced_context()

        result = generate_rules(project_data, config, enhanced_context=ctx)

        assert "Bug fix" in result
        assert "New feature" in result
        assert "Refactor" in result

    def test_context_strategy_has_exclude_list(self):
        project_data = {
            "name": "test-project",
            "description": "A test project",
            "tech_stack": ["python"],
            "features": [],
        }
        config = {"generation": {"max_description_length": 200}}
        ctx = _make_enhanced_context()

        result = generate_rules(project_data, config, enhanced_context=ctx)

        assert "__pycache__" in result
        assert ".venv" in result

    def test_context_strategy_not_in_basic_rules(self):
        """Basic rules (no enhanced context) should not have CONTEXT STRATEGY."""
        project_data = {
            "name": "test-project",
            "description": "A test project",
            "tech_stack": ["python"],
            "features": [],
        }
        config = {"generation": {"max_description_length": 200}}

        result = generate_rules(project_data, config, enhanced_context=None)

        assert "## CONTEXT STRATEGY" not in result


class TestContextStrategyByProjectType:
    """Test that context strategies differ by project type."""

    def test_cli_strategy_references_main_py(self):
        structure = {"entry_points": ["main.py"], "patterns": ["cli-tool"]}
        test_info = {"framework": "pytest", "has_conftest": True}

        result = _build_context_strategy(structure, ["main.py"], "cli-tool", test_info)

        assert "`main.py`" in result

    def test_fastapi_strategy_references_app_entry(self):
        structure = {"entry_points": ["app/main.py"], "patterns": ["fastapi-api"]}
        test_info = {"framework": "pytest", "has_conftest": False}

        result = _build_context_strategy(structure, ["app/main.py"], "fastapi-api", test_info)

        assert "`app/main.py`" in result

    def test_django_strategy_includes_migrations_exclude(self):
        structure = {"entry_points": ["manage.py"], "patterns": ["django-app"]}
        test_info = {"framework": "pytest", "has_conftest": False}

        result = _build_context_strategy(structure, ["manage.py"], "django-app", test_info)

        assert "migrations" in result


class TestClineruleContextConfig:
    """Test .clinerules.yaml has context config with exclude patterns."""

    def test_clinerules_has_context_section(self):
        ctx = _make_enhanced_context()
        yaml_str = generate_clinerules("test-project", {"builtin/code-review"}, ctx)
        data = yaml.safe_load(yaml_str)

        assert "context" in data

    def test_clinerules_context_has_exclude(self):
        ctx = _make_enhanced_context()
        yaml_str = generate_clinerules("test-project", {"builtin/code-review"}, ctx)
        data = yaml.safe_load(yaml_str)

        assert "exclude" in data["context"]
        excludes = data["context"]["exclude"]
        assert "**/*.pyc" in excludes
        assert "**/__pycache__/**" in excludes
        assert "**/.venv/**" in excludes

    def test_clinerules_context_has_max_file_size(self):
        ctx = _make_enhanced_context()
        yaml_str = generate_clinerules("test-project", {"builtin/code-review"}, ctx)
        data = yaml.safe_load(yaml_str)

        assert data["context"]["max_file_size"] == 50000

    def test_clinerules_context_has_load_on_demand(self):
        ctx = _make_enhanced_context()
        yaml_str = generate_clinerules("test-project", {"builtin/code-review"}, ctx)
        data = yaml.safe_load(yaml_str)

        assert "load_on_demand" in data["context"]
        lod = data["context"]["load_on_demand"]
        assert "tests/" in lod
        assert "docs/" in lod

    def test_build_context_config_without_context(self):
        result = _build_context_config(None)

        assert "exclude" in result
        assert "max_file_size" in result
        assert "load_on_demand" in result


class TestSkillPromptFileHints:
    """Test skill prompts include relevant_files."""

    def test_skill_prompt_has_relevant_files_section(self):
        ctx = _make_enhanced_context(
            python_deps=["fastapi"],
            tech_stack=["python"],
            entry_points=["app/main.py"],
        )
        result = build_skill_prompt(
            skill_topic="api-validation",
            project_name="my-api",
            context=ctx,
            code_examples=[],
            detected_patterns=["fastapi-api"],
        )

        assert "RELEVANT FILES" in result
        assert "EXCLUDE FILES" in result

    def test_skill_prompt_relevant_files_match_topic(self):
        ctx = _make_enhanced_context(
            python_deps=["fastapi"],
            tech_stack=["python"],
            entry_points=["app/main.py"],
        )
        result = build_skill_prompt(
            skill_topic="api-validation",
            project_name="my-api",
            context=ctx,
            code_examples=[],
            detected_patterns=["fastapi-api"],
        )

        # api topic should include routes/endpoints patterns
        assert "routes" in result or "api" in result

    def test_detect_relevant_files_for_test_topic(self):
        ctx = _make_enhanced_context(
            test_framework="pytest",
            entry_points=["main.py"],
        )
        relevant, exclude = _detect_relevant_files("test-coverage", ctx, None)

        assert any("test" in f for f in relevant)

    def test_detect_relevant_files_for_auth_topic(self):
        ctx = _make_enhanced_context(entry_points=["app/main.py"])
        relevant, exclude = _detect_relevant_files("auth-patterns", ctx, None)

        assert any("auth" in f for f in relevant)

    def test_detect_relevant_files_for_docker_topic(self):
        ctx = _make_enhanced_context(entry_points=["main.py"])
        relevant, exclude = _detect_relevant_files("docker-setup", ctx, None)

        assert any("Dockerfile" in f or "docker" in f for f in relevant)

    def test_detect_relevant_files_fallback(self):
        """Unknown topic should still return something."""
        ctx = _make_enhanced_context(
            tech_stack=["python"],
            entry_points=["main.py"],
        )
        relevant, exclude = _detect_relevant_files("unknown-topic", ctx, None)

        assert len(relevant) > 0
