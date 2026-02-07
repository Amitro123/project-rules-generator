import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

# We will import these from the new module once created
# from generator.skills_cli import list_skills_command, create_skill_command
from main import main

class TestSkillsCLI:
    """Tests for the Skills CLI commands."""

    def test_list_skills_flag(self, tmp_path):
        """Test that --list-skills flag triggers the listing."""
        runner = CliRunner()
        
        # Mocking the actual list_skills function to avoid dependency on filesystem state during integration test
        with patch('generator.skills_cli.list_skills') as mock_list:
            result = runner.invoke(main, ['--list-skills'])
            
            # If implementation is correct, it should call list_skills and exit
            assert result.exit_code == 0
            mock_list.assert_called_once()

    def test_create_skill_flag(self, tmp_path):
        """Test that --create-skill flag triggers creation."""
        runner = CliRunner()
        
        with patch('generator.skills_cli.create_skill') as mock_create:
            result = runner.invoke(main, ['--create-skill', 'my-new-skill'])
            
            assert result.exit_code == 0
            mock_create.assert_called_once_with('my-new-skill', None)

    def test_create_skill_from_readme_flag(self, tmp_path):
        """Test that --create-skill with --from-readme passes the path."""
        runner = CliRunner()
        readme = tmp_path / "README.md"
        readme.write_text("# Test")
        
        with patch('generator.skills_cli.create_skill') as mock_create:
            result = runner.invoke(main, ['--create-skill', 'my-new-skill', '--from-readme', str(readme)])
            
            assert result.exit_code == 0
            mock_create.assert_called_once_with('my-new-skill', str(readme))

    
    # Unit tests for the logic (which we will implement in generator/skills_cli.py)
    # We define what we WANT the logic to do here.

    def test_logic_list_skills_output(self, capsys):
        """Test that list_skills prints the correct structure."""
        from generator import skills_cli
        
        # Mock the directory structure search
        # We need to mock how it finds skills. 
        # Assuming it uses a similar discovery mechanism to orchestrator or just scans dirs.
        # Let's assume it scans the default locations.
        
        with patch('pathlib.Path.glob') as mock_glob:
            # Setup mocks for 3 layers
            # This is tricky without the code existing. 
            # Alternatively, we can test it against the REAL filesystem since we just created it in Phase 1!
            
            skills_cli.list_skills()
            captured = capsys.readouterr()
            
            assert "[Built-in] Skills" in captured.out
            assert "brainstorming" in captured.out
            assert "writing-plans" in captured.out
            # We know these exist from Phase 1

    def test_logic_create_skill_basic(self, tmp_path):
        """Test creating a basic skill from template."""
        from generator import skills_cli
        
        # Patch the skills root to use a temp dir so we don't mess up real project
        with patch('generator.skills_cli.get_skills_root', return_value=tmp_path):
            skills_cli.create_skill("test-skill-unit", None)
            
            expected_file = tmp_path / "learned" / "test-skill-unit" / "SKILL.md"
            assert expected_file.exists()
            content = expected_file.read_text()
            assert "# Skill: Test Skill Unit" in content
            assert "## Purpose" in content
