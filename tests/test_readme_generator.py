"""Tests for Interactive README Generator."""

import shutil
import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Mock click if not available to handle missing dependency in test environment
if "click" not in sys.modules:
    sys.modules["click"] = MagicMock()

from generator.readme_generator import (
    generate_readme_interactively,
    generate_readme_with_llm,
    is_readme_minimal,
)


class TestReadmeGenerator(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_readme_gen")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_is_readme_minimal(self):
        """Test minimal detection logic."""
        # Missing file
        self.assertTrue(is_readme_minimal(self.test_dir / "MISSING.md"))

        # Empty file
        p = self.test_dir / "EMPTY.md"
        p.write_text("", encoding="utf-8")
        self.assertTrue(is_readme_minimal(p))

        # Short file
        p = self.test_dir / "SHORT.md"
        p.write_text("# Title\nDesc", encoding="utf-8")
        self.assertTrue(is_readme_minimal(p))

        # TODO placeholder
        p = self.test_dir / "TODO.md"
        p.write_text("# Title\n\nTODO: Write this\n\nLines\nLines", encoding="utf-8")
        self.assertTrue(is_readme_minimal(p))

        # Good file
        p = self.test_dir / "GOOD.md"
        content = "# Title\n\nDesc\n" + ("\nLine" * 10) + ("A" * 200)
        p.write_text(content, encoding="utf-8")
        self.assertFalse(is_readme_minimal(p))

    @patch("click.prompt")
    @patch("click.confirm")
    @patch("generator.readme_generator.generate_readme_template")
    @patch("generator.project_analyzer.ProjectAnalyzer")
    def test_generate_interactive(self, mock_analyzer_cls, mock_gen_template, mock_confirm, mock_prompt):
        """Test flow of interactive generation."""
        # Mocks
        mock_prompt.side_effect = ["Test Proj", "Desc", "Purpose", "Python", "Features"]
        mock_confirm.return_value = True
        mock_gen_template.return_value = "# Template README"
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {"tech_stack": {}, "structure": {}}
        mock_analyzer_cls.return_value = mock_analyzer

        # Run
        content = generate_readme_interactively(self.test_dir, use_ai=False)

        # Verify
        self.assertEqual(content, "# Template README")
        mock_gen_template.assert_called_once()

    @patch("generator.llm_skill_generator.LLMSkillGenerator")
    def test_generate_readme_with_llm_success(self, mock_llm_gen_cls):
        """Test successful AI README generation."""
        # Setup mock
        mock_llm_gen = MagicMock()
        mock_llm_gen.generate_content.return_value = "# AI Generated README"
        mock_llm_gen_cls.return_value = mock_llm_gen

        # Inputs
        user_input = {
            "name": "Test Project",
            "description": "A test project",
            "purpose": "Testing",
            "tech_stack": "Python",
            "features": "Feature 1, Feature 2",
        }
        context = {
            "tech_stack": {
                "backend": ["Python"],
                "frontend": [],
                "database": [],
                "languages": ["Python"],
            },
            "structure": {
                "has_backend": True,
                "has_frontend": False,
                "has_tests": True,
                "has_docker": False,
            },
        }

        # Run
        content = generate_readme_with_llm(user_input, context)

        # Verify
        self.assertEqual(content, "# AI Generated README")
        mock_llm_gen_cls.assert_called_once()

        # Verify prompt content
        call_args = mock_llm_gen.generate_content.call_args
        prompt = call_args[0][0]
        self.assertIn("Test Project", prompt)
        self.assertIn("A test project", prompt)
        self.assertIn("Python", prompt)
        self.assertIn("Feature 1", prompt)
        self.assertIn("# Generate Professional README.md", prompt)

    @patch("generator.readme_generator.generate_readme_template")
    @patch("generator.llm_skill_generator.LLMSkillGenerator")
    def test_generate_readme_with_llm_failure(self, mock_llm_gen_cls, mock_fallback):
        """Test fallback to template on AI failure."""
        # Setup mock to raise exception
        mock_llm_gen = MagicMock()
        mock_llm_gen.generate_content.side_effect = Exception("API Error")
        mock_llm_gen_cls.return_value = mock_llm_gen

        mock_fallback.return_value = "# Fallback Template"

        # Inputs - Provide complete user_input to avoid KeyError
        user_input = {
            "name": "Test Project",
            "description": "A test project",
            "purpose": "Testing",
            "tech_stack": "Python",
            "features": "Feature 1",
        }
        context = {"tech_stack": {}, "structure": {}}

        # Run
        content = generate_readme_with_llm(user_input, context)

        # Verify fallback
        self.assertEqual(content, "# Fallback Template")

        # Verify LLM was attempted
        mock_llm_gen_cls.assert_called_once()
        mock_llm_gen.generate_content.assert_called_once()

        # Verify fallback was called
        mock_fallback.assert_called_once_with(user_input, context)
