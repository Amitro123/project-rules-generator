from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cli.cli import cli as main
from generator.skills_manager import SkillsManager


@pytest.fixture
def temp_skills_dir(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "builtin").mkdir()
    (skills_dir / "learned").mkdir()

    # Create a dummy builtin skill
    (skills_dir / "builtin" / "brainstorming").mkdir()
    (skills_dir / "builtin" / "brainstorming" / "SKILL.md").write_text("# Brainstorming")

    return skills_dir


@pytest.fixture
def mock_manager(temp_skills_dir):
    def side_effect(*args, **kwargs):
        # Allow any args, return manager pointing to temp dir for functional tests
        # We override learned to use our temp dir instead of user home
        manager = SkillsManager(project_path=temp_skills_dir)
        manager.discovery.global_learned = temp_skills_dir / "learned"
        manager.global_learned = temp_skills_dir / "learned"
        return manager

    return side_effect


def test_cli_respects_project_path(tmp_path):
    target_dir = tmp_path / "target_project"
    target_dir.mkdir()

    runner = CliRunner()
    with patch("cli.skills_cmd.SkillsManager") as MockClass:
        MockClass.return_value.list_skills.return_value = {"skill1": {"type": "builtin", "path": "path/to/skill1"}}
        MockClass.return_value.project_path = target_dir

        result = runner.invoke(main, ["skills", "list", str(target_dir)])

        assert result.exit_code == 0
        MockClass.assert_called_with(project_path=target_dir)


def test_list_skills(temp_skills_dir, mock_manager):
    runner = CliRunner()
    with patch("cli.skills_cmd.SkillsManager", side_effect=mock_manager):
        result = runner.invoke(main, ["skills", "list", str(temp_skills_dir), "--all"])
        assert result.exit_code == 0
        assert "brainstorming" in result.output


def test_create_skill(temp_skills_dir, mock_manager):
    runner = CliRunner()
    llm_output = "# Skill: New Skill\n\n## Purpose\nTest skill.\n"
    with patch("cli.skills_cmd.SkillsManager", side_effect=mock_manager), patch(
        "generator.llm_skill_generator.LLMSkillGenerator.generate_skill", return_value=llm_output
    ):
        result = runner.invoke(main, ["skills", "create", "new-skill", str(temp_skills_dir)])

        assert result.exit_code == 0, result.output
        assert "Created new skill 'new-skill'" in result.output

        skill_path = temp_skills_dir / "learned" / "new-skill" / "SKILL.md"
        assert skill_path.exists()
        assert "# Skill: New Skill" in skill_path.read_text(encoding="utf-8")


def test_create_skill_sanitization(temp_skills_dir, mock_manager):
    runner = CliRunner()
    with patch("cli.skills_cmd.SkillsManager", side_effect=mock_manager):
        result = runner.invoke(main, ["skills", "create", "bad name!", str(temp_skills_dir)])
        # It should sanitize 'bad name!' to 'bad-name' and succeed
        assert result.exit_code == 0
        # We now expect the sanitized name in the output
        assert "Created new skill 'bad-name'" in result.output

        skill_path = temp_skills_dir / "learned" / "bad-name" / "SKILL.md"
        assert skill_path.exists()


def test_create_skill_from_readme(temp_skills_dir, mock_manager, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        """# Test Project
Description of test project.

## Installation
1. Run install command.

## Quick Start
1. Run usage command.
""",
        encoding="utf-8",
    )

    runner = CliRunner()
    with patch("cli.skills_cmd.SkillsManager", side_effect=mock_manager):
        # Use "test-project" so the skill name words ("test", "project") appear in the
        # README purpose ("Description of test project.") and READMEStrategy returns
        # content rather than falling through to StubStrategy.
        result = runner.invoke(
            main,
            ["skills", "create", "test-project", str(temp_skills_dir), "--from-readme", str(readme)],
        )
        assert result.exit_code == 0, result.output

        skill_path = temp_skills_dir / "learned" / "test-project" / "SKILL.md"
        assert skill_path.exists()
        content = skill_path.read_text(encoding="utf-8")

        # Assert smart filling
        assert "Description of test project" in content  # Purpose
        assert "Run install command" in content  # Process (Installation)
        assert "Run usage command" in content  # Process (Usage/Quick Start)

        # Anti-Patterns section header should be present
        assert "## Anti-Patterns" in content

        # Context
        assert "## Context (from README)" in content


def test_create_duplicate_skill(temp_skills_dir, mock_manager):
    runner = CliRunner()
    with patch("cli.skills_cmd.SkillsManager", side_effect=mock_manager):
        runner.invoke(main, ["skills", "create", "dup-skill", str(temp_skills_dir)])
        result = runner.invoke(main, ["skills", "create", "dup-skill", str(temp_skills_dir)])
        assert result.exit_code == 0
        assert "Updating" in result.output or "Created" in result.output


def test_remove_skill(temp_skills_dir, mock_manager):
    runner = CliRunner()
    with patch("cli.skills_cmd.SkillsManager", side_effect=mock_manager):
        runner.invoke(main, ["skills", "create", "to-remove", str(temp_skills_dir)])
        result = runner.invoke(main, ["skills", "remove", "to-remove", str(temp_skills_dir)])
        assert result.exit_code == 0
        assert "Removed" in result.output
        skill_path = temp_skills_dir / "learned" / "to-remove"
        assert not skill_path.exists()


def test_remove_nonexistent_skill_exits_1(temp_skills_dir, mock_manager):
    runner = CliRunner()
    with patch("cli.skills_cmd.SkillsManager", side_effect=mock_manager):
        result = runner.invoke(main, ["skills", "remove", "no-such-skill", str(temp_skills_dir)])
        assert result.exit_code != 0


def test_remove_skill_path_traversal_blocked(temp_skills_dir, mock_manager):
    """Path traversal attempts (../../) must be rejected with a non-zero exit code."""
    runner = CliRunner()
    with patch("cli.skills_cmd.SkillsManager", side_effect=mock_manager):
        result = runner.invoke(main, ["skills", "remove", "../../etc/passwd", str(temp_skills_dir)])
        assert result.exit_code != 0
        assert "Invalid" in result.output or result.exit_code != 0
