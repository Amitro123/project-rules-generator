"""Tests for Skills + Rules Integration."""

import shutil
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from generator.skills_manager import SkillsManager


class TestSkillsIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_integration_skills")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)

        # Create dummy skills
        (self.test_dir / "builtin/dummy-skill").mkdir(parents=True)
        (self.test_dir / "builtin/dummy-skill/SKILL.md").write_text(
            "# Skill: Dummy\n\n## Auto-Trigger\n- User mentions: dummy\n- Project phase: testing\n\n## Process\n...",
            encoding="utf-8",
        )

        # Mock paths
        self.original_home = Path.home
        Path.home = MagicMock(return_value=self.test_dir)

    def tearDown(self):
        Path.home = self.original_home
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_extract_auto_triggers(self):
        """Test extraction of auto-triggers from skills."""
        manager = SkillsManager(project_path=self.test_dir)
        # We need to make sure manager.builtin_path points to our test dir
        manager.discovery.global_builtin = self.test_dir / "builtin"
        manager.discovery.global_learned = self.test_dir / "learned"
        manager.discovery.package_builtin = self.test_dir / "pkg_builtin"

        triggers = manager.extract_all_triggers()

        self.assertEqual(len(triggers), 1)
        self.assertIn("dummy-skill", triggers)
        self.assertIn("user mentions: dummy", triggers["dummy-skill"])
        self.assertIn("project phase: testing", triggers["dummy-skill"])

    def test_get_all_skills_content(self):
        """Test retrieval of all skills content."""
        manager = SkillsManager(project_path=self.test_dir)
        manager.discovery.global_builtin = self.test_dir / "builtin"

        content = manager.get_all_skills_content()

        self.assertIn("dummy-skill", content["builtin"])
        self.assertIn("# Skill: Dummy", content["builtin"]["dummy-skill"]["content"])


if __name__ == "__main__":
    unittest.main()
