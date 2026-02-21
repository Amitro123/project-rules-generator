import json

import pytest
import yaml

from generator.renderers import (
    JsonSkillRenderer,
    MarkdownSkillRenderer,
    YamlSkillRenderer,
)

# NOTE: skills_generator.py removed in v1.1 - generate_skills tests are skipped
from generator.types import Skill, SkillFile


@pytest.fixture
def sample_skill():
    return Skill(
        name="test-skill",
        description="A test skill",
        category="core",
        triggers=["test", "verify"],
        tools=["pytest"],
        when_to_use=["Taking a test"],
        avoid_if=["Not testing"],
        input_desc="Test input",
        output_desc="Test output",
        usage_example="run test",
        params={"timeout": 10},
    )


@pytest.fixture
def sample_skill_file(sample_skill):
    return SkillFile(
        project_name="unit-test-project",
        project_type="agent",
        skills=[sample_skill],
        confidence=0.95,
        tech_stack=["python", "pytest"],
        description="A project for unit testing",
    )


def test_skill_to_dict(sample_skill):
    data = sample_skill.to_dict()
    assert data["name"] == "test-skill"
    assert data["triggers"] == ["test", "verify"]
    assert data["params"]["timeout"] == 10


def test_json_renderer(sample_skill_file):
    renderer = JsonSkillRenderer()
    output = renderer.render(sample_skill_file)
    data = json.loads(output)

    assert data["meta"]["project"] == "unit-test-project"
    assert data["meta"]["version"] == "1.0"
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "test-skill"


def test_yaml_renderer(sample_skill_file):
    renderer = YamlSkillRenderer()
    output = renderer.render(sample_skill_file)
    data = yaml.safe_load(output)

    assert data["meta"]["project"] == "unit-test-project"
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "test-skill"


def test_markdown_renderer(sample_skill_file):
    renderer = MarkdownSkillRenderer()
    output = renderer.render(sample_skill_file)

    assert "project: unit-test-project" in output
    assert "## CORE SKILLS" in output
    assert "### test-skill" in output
    assert "**Tools:** pytest" in output
    assert "**Triggers:**" in output
    assert "- verify" in output


def test_generate_skills_integration():
    """Legacy test - skills_generator removed in v1.1."""
    pytest.skip("skills_generator.py removed in v1.1 - use SkillsManager.create_skill()")
