"""Tests for rules and skills generators."""
import pytest
from generator.rules_generator import generate_rules
from generator.skills_generator import generate_skills


class TestRulesGenerator:
    """Test suite for rules generation."""

    def test_generate_rules_structure(self, mock_config):
        """Test that generated rules has correct structure."""
        project_data = {
            'name': 'test-project',
            'description': 'A test project description',
            'tech_stack': ['python', 'fastapi'],
            'features': ['Feature one', 'Feature two', 'Feature three']
        }
        
        result = generate_rules(project_data, mock_config)
        
        # Check YAML frontmatter
        assert result.startswith('---')
        assert 'project: test-project' in result
        
        # Check required sections
        assert '## CONTEXT' in result
        assert '## DO' in result
        assert "## DON'T" in result or "## DON'T" in result
        assert '## PRIORITIES' in result
        assert '## WORKFLOWS' in result
    
    def test_generate_rules_with_tech_stack(self, mock_config):
        """Test that tech stack is included in rules."""
        project_data = {
            'name': 'test-project',
            'description': 'A test project',
            'tech_stack': ['python', 'django', 'postgresql'],
            'features': []
        }
        
        result = generate_rules(project_data, mock_config)
        
        assert 'python, django, postgresql' in result
        assert 'Use python, django, postgresql' in result
    
    def test_generate_rules_with_features_as_priorities(self, mock_config):
        """Test that features become priorities."""
        project_data = {
            'name': 'test-project',
            'description': 'A test project',
            'tech_stack': ['python'],
            'features': ['Fast processing', 'Easy config', 'Good tests']
        }
        
        result = generate_rules(project_data, mock_config)
        
        assert '1. Fast processing' in result
        assert '2. Easy config' in result
        assert '3. Good tests' in result
    
    def test_generate_rules_default_priorities(self, mock_config):
        """Test default priorities when no features."""
        project_data = {
            'name': 'test-project',
            'description': 'A test project',
            'tech_stack': [],
            'features': []
        }
        
        result = generate_rules(project_data, mock_config)
        
        # Should have default priorities
        assert '## PRIORITIES' in result
        assert '1.' in result
        assert '2.' in result
        assert '3.' in result
    
    def test_generate_rules_description_truncation(self, mock_config):
        """Test that long descriptions are truncated."""
        long_desc = 'A' * 300
        project_data = {
            'name': 'test-project',
            'description': long_desc,
            'tech_stack': [],
            'features': []
        }
        
        result = generate_rules(project_data, mock_config)
        
        # Description should be truncated with ...
        assert '...' in result


class TestSkillsGenerator:
    """Test suite for skills generation."""

    def test_generate_skills_structure(self, mock_config):
        """Test that generated skills has correct structure."""
        project_data = {
            'name': 'test-project',
            'description': 'A test project',
            'tech_stack': ['python'],
            'features': ['Feature one']
        }
        
        result = generate_skills(project_data, mock_config)
        
        # Check YAML frontmatter
        assert result.startswith('---')
        assert 'project: test-project' in result
        
        # Check required sections
        assert '## CORE SKILLS' in result
        assert '### analyze-code' in result
        assert '### refactor-module' in result
        assert '### test-coverage' in result
    
    def test_generate_skills_domain_specific(self, mock_config):
        """Test domain-specific skills based on tech stack."""
        project_data = {
            'name': 'test-project',
            'description': 'A test project',
            'tech_stack': ['react', 'typescript'],
            'features': []
        }
        
        result = generate_skills(project_data, mock_config)
        
        # Should have react specific expert skill
        assert 'react-expert' in result
        assert 'refactor React components' in result
    
    def test_generate_skills_usage_section(self, mock_config):
        """Test that usage instructions are included."""
        project_data = {
            'name': 'my-project',
            'description': 'A test project',
            'tech_stack': ['python'],
            'features': []
        }
        
        result = generate_skills(project_data, mock_config)
        
        assert '## USAGE' in result
        assert '/skills load my-project-skills.md' in result
    
    def test_generate_skills_with_primary_domain(self, mock_config):
        """Test that first tech becomes primary domain."""
        project_data = {
            'name': 'test-project',
            'description': 'A test project',
            'tech_stack': ['fastapi', 'python', 'docker'],
            'features': []
        }
        
        result = generate_skills(project_data, mock_config)
        
        # First tech (fastapi) should use specific template
        assert 'fastapi-security-auditor' in result
        assert 'security issues' in result
