import shutil
from pathlib import Path
import pytest
from unittest.mock import patch

from generator.skill_creator import CoworkSkillCreator
from generator.skill_discovery import SkillDiscovery

@pytest.fixture
def mock_global_home(tmp_path):
    """Mock User Home for global cache."""
    with patch("generator.skill_discovery.Path.home", return_value=tmp_path):
        yield tmp_path

class TestRestoreLearnedFlow:
    
    def test_end_to_end_restore_flow(self, tmp_path, mock_global_home):
        """
        Verify the restored logic:
        1. Detects pytest-testing-workflow
        2. Creates it in GLOBAL learned (mock_global_home)
        3. Links it to PROJECT skills/project
        4. Reuses it on second run
        """
        # 1. Setup Project
        project_dir = tmp_path / "my_project"
        project_dir.mkdir()
        (project_dir / "README.md").write_text("# My Project\n\nUses pytest for testing.")
        (project_dir / "requirements.txt").write_text("pytest\n")
        (project_dir / "tests").mkdir()
        (project_dir / "tests" / "test_foo.py").write_text("def test_foo(): pass")

        # 2. Run generate_all (First Run - Creation)
        creator = CoworkSkillCreator(project_dir)
        creator.generate_all(use_ai=False) # Use template/default logic if AI false

        # Checks
        # Global Cache Population
        global_learned = mock_global_home / ".project-rules-generator" / "learned"
        assert global_learned.exists()
        skill_file = global_learned / "pytest-testing-workflow.md"
        assert skill_file.exists()
        assert "pytest" in skill_file.read_text(encoding="utf-8")

        # Project Link
        project_skills = project_dir / ".clinerules" / "skills" / "project"
        assert project_skills.exists()
        project_skill = project_skills / "pytest-testing-workflow.md"
        assert project_skill.exists()
        
        # Verify content/symlink
        # Note: In test env, it might be a copy depending on OS privileges, but content must match
        assert project_skill.read_text(encoding="utf-8") == skill_file.read_text(encoding="utf-8")

        # 3. Modify Global (Simulate learning/evolving)
        skill_file.write_text("Updated Global Content", encoding="utf-8")

        # 4. Run generate_all (Second Run - Reuse)
        # It should link the updated global file (if symlink) or overwrite/skip?
        # link_from_learned does _link_or_copy. If target exists, it might skip if symlink correct?
        # Let's clean project skill to force re-link/re-copy
        project_skill.unlink()
        
        creator.generate_all(use_ai=False)
        
        # Output capture would show "♻️ Reusing"
        
        # Verify it brought back the updated content
        assert project_skill.exists()
        assert project_skill.read_text(encoding="utf-8") == "Updated Global Content"

    def test_tool_selection_includes_tox(self, tmp_path, mock_global_home):
        project_dir = tmp_path / "tox_project"
        project_dir.mkdir()
        (project_dir / "README.md").write_text("Pytest project", encoding="utf-8")
        (project_dir / "requirements.txt").write_text("pytest\ntox\ncoverage", encoding="utf-8")
        
        creator = CoworkSkillCreator(project_dir)
        
        # Directly test _select_tools
        tools = creator._select_tools("pytest-testing-workflow", ["pytest"])
        assert "tox" in tools
        assert "pytest" in tools
        assert "coverage" in tools
