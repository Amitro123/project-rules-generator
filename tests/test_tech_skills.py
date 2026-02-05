import pytest
from generator.skills_generator import generate_skills

def test_generate_tech_skills_react():
    project_data = {
        'name': 'react-app',
        'tech_stack': ['react', 'javascript'],
        'features': [],
        'description': 'A react app'
    }
    config = {}
    
    # Mock detection by ignoring path (project_path='.' will fallback to CLI/Generator but that's fine)
    # We care about the TECH SPECIFIC SKILLS section
    
    content = generate_skills(project_data, config, '.')
    
    assert "## TECH SKILLS" in content
    assert "react-expert" in content
    assert "Performance optimization (memoization)" in content

def test_generate_tech_skills_mixed():
    project_data = {
        'name': 'fullstack-app',
        'tech_stack': ['fastapi', 'react', 'docker'],
        'features': [],
        'description': 'Fullstack'
    }
    config = {}
    
    content = generate_skills(project_data, config, '.')
    
    assert "fastapi-security-auditor" in content
    assert "react-expert" in content
    assert "docker-optimizer" in content

def test_generate_fallback_expert(tmp_path):
    # Use a name that triggers 'generator' type (which has no default skills yet)
    # to ensure we hit the fallback path.
    # Also use tmp_path to avoid detecting 'cli_tool' from the repo itself.
    project_data = {
        'name': 'rust-generator',
        'tech_stack': ['rust'],
        'features': [],
        'description': 'Rust app'
    }
    config = {}
    
    content = generate_skills(project_data, config, str(tmp_path))
    
    # 'rust' is not in TECH_SPECIFIC_SKILLS, should generate fallback
    assert "rust-expert" in content
