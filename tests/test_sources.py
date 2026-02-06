import pytest
import yaml
from pathlib import Path
from generator.sources.builtin import BuiltinSkillsSource
from generator.types import SkillNeed

@pytest.fixture
def mock_templates_dir(tmp_path):
    """Create a temporary templates directory with some skill files."""
    skills_dir = tmp_path / "templates" / "skills"
    skills_dir.mkdir(parents=True)
    
    # Create a generic tech skill
    tech_skill = {
        "name": "fastapi-expert",
        "description": "Expert in FastAPI",
        "category": "tech",
        "triggers": ["fastapi"]
    }
    (skills_dir / "fastapi.yaml").write_text(yaml.dump([tech_skill]))
    
    # Create a project type skill
    type_skill = {
        "name": "model-reviewer",
        "description": "Review ML models",
        "category": "ml_pipeline"
    }
    (skills_dir / "ml.yaml").write_text(yaml.dump([type_skill]))
    
    return skills_dir

@pytest.fixture
def mock_config():
    return {
        "skill_sources": {
            "builtin": {
                "enabled": True,
                "path": "templates/skills"
            },
            "learned": {
                "enabled": True,
                "path": "~/.project-rules-generator/learned_skills"
            },
            "awesome": {
                "enabled": False,
                "path": ""
            },
            "preference_order": ["builtin", "awesome", "learned"]
        }
    }

def test_builtin_source_priority(mock_config, mock_templates_dir):
    source = BuiltinSkillsSource(mock_config, templates_dir=mock_templates_dir)
    # Priority logic: len(order) - index
    # order = ['builtin', 'awesome', 'learned']
    # len=3, index('builtin')=0 => 3-0 = 3
    assert source.priority == 3

def test_builtin_discovery_exact_match(mock_config, mock_templates_dir):
    source = BuiltinSkillsSource(mock_config, templates_dir=mock_templates_dir)
    
    needs = [SkillNeed(type="tech", name="fastapi-expert", confidence=1.0)]
    found = source.discover(needs)
    
    assert len(found) >= 1
    assert found[0].name == "fastapi-expert"
    assert found[0].source == "builtin"

def test_builtin_discovery_keyword_match(mock_config, mock_templates_dir):
    source = BuiltinSkillsSource(mock_config, templates_dir=mock_templates_dir)
    
    needs = [SkillNeed(type="tech", name="fastapi", confidence=1.0)]
    found = source.discover(needs)
    
    assert len(found) >= 1
    assert found[0].name == "fastapi-expert"

def test_builtin_discovery_category_match(mock_config, mock_templates_dir):
    source = BuiltinSkillsSource(mock_config, templates_dir=mock_templates_dir)
    
    needs = [SkillNeed(type="project_type", name="ml_pipeline", confidence=1.0)]
    found = source.discover(needs)
    
    assert len(found) >= 1
    assert found[0].name == "model-reviewer"

# Learned Source Tests
from generator.sources.learned import LearnedSkillsSource

@pytest.fixture
def mock_learned_dir(tmp_path):
    learned_dir = tmp_path / "learned_skills"
    learned_dir.mkdir()
    
    skill = {
        "name": "custom-audit",
        "category": "core",
        "description": "Custom audit skill"
    }
    (learned_dir / "my_skills.yaml").write_text(yaml.dump([skill]))
    return learned_dir

def test_learned_source_discovery(mock_config, mock_learned_dir):
    # Update config to point to temp dir
    mock_config['skill_sources']['learned']['path'] = str(mock_learned_dir)
    
    source = LearnedSkillsSource(mock_config)
    needs = [SkillNeed(type="pattern", name="custom-audit", confidence=1.0)]
    
    found = source.discover(needs)
    assert len(found) == 1
    assert found[0].name == "custom-audit"
    assert found[0].source == "learned"

# Awesome Source Tests
from generator.sources.awesome import AwesomeSkillsSource

def test_awesome_source_discovery(mock_config):
    # Point to the fixtures directory
    fixtures_path = Path("tests/fixtures/awesome-skills")
    
    mock_config['skill_sources']['awesome']['enabled'] = True
    mock_config['skill_sources']['awesome']['path'] = str(fixtures_path)
    
    source = AwesomeSkillsSource(mock_config)
    
    # Test 1: Discover by tech match (fastapi)
    needs = [SkillNeed(type="tech", name="fastapi", confidence=1.0)]
    found = source.discover(needs)
    
    assert len(found) >= 1
    names = [s.name for s in found]
    assert "fastapi-security-auditor" in names
    assert found[0].source == "awesome-skills"
    
    # Test 2: Discover by tech match (react)
    needs = [SkillNeed(type="tech", name="react", confidence=1.0)]
    found = source.discover(needs)
    
    names = [s.name for s in found]
    assert "react-expert" in names
    
    # Test 3: Match with files context
    # Create a need that matches files
    needs = [SkillNeed(
        type="core", 
        name="custom-check", 
        confidence=1.0, 
        context={"files": ["main.py", "app.py"]} # These match fastapi-security-auditor matches
    )]
    found = source.discover(needs)
    # The skill name isn't 'custom-check', but it matches on 'files'
    # Wait, my logic checks score >= 0.5. 
    # File match gives 0.7 if overlap.
    # But does _calculate_match_score require name match?
    # No, it adds max score.
    # So it should find it.
    
    names = [s.name for s in found]
    assert "fastapi-security-auditor" in names
