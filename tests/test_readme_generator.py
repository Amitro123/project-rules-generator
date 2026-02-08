"""Tests for Interactive README Generator."""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import shutil

from generator.readme_generator import is_readme_minimal, generate_readme_interactively

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
        p.write_text("", encoding='utf-8')
        self.assertTrue(is_readme_minimal(p))
        
        # Short file
        p = self.test_dir / "SHORT.md"
        p.write_text("# Title\nDesc", encoding='utf-8')
        self.assertTrue(is_readme_minimal(p))
        
        # TODO placeholder
        p = self.test_dir / "TODO.md"
        p.write_text("# Title\n\nTODO: Write this\n\nLines\nLines", encoding='utf-8')
        self.assertTrue(is_readme_minimal(p))
        
        # Good file
        p = self.test_dir / "GOOD.md"
        content = "# Title\n\nDesc\n" + ("\nLine" * 10) + ("A" * 200)
        p.write_text(content, encoding='utf-8')
        self.assertFalse(is_readme_minimal(p))
    
    @patch('click.prompt')
    @patch('click.confirm')
    @patch('generator.readme_generator.generate_readme_template')
    @patch('generator.project_analyzer.ProjectAnalyzer')
    def test_generate_interactive(self, mock_analyzer_cls, mock_gen_template, mock_confirm, mock_prompt):
        """Test flow of interactive generation."""
        # Mocks
        mock_prompt.side_effect = ["Test Proj", "Desc", "Purpose", "Python", "Features"]
        mock_confirm.return_value = True
        mock_gen_template.return_value = "# Template README"
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {'tech_stack': {}, 'structure': {}}
        mock_analyzer_cls.return_value = mock_analyzer
        
        # Run
        content = generate_readme_interactively(self.test_dir, use_ai=False)
        
        # Verify
        self.assertEqual(content, "# Template README")
        mock_gen_template.assert_called_once()
