"""Tests for AI-powered skill generation."""

import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import shutil

from src.skills.skill_manager import SkillsManager

class TestAISkillGeneration(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_ai_skills")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)
        
        # Mock home directory for SkillsManager
        self.original_home = Path.home
        # Create a function that returns the test path
        self.home_patch = patch('pathlib.Path.home', return_value=self.test_dir)
        self.home_patch.start()
        
    def tearDown(self):
        self.home_patch.stop()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch('generator.project_analyzer.ProjectAnalyzer')
    @patch('src.ai.ai_client.AIClientFactory.get_client')
    def test_create_skill_with_ai(self, mock_get_client, mock_analyzer_cls):
        """Test create_skill calls AI components when use_ai=True."""
        # Setup mocks
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {'context': 'dummy'}
        mock_analyzer_cls.return_value = mock_analyzer
        
        mock_client = MagicMock()
        # The prompt is complex, so we just mock the return
        mock_client.generate_content.return_value = "# Skill: AI Test\n\n## Purpose\nAI Generated"
        mock_get_client.return_value = mock_client
        
        manager = SkillsManager()
        
        # Call create_skill with use_ai=True
        skill_path = manager.create_skill(
            "ai-test-skill", 
            project_path=".", 
            use_ai=True
        )
        
        # Verify interactions
        mock_analyzer_cls.assert_called_once()
        mock_client.generate_content.assert_called()
        
        # Verify file content
        content = (skill_path / "SKILL.md").read_text(encoding='utf-8')
        self.assertIn("AI Generated", content)

    @patch('src.ai.ai_client.AIClientFactory.get_client')
    def test_create_skill_ai_failure_fallback(self, mock_get_client):
        """Test fallback when AI generation fails."""
        mock_client = MagicMock()
        mock_client.generate_content.return_value = "" # Empty response implies failure/fallback
        mock_get_client.return_value = mock_client
        
        manager = SkillsManager()
        
        skill_path = manager.create_skill(
            "failed-ai-skill", 
            project_path=".", 
            use_ai=True
        )
        
        # Should populate with default template
        content = (skill_path / "SKILL.md").read_text(encoding='utf-8')
        self.assertIn("# Skill: Failed Ai Skill", content)
        # Should NOT have AI content
        self.assertNotIn("AI Generated", content)
