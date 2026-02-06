import pytest
from generator.orchestrator import SkillOrchestrator
from generator.sources.builtin import BuiltinSkillsSource
from pathlib import Path

@pytest.fixture
def mock_config():
    return {
        "skill_sources": {
            "builtin": {
                "enabled": True,
                "path": "templates/skills"
            },
            "preference_order": ["builtin", "awesome", "learned"]
        }
    }

@pytest.fixture
def mock_project_data():
    return {
        "name": "test-project",
        "tech_stack": ["fastapi"],
        "features": [],
        "description": "A test project",
        "raw_readme": "# Test Project\nBuilt with FastAPI."
    }

@pytest.fixture
def orchestrator(mock_config, tmp_path):
    orch = SkillOrchestrator(mock_config)
    # Using real BuiltinSource but pointing to temp dir
    skills_dir = tmp_path / "templates" / "skills"
    skills_dir.mkdir(parents=True)
    
    # Create fake skills
    import yaml
    (skills_dir / "fastapi.yaml").write_text(yaml.dump([
        {"name": "fastapi-expert", "description": "Expert in {project_name}", "category": "tech"}
    ]))
    (skills_dir / "core.yaml").write_text(yaml.dump([
        {"name": "core", "description": "Core stuff", "category": "core"}
    ]))
    
    source = BuiltinSkillsSource(mock_config, templates_dir=skills_dir)
    orch.register_source(source)
    return orch

def test_orchestrator_flow(orchestrator, mock_project_data, tmp_path):
    skills = orchestrator.orchestrate(mock_project_data, str(tmp_path))
    
    skill_names = [s.name for s in skills]
    assert "fastapi-expert" in skill_names
    assert "core" in skill_names
    
    # Check adaption
    fastapi_skill = next(s for s in skills if s.name == "fastapi-expert")
    assert "test-project" in fastapi_skill.description
    assert fastapi_skill.adapted_for == "test-project"
