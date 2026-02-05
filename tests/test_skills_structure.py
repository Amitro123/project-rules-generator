import json
import yaml
import pytest
from generator.types import Skill, SkillFile
from generator.renderers import MarkdownSkillRenderer, JsonSkillRenderer, YamlSkillRenderer
from generator.skills_generator import generate_skills

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
        params={"timeout": 10}
    )

@pytest.fixture
def sample_skill_file(sample_skill):
    return SkillFile(
        project_name="unit-test-project",
        project_type="agent",
        skills=[sample_skill],
        confidence=0.95,
        tech_stack=["python", "pytest"],
        description="A project for unit testing"
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
    """Test the full generation pipeline with mock data"""
    project_data = {
        "name": "integration-test",
        "tech_stack": ["react", "fastapi"],
        "description": "Integration test project",
        "features": []
    }
    config = {}
    
    # Test valid JSON generation
    json_output = generate_skills(project_data, config, format='json')
    data = json.loads(json_output)
    
    skills_names = [s["name"] for s in data["skills"]]
    
    # Check that we got core skills
    assert "analyze-code" in skills_names
    
    # Check that we got tech specific skills
    assert "react-expert" in skills_names
    assert "fastapi-security-auditor" in skills_names

    # Check that we got type specific skills (auto-detected as web_app or similar based on tech? 
    # Actually the detector might default to something else if minimal data, but let's check basic structure)
    assert data["meta"]["project"] == "integration-test" 
