from click.testing import CliRunner
from main import main
from pathlib import Path
from unittest.mock import patch, MagicMock
from generator.skills_manager import SkillsManager
import pytest

@pytest.fixture
def temp_skills_dir(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "builtin").mkdir()
    (skills_dir / "learned").mkdir()
    (skills_dir / "awesome").mkdir()

    # Create a dummy builtin skill
    (skills_dir / "builtin" / "brainstorming").mkdir()
    (skills_dir / "builtin" / "brainstorming" / "SKILL.md").write_text("# Brainstorming")

    return skills_dir

@pytest.fixture
def mock_manager(temp_skills_dir):
    def side_effect(*args, **kwargs):
        # Allow any args, return manager pointing to temp dir for functional tests
        # We ignore the path passed by main.py in functional tests to keep setup simple
        return SkillsManager(base_path=temp_skills_dir)
    return side_effect

def test_list_skills(temp_skills_dir, mock_manager):
    runner = CliRunner()
    with patch("main.SkillsManager", side_effect=mock_manager):
        result = runner.invoke(main, ['--list-skills'])
        assert result.exit_code == 0
        assert "Available Skills" in result.output
        assert "Builtin" in result.output
        assert "brainstorming" in result.output

def test_create_skill(temp_skills_dir, mock_manager):
    runner = CliRunner()
    with patch("main.SkillsManager", side_effect=mock_manager):
        result = runner.invoke(main, ['--create-skill', 'new-skill'])
        assert result.exit_code == 0
        assert "Created new skill 'new-skill'" in result.output

        skill_path = temp_skills_dir / "learned" / "new-skill" / "SKILL.md"
        assert skill_path.exists()
        # Assert updated template format
        assert "# Skill: New Skill" in skill_path.read_text()

def test_create_skill_sanitization(temp_skills_dir, mock_manager):
    runner = CliRunner()
    with patch("main.SkillsManager", side_effect=mock_manager):
        result = runner.invoke(main, ['--create-skill', 'bad name!'])
        # It should sanitize 'bad name!' to 'badname' and succeed
        assert result.exit_code == 0
        # We now expect the sanitized name in the output
        assert "Created new skill 'badname'" in result.output

        skill_path = temp_skills_dir / "learned" / "badname" / "SKILL.md"
        assert skill_path.exists()

def test_create_skill_from_readme(temp_skills_dir, mock_manager, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("Project Description")

    runner = CliRunner()
    with patch("main.SkillsManager", side_effect=mock_manager):
        result = runner.invoke(main, ['--create-skill', 'readme-skill', '--from-readme', str(readme)])
        assert result.exit_code == 0

        skill_path = temp_skills_dir / "learned" / "readme-skill" / "SKILL.md"
        assert skill_path.exists()
        # Assert updated context format
        assert "## Context (from README.md)" in skill_path.read_text()

def test_create_duplicate_skill(temp_skills_dir, mock_manager):
    runner = CliRunner()
    with patch("main.SkillsManager", side_effect=mock_manager):
        runner.invoke(main, ['--create-skill', 'dup-skill'])
        result = runner.invoke(main, ['--create-skill', 'dup-skill'])
        assert result.exit_code == 1
        assert "Failed to create skill" in result.output

def test_cli_respects_project_path(tmp_path):
    target_dir = tmp_path / "target_project"
    target_dir.mkdir()

    runner = CliRunner()
    with patch("main.SkillsManager") as MockClass:
        # Mocking list_skills to return a structure that won't cause main.py to crash on sum()
        MockClass.return_value.list_skills.return_value = {'builtin': ['skill1']}
        
        result = runner.invoke(main, [str(target_dir), '--list-skills'])

        assert result.exit_code == 0
        expected_path = target_dir.resolve() / "skills"
        MockClass.assert_called_with(base_path=expected_path)
