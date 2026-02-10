"""Tests for AI-powered skill generation."""

import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import shutil

from generator.skills_manager import SkillsManager


class TestAISkillGeneration(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_ai_skills")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)

        # Mock home directory for SkillsManager
        self.original_home = Path.home
        Path.home = MagicMock(return_value=self.test_dir)

    def tearDown(self):
        Path.home = self.original_home
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch('generator.project_analyzer.ProjectAnalyzer')
    @patch('generator.llm_skill_generator.LLMSkillGenerator')
    def test_create_skill_with_ai(self, mock_llm_cls, mock_analyzer_cls):
        """Test create_skill calls AI components when use_ai=True."""
        # Setup mocks
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {'context': 'dummy'}
        mock_analyzer_cls.return_value = mock_analyzer

        mock_generator = MagicMock()
        mock_generator.generate_skill.return_value = "# Skill: AI Test\n\n## Purpose\nAI Generated"
        mock_llm_cls.return_value = mock_generator

        manager = SkillsManager()

        # Call create_skill with use_ai=True
        skill_path = manager.create_skill(
            "ai-test-skill",
            project_path=".",
            use_ai=True
        )

        # Verify interactions
        mock_analyzer_cls.assert_called_once()
        mock_generator.generate_skill.assert_called_once_with("ai-test-skill", {'context': 'dummy'})

        # Verify file content
        content = (skill_path / "SKILL.md").read_text(encoding='utf-8')
        self.assertIn("AI Generated", content)

    @patch('generator.llm_skill_generator.create_ai_client', side_effect=ImportError("No provider"))
    def test_create_skill_ai_missing_dependency(self, mock_create):
        """Test fallback when AI provider is unavailable."""
        manager = SkillsManager()

        # Should gracefully fallback and produce a default template
        skill_path = manager.create_skill(
            "missing-dep-skill",
            project_path=".",
            use_ai=True
        )

        content = (skill_path / "SKILL.md").read_text(encoding='utf-8')
        self.assertIn("# Skill: Missing Dep Skill", content)
        self.assertNotIn("AI Generated", content)

    @patch('generator.project_analyzer.ProjectAnalyzer')
    @patch('generator.llm_skill_generator.LLMSkillGenerator')
    def test_create_skill_ai_failure_fallback(self, mock_llm_cls, mock_analyzer_cls):
        """Test fallback when AI generation raises exception."""
        mock_analyzer = MagicMock()
        mock_analyzer_cls.return_value = mock_analyzer

        # Simulate LLM failure
        mock_generator = MagicMock()
        mock_generator.generate_skill.side_effect = RuntimeError("API Error")
        mock_llm_cls.return_value = mock_generator

        manager = SkillsManager()

        skill_path = manager.create_skill(
            "failed-ai-skill",
            project_path=".",
            use_ai=True
        )

        # Should populate with default template
        content = (skill_path / "SKILL.md").read_text(encoding='utf-8')
        self.assertIn("# Skill: Failed Ai Skill", content)
