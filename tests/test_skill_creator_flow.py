
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from generator.skill_creator import CoworkSkillCreator
from generator.skill_discovery import SkillDiscovery

class TestSkillCreatorFlow:
    @pytest.fixture
    def mock_discovery(self):
        with patch("generator.skill_creator.SkillDiscovery") as MockDiscovery:
            # Setup the mock instance
            mock_instance = MockDiscovery.return_value
            
            # Create temporary directories for the mock to use
            self.temp_global = tempfile.TemporaryDirectory()
            self.temp_global_learned = Path(self.temp_global.name) / "learned"
            self.temp_global_learned.mkdir(parents=True)
            
            mock_instance.global_learned = self.temp_global_learned
            mock_instance.ensure_global_structure = MagicMock()
            mock_instance.setup_project_structure = MagicMock()
            
            yield mock_instance
            
            self.temp_global.cleanup()

    def test_generate_all_creates_new_skill(self, mock_discovery, tmp_path):
        """Test that generate_all creates a new skill if it doesn't exist globally."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        (project_path / "README.md").write_text("# Test Project\n\nUses FastAPI.")
        
        creator = CoworkSkillCreator(project_path)
        # Verify the mock was injected (since we patched the class import in skill_creator)
        assert creator.discovery == mock_discovery
        
        # Override detect_skill_needs to return a specific skill for predictability
        creator.detect_skill_needs = MagicMock(return_value=["fastapi-api-workflow"])
        
        # Run generate_all
        creator.generate_all()
        
        # Verify ensure_global_structure called
        mock_discovery.ensure_global_structure.assert_called_once()
        
        # Verify skill file created in GLOBAL learned
        expected_skill_file = mock_discovery.global_learned / "fastapi-api-workflow.md"
        assert expected_skill_file.exists()
        assert "FastAPI" in expected_skill_file.read_text(encoding="utf-8")

    def test_generate_all_reuses_existing_skill(self, mock_discovery, tmp_path):
        """Test that generate_all reuses an existing global skill."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        
        # Pre-populate global learned
        skill_name = "existing-skill"
        (mock_discovery.global_learned / f"{skill_name}.md").write_text("Existing Content")
        
        creator = CoworkSkillCreator(project_path)
        creator.detect_skill_needs = MagicMock(return_value=[skill_name])
        
        # Mock create_skill to ensure it's NOT called for creation (logic check)
        # But wait, create_skill is called inside generate_all only if exists_in_learned is False.
        # We can spy on save_to_learned or check file mtime/content.
        
        with patch.object(creator, 'create_skill') as mock_create:
            creator.generate_all()
            
            # create_skill should NOT be called because it exists
            mock_create.assert_not_called()
            
        # Verify setup_project_structure (symlinks) called
        mock_discovery.setup_project_structure.assert_called()

