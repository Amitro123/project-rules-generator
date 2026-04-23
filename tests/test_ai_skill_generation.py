"""Tests for AI-powered skill generation."""

import shutil
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from generator.skills_manager import SkillsManager


class TestAISkillGeneration(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_ai_skills")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)

        # Mock global directory for SkillPathManager to prevent pollution
        from generator.storage.skill_paths import SkillPathManager
        self.patcher1 = patch.object(SkillPathManager, "GLOBAL_DIR", self.test_dir)
        self.patcher2 = patch.object(SkillPathManager, "GLOBAL_LEARNED", self.test_dir / "learned")
        self.patcher3 = patch.object(SkillPathManager, "GLOBAL_BUILTIN", self.test_dir / "builtin")
        self.patcher1.start()
        self.patcher2.start()
        self.patcher3.start()

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_create_skill_with_ai(self):
        """Test create_skill invokes AIStrategy when use_ai=True.

        Patches AIStrategy.generate() directly instead of ProjectAnalyzer +
        LLMSkillGenerator because ProjectAnalyzer is run in a ThreadPoolExecutor
        and unittest.mock patches are NOT visible across thread boundaries.
        """
        ai_content = "# Skill: AI Test\n\n## Purpose\nAI Generated"

        with patch(
            "generator.strategies.ai_strategy.AIStrategy.generate",
            return_value=ai_content,
        ) as mock_ai_generate:
            manager = SkillsManager()
            skill_path = manager.create_skill("ai-test-skill", project_path=".", use_ai=True, force=True)

            # AIStrategy.generate should have been called once
            mock_ai_generate.assert_called_once()

            # The AI-produced content must be written to SKILL.md
            content = (skill_path / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("AI Generated", content)

    @patch(
        "generator.llm_skill_generator.create_ai_client",
        side_effect=ImportError("No provider"),
    )
    def test_create_skill_ai_missing_dependency(self, mock_create):
        """Test fallback when AI provider SDK is unavailable."""
        manager = SkillsManager()

        # Should gracefully fallback and produce a default template
        skill_path = manager.create_skill("missing-dep-skill", project_path=".", use_ai=True)

        content = (skill_path / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("# Skill: Missing Dep Skill", content)
        self.assertNotIn("AI Generated", content)

    def test_create_skill_ai_failure_fallback(self):
        """Test fallback when AI strategy raises an exception mid-generation."""
        with patch(
            "generator.strategies.ai_strategy.AIStrategy.generate",
            side_effect=RuntimeError("API Error"),
        ):
            manager = SkillsManager()
            skill_path = manager.create_skill("failed-ai-skill", project_path=".", use_ai=True)

            # Should fall through to README/Cowork/Stub and produce a default template
            content = (skill_path / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("# Skill: Failed Ai Skill", content)
