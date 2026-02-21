"""Tests for enhanced multi-source parser (Phase 1)."""

import json
from pathlib import Path

from generator.analyzers.structure_analyzer import StructureAnalyzer
from generator.parsers.dependency_parser import DependencyParser
from generator.parsers.enhanced_parser import EnhancedProjectParser


class TestDependencyParser:
    """Test dependency parsing for all ecosystems."""

    def test_parse_requirements_txt_basic(self, tmp_path):
        """Parse standard requirements.txt with pinned versions."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            "fastapi==0.100.0\n" "pydantic>=2.0.0\n" "uvicorn~=0.23.0\n" "# This is a comment\n" "\n" "click\n"
        )
        deps = DependencyParser.parse_requirements_txt(req_file)

        assert len(deps) == 4
        names = [d["name"] for d in deps]
        assert "fastapi" in names
        assert "pydantic" in names
        assert "uvicorn" in names
        assert "click" in names

        # Check version extraction
        fastapi = next(d for d in deps if d["name"] == "fastapi")
        assert fastapi["version"] == "0.100.0"
        assert fastapi["constraint"] == "=="

    def test_parse_requirements_txt_extras(self, tmp_path):
        """Parse requirements with extras."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("uvicorn[standard]>=0.23.0\n")
        deps = DependencyParser.parse_requirements_txt(req_file)

        assert len(deps) == 1
        assert deps[0]["name"] == "uvicorn"
        assert deps[0]["extras"] == "standard"

    def test_parse_requirements_txt_editable(self, tmp_path):
        """Parse editable installs."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("-e git+https://github.com/user/repo.git#egg=mypackage\n")
        deps = DependencyParser.parse_requirements_txt(req_file)

        assert len(deps) == 1
        assert deps[0]["name"] == "mypackage"
        assert deps[0]["constraint"] == "editable"

    def test_parse_requirements_txt_skips_options(self, tmp_path):
        """Skip -r includes and --flags."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("-r base-requirements.txt\n" "--index-url https://pypi.org/simple\n" "requests>=2.28.0\n")
        deps = DependencyParser.parse_requirements_txt(req_file)

        assert len(deps) == 1
        assert deps[0]["name"] == "requests"

    def test_parse_package_json(self, tmp_path):
        """Parse package.json for Node deps."""
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text(
            json.dumps(
                {
                    "name": "my-app",
                    "dependencies": {
                        "react": "^18.2.0",
                        "next": "~13.4.0",
                    },
                    "devDependencies": {
                        "typescript": "^5.0.0",
                        "jest": "~29.0.0",
                    },
                    "scripts": {
                        "dev": "next dev",
                        "build": "next build",
                    },
                }
            )
        )
        result = DependencyParser.parse_package_json(pkg_file)

        assert result["project_name"] == "my-app"
        assert len(result["dependencies"]) == 2
        assert len(result["dev_dependencies"]) == 2

        dep_names = [d["name"] for d in result["dependencies"]]
        assert "react" in dep_names
        assert "next" in dep_names

        assert result["scripts"]["dev"] == "next dev"

    def test_parse_pyproject_toml_fallback(self, tmp_path):
        """Test fallback parsing when tomli unavailable."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "my-project"
dependencies = [
    "fastapi>=0.100.0",
    "pydantic>=2.0",
]
""")
        result = DependencyParser._parse_pyproject_fallback(pyproject)

        assert result["project_name"] == "my-project"
        dep_names = [d["name"] for d in result["dependencies"]]
        assert "fastapi" in dep_names

    def test_detect_system_dependencies(self, tmp_path):
        """Detect system deps from source code."""
        py_file = tmp_path / "processor.py"
        py_file.write_text("import subprocess\n" 'subprocess.run(["ffmpeg", "-i", input_file])\n')
        system_deps = DependencyParser.detect_system_dependencies(tmp_path)
        assert "ffmpeg" in system_deps


class TestStructureAnalyzer:
    """Test project structure analysis."""

    def test_detect_python_cli(self, tmp_path):
        """Detect Python CLI project."""
        (tmp_path / "main.py").write_text("import click\n@click.command()\ndef main(): pass\n")
        (tmp_path / "cli.py").write_text("import argparse\n")

        analyzer = StructureAnalyzer(tmp_path)
        result = analyzer.detect_project_type()

        assert result["type"] == "python-cli"
        assert result["confidence"] > 0

    def test_detect_fastapi(self, tmp_path):
        """Detect FastAPI project."""
        (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "users.py").write_text("from fastapi import APIRouter\n")

        analyzer = StructureAnalyzer(tmp_path)
        result = analyzer.detect_project_type()

        assert result["type"] == "fastapi-api"

    def test_detect_test_framework_pytest(self, tmp_path):
        """Detect pytest as test framework."""
        (tmp_path / "conftest.py").write_text("import pytest\n")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").write_text("import pytest\ndef test_something(): pass\n")

        analyzer = StructureAnalyzer(tmp_path)
        framework = analyzer.detect_test_framework()
        assert framework == "pytest"

    def test_analyze_tests(self, tmp_path):
        """Full test analysis."""
        (tmp_path / "conftest.py").write_text("import pytest\n")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "conftest.py").write_text("import pytest\n")
        (tests_dir / "test_unit.py").write_text("def test_a(): pass\n")
        (tests_dir / "test_integration.py").write_text("def test_b(): pass\n")
        fixtures_dir = tests_dir / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "data.json").write_text("{}")

        analyzer = StructureAnalyzer(tmp_path)
        result = analyzer.analyze_tests()

        assert result["framework"] == "pytest"
        assert result["test_files"] >= 2
        assert "unit" in result["patterns"]
        assert "integration" in result["patterns"]
        assert result["has_conftest"] is True
        assert result["has_fixtures"] is True

    def test_detect_self_project(self):
        """Test with the project-rules-generator itself."""
        project_path = Path(__file__).parent.parent
        analyzer = StructureAnalyzer(project_path)
        result = analyzer.detect_project_type()

        assert result["type"] == "python-cli"
        assert result["test_framework"] == "pytest"
        assert "main.py" in result["entry_points"]


class TestEnhancedProjectParser:
    """Test the full enhanced parser."""

    def test_extract_full_context_python_project(self, tmp_path):
        """Test full context extraction for a Python project."""
        # Setup test project
        (tmp_path / "README.md").write_text("# My CLI Tool\n\nA Python CLI tool.\n\n## Tech\n- python\n- click\n")
        (tmp_path / "requirements.txt").write_text("click>=8.0\npydantic>=2.0\npytest>=7.0\n")
        (tmp_path / "main.py").write_text("import click\n@click.command()\ndef main(): pass\n")

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "conftest.py").write_text("import pytest\n")
        (tests_dir / "test_main.py").write_text("def test_main(): pass\n")

        parser = EnhancedProjectParser(tmp_path)
        context = parser.extract_full_context()

        # Check all sections are present
        assert "readme" in context
        assert "dependencies" in context
        assert "structure" in context
        assert "test_patterns" in context
        assert "metadata" in context

        # Check dependencies
        deps = context["dependencies"]
        python_names = [d["name"] for d in deps["python"]]
        assert "click" in python_names
        assert "pydantic" in python_names

        # Check metadata
        metadata = context["metadata"]
        assert "click" in metadata["tech_stack"]
        assert "pytest" in metadata["tech_stack"]
        assert "python" in metadata["languages"]

    def test_extract_full_context_node_project(self, tmp_path):
        """Test full context extraction for a Node.js project."""
        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "my-react-app",
                    "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
                    "devDependencies": {"typescript": "^5.0.0"},
                }
            )
        )
        src = tmp_path / "src"
        src.mkdir()
        (src / "App.tsx").write_text('import React from "react";\nexport default function App() {}\n')
        components = src / "components"
        components.mkdir()
        (components / "Button.tsx").write_text("export const Button = () => <button />\n")

        parser = EnhancedProjectParser(tmp_path)
        context = parser.extract_full_context()

        metadata = context["metadata"]
        assert "react" in metadata["tech_stack"]
        assert "javascript" in metadata["languages"]

    def test_no_react_in_python_project(self, tmp_path):
        """React skills should NOT appear in Python-only projects."""
        (tmp_path / "requirements.txt").write_text("fastapi>=0.100.0\npydantic>=2.0\n")
        (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")

        parser = EnhancedProjectParser(tmp_path)
        context = parser.extract_full_context()

        metadata = context["metadata"]
        assert "react" not in metadata["tech_stack"]
        assert "vue" not in metadata["tech_stack"]

    def test_extract_self_project(self):
        """Test with the project-rules-generator itself."""
        project_path = Path(__file__).parent.parent
        parser = EnhancedProjectParser(project_path)
        context = parser.extract_full_context()

        metadata = context["metadata"]
        assert "click" in metadata["tech_stack"]
        assert "pydantic" in metadata["tech_stack"]
        assert "python" in metadata["languages"]
        assert metadata["has_tests"] is True
