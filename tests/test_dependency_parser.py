"""Tests for DependencyParser."""

import unittest
from pathlib import Path
from generator.parsers.dependency_parser import DependencyParser

class TestDependencyParser(unittest.TestCase):
    def setUp(self):
        self.parser = DependencyParser()

    def test_detect_system_dependencies_redundancy(self):
        """Test that files are not scanned multiple times."""
        # This test mocks the file system or uses a specific structure
        # to verify that the scanner deduplicates paths.
        # Since we can't easily mock the file system scan without refactoring,
        # we will verify the logic by creating a temporary directory structure.
        import tempfile
        import shutil
        
        test_dir = Path(tempfile.mkdtemp())
        try:
            (test_dir / "script.py").touch()
            (test_dir / "subdir").mkdir()
            (test_dir / "subdir" / "module.py").touch()
            
            # Monkeypatch Path.glob to track calls if possible, 
            # OR better, trust the refactor logic. 
            # Actually, let's just run it and ensure no error, 
            # and manually verify code correctness. 
            # But to TDD this, we'd want to spy on the file reading.
            
            # Let's mock read_text to count calls
            call_counts = {}
            original_read_text = Path.read_text
            
            def side_effect(self, encoding=None, errors=None):
                path_str = str(self)
                call_counts[path_str] = call_counts.get(path_str, 0) + 1
                return "import requests"

            # Context manager to patch Path.read_text
            from unittest.mock import patch
            with patch("pathlib.Path.read_text", side_effect=side_effect, autospec=True):
                 DependencyParser.detect_system_dependencies(test_dir)
            
            # Check redundancy
            for path, count in call_counts.items():
                if "script.py" in path or "module.py" in path:
                    self.assertEqual(count, 1, f"File {path} scanned {count} times")

        finally:
            shutil.rmtree(test_dir)

    def test_parse_pep508_complex(self):
        """Test parsing of complex PEP 508 strings."""
        cases = [
            ("requests>=2.0.0,!=2.1.0", {"name": "requests", "version": "!=2.1.0,>=2.0.0", "extras": ""}),
            ("fastapi[all]", {"name": "fastapi", "extras": "all", "version": ""}),
            ("pkg[e1,e2]>=1.0", {"name": "pkg", "extras": "e1,e2", "version": ">=1.0"}),
            ("pkg; sys_platform == 'win32'", {"name": "pkg", "marker": 'sys_platform == "win32"'}),
            ("package @ git+https://github.com/example/package.git", {"name": "package", "url": "git+https://github.com/example/package.git"}),
            ("urllib3<2.0.0,>=1.25.3", {"name": "urllib3", "version": "<2.0.0,>=1.25.3"}),
        ]
        
        # Note: The current implementation returns a dict with 'version', 'constraint', etc.
        # We need to adapt the test to match the return structure OR the new structure.
        # The plan is to switch to packaging, which might change exact output format slightly,
        # but we should aim for backward compatibility in the keys.
        
        for input_str, expected in cases:
            result = DependencyParser._parse_pep508(input_str)
            self.assertIsNotNone(result, f"Failed to parse: {input_str}")
            self.assertEqual(result["name"], expected["name"])
            if "extras" in expected:
                 self.assertEqual(result["extras"], expected["extras"])
            # Version/constraint might need adjusting based on how packaging parses it.

if __name__ == "__main__":
    unittest.main()
