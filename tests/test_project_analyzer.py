"""Tests for Project Analyzer."""

import unittest
from pathlib import Path
import shutil
import json
import tempfile

from generator.project_analyzer import ProjectAnalyzer

class TestProjectAnalyzer(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_project_analyzer")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_analyze_structure(self):
        """Test structure detection."""
        # Create structure
        (self.test_dir / "backend").mkdir()
        (self.test_dir / "frontend").mkdir()
        (self.test_dir / "api").mkdir()
        (self.test_dir / "tests").mkdir()
        (self.test_dir / "Dockerfile").touch()
        (self.test_dir / "docker-compose.yml").touch()

        analyzer = ProjectAnalyzer(self.test_dir)
        analysis = analyzer.analyze()
        structure = analysis['structure']

        self.assertTrue(structure['has_backend'])
        self.assertTrue(structure['has_frontend'])
        self.assertTrue(structure['has_api'])
        self.assertTrue(structure['has_tests'])
        self.assertTrue(structure['has_docker'])
        self.assertTrue(structure['has_docker_compose'])
        self.assertIn('backend', structure['main_directories'])

    def test_detect_tech_stack_python(self):
        """Test Python tech stack detection."""
        req_content = "fastapi\nredis\nopenai-whisper\n"
        (self.test_dir / "requirements.txt").write_text(req_content, encoding='utf-8')

        analyzer = ProjectAnalyzer(self.test_dir)
        analysis = analyzer.analyze()
        tech = analysis['tech_stack']

        self.assertIn('Python', tech['languages'])
        self.assertIn('FastAPI', tech['backend'])
        self.assertIn('Redis', tech['database'])
        self.assertIn('Whisper', tech['backend'])

    def test_detect_tech_stack_node(self):
        """Test Node.js tech stack detection."""
        pkg_content = json.dumps({
            "dependencies": {
                "react": "^18.0.0",
                "next": "^13.0.0",
                "tailwindcss": "^3.0.0"
            }
        })
        (self.test_dir / "package.json").write_text(pkg_content, encoding='utf-8')

        analyzer = ProjectAnalyzer(self.test_dir)
        analysis = analyzer.analyze()
        tech = analysis['tech_stack']

        self.assertIn('JavaScript/TypeScript', tech['languages'])
        self.assertIn('React', tech['frontend'])
        self.assertIn('Next.js', tech['frontend'])
        self.assertIn('TailwindCSS', tech['frontend'])

    def test_extract_workflows(self):
        """Test workflow extraction."""
        # Scripts
        scripts_dir = self.test_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "deploy.sh").touch()

        # package.json scripts
        pkg_content = json.dumps({
            "scripts": {
                "start": "node index.js",
                "test": "jest"
            }
        })
        (self.test_dir / "package.json").write_text(pkg_content, encoding='utf-8')

        analyzer = ProjectAnalyzer(self.test_dir)
        analysis = analyzer.analyze()
        workflows = analysis['workflows']

        workflow_names = [w['name'] for w in workflows]
        self.assertIn('deploy', workflow_names)
        self.assertIn('start', workflow_names)
        self.assertIn('test', workflow_names)

    def test_get_key_files(self):
        """Test key files extraction."""
        (self.test_dir / "main.py").write_text("print('hello')", encoding='utf-8')
        (self.test_dir / "requirements.txt").write_text("requests", encoding='utf-8')

        analyzer = ProjectAnalyzer(self.test_dir)
        analysis = analyzer.analyze()
        files = analysis['key_files']

        self.assertIn('main.py', files)
        self.assertIn('requirements.txt', files)
        self.assertEqual(files['main.py'], "print('hello')")
