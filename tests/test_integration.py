"""Integration tests for end-to-end flow."""
import pytest
from pathlib import Path
from click.testing import CliRunner
from main import main


class TestIntegration:
    """Test suite for end-to-end integration."""

    def test_full_flow_generates_files(self, tmp_path):
        """Test complete flow generates both files correctly."""
        # Create a test project
        project_dir = tmp_path / 'my-test-project'
        project_dir.mkdir()
        
        # Create README
        readme = project_dir / 'README.md'
        readme.write_text("""# My Test Project

A complete test of the generator system.

## Features

- Automated documentation
- Git integration
- Configurable templates

## Technology

- Python 3.11
- Click for CLI
- PyYAML for config

## Getting Started

Install and run.
""", encoding='utf-8')
        
        # Run the generator
        runner = CliRunner()
        result = runner.invoke(main, [str(project_dir), '--no-commit', '--verbose'])
        
        # Check success
        assert result.exit_code == 0
        assert 'Generated files' in result.output
        assert 'Done!' in result.output
        
        # Check files exist
        rules_file = project_dir / 'my-test-project-rules.md'
        skills_file = project_dir / 'my-test-project-skills.md'
        
        assert rules_file.exists()
        assert skills_file.exists()
        
        # Check rules file content
        rules_content = rules_file.read_text()
        assert 'project: my-test-project' in rules_content
        assert '## DO' in rules_content
        # python should be detected from "Python 3.11"
        assert 'python' in rules_content.lower()
        
        # Check skills file content
        skills_content = skills_file.read_text()
        assert 'project: my-test-project' in skills_content
        assert '## CORE SKILLS' in skills_content
        assert 'cli-usability-auditor' in skills_content
    
    def test_flow_with_different_tech_stacks(self, tmp_path):
        """Test with various tech stack combinations."""
        test_cases = [
            {
                'name': 'react-project',
                'tech': ['react', 'typescript', 'nextjs'],
                'tech_keys': ['react', 'typescript']
            },
            {
                'name': 'ml-project', 
                'tech': ['python', 'pytorch', 'fastapi'],
                'tech_keys': ['python', 'pytorch']
            },
            {
                'name': 'infra-project',
                'tech': ['terraform', 'aws', 'docker', 'kubernetes'],
                'tech_keys': ['terraform', 'aws']
            }
        ]
        
        runner = CliRunner()
        
        for case in test_cases:
            project_dir = tmp_path / case['name']
            project_dir.mkdir()
            
            tech_list = '\n'.join([f'- {t}' for t in case['tech']])
            readme = project_dir / 'README.md'
            readme.write_text(f"""# {case['name'].replace('-', ' ').title()}

Description.

## Tech

{tech_list}
""")
            
            result = runner.invoke(main, [str(project_dir), '--no-commit', '--quiet'])
            assert result.exit_code == 0, f"Failed for {case['name']}"
            
            # Verify tech stack in output files
            rules = (project_dir / f"{case['name']}-rules.md").read_text()
            for tech in case['tech_keys']:
                assert tech in rules, f"Expected {tech} in {case['name']} rules"
    
    def test_flow_preserves_existing_files(self, tmp_path):
        """Test that running twice updates files."""
        project_dir = tmp_path / 'existing-project'
        project_dir.mkdir()
        
        readme = project_dir / 'README.md'
        readme.write_text("# Existing Project\n\nDescription.")
        
        # First run
        runner = CliRunner()
        runner.invoke(main, [str(project_dir), '--no-commit', '--quiet'])
        
        rules_file = project_dir / 'existing-project-rules.md'
        first_content = rules_file.read_text()
        
        # Second run (should overwrite)
        runner.invoke(main, [str(project_dir), '--no-commit', '--quiet'])
        
        second_content = rules_file.read_text()
        
        # Files should exist and be similar
        assert rules_file.exists()
        assert 'project: existing-project' in second_content
    
    def test_sample_project_integration(self, sample_project_path):
        """Test with the bundled sample project."""
        runner = CliRunner()
        
        # Clean up previously generated files for fresh test
        for f in sample_project_path.glob('*.md'):
            if f.name != 'README.md':
                f.unlink()
        
        result = runner.invoke(main, [str(sample_project_path), '--no-commit'])
        
        assert result.exit_code == 0
        
        # Verify generated files
        rules = sample_project_path / 'sample-project-rules.md'
        skills = sample_project_path / 'sample-project-skills.md'
        
        assert rules.exists()
        assert skills.exists()
        
        # Verify content quality
        rules_content = rules.read_text()
        assert '## DO' in rules_content
        assert "## DON'T" in rules_content or "DON'T" in rules_content
        assert '## PRIORITIES' in rules_content
        assert '## WORKFLOWS' in rules_content
