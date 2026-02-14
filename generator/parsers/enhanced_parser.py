"""Enhanced multi-source project parser for comprehensive context extraction."""

import logging
from pathlib import Path
from typing import Any, Dict

from generator.analyzers.structure_analyzer import StructureAnalyzer

from .dependency_parser import DependencyParser

logger = logging.getLogger(__name__)


class EnhancedProjectParser:
    """Extract context from README + dependencies + structure + tests."""

    def __init__(self, project_path: Path):
        self.path = Path(project_path)
        self.context: Dict[str, Any] = {}
        self._dep_parser = DependencyParser()
        self._structure_analyzer = StructureAnalyzer(self.path)

    def extract_full_context(self) -> Dict[str, Any]:
        """
        Main entry point - gather all context from multiple sources.

        Returns:
            {
                'readme': {...},
                'dependencies': {'python': [...], 'node': [...], 'system': [...]},
                'structure': {'type': ..., 'patterns': [...], ...},
                'test_patterns': {'framework': ..., ...},
                'metadata': {'tech_stack': [...], 'project_name': ..., ...},
            }
        """
        self.context = {
            "readme": self._parse_readme(),
            "dependencies": self._parse_dependencies(),
            "structure": self._analyze_structure(),
            "test_patterns": self._analyze_tests(),
            "metadata": {},
        }

        # Build metadata from all sources
        self.context["metadata"] = self._extract_metadata()

        return self.context

    def _parse_readme(self) -> Dict[str, Any]:
        """Parse README if it exists."""
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        for filename in readme_files:
            readme_path = self.path / filename
            if readme_path.exists():
                try:
                    from analyzer.readme_parser import parse_readme

                    return parse_readme(readme_path)
                except Exception as e:
                    logger.warning(f"README parsing failed: {e}")
                    # Return raw content as fallback
                    try:
                        content = readme_path.read_text(
                            encoding="utf-8", errors="replace"
                        )
                        return {
                            "name": self.path.name,
                            "tech_stack": [],
                            "features": [],
                            "description": "",
                            "raw_readme": content[:4000],
                            "readme_path": str(readme_path),
                        }
                    except Exception:
                        pass
        return {
            "name": self.path.name,
            "tech_stack": [],
            "features": [],
            "description": "No README found.",
            "raw_readme": "",
            "readme_path": None,
        }

    def _parse_dependencies(self) -> Dict[str, Any]:
        """
        Parse dependencies from all available sources.

        Returns:
            {
                'python': [{'name': 'fastapi', 'version': '0.100.0', ...}],
                'node': [{'name': 'react', 'version': '18.2.0', ...}],
                'system': ['ffmpeg', 'redis-server'],
                'python_dev': [...],
                'node_dev': [...],
            }
        """
        result: Dict[str, Any] = {
            "python": [],
            "node": [],
            "system": [],
            "python_dev": [],
            "node_dev": [],
        }

        # Python: requirements.txt
        req_file = self.path / "requirements.txt"
        if req_file.exists():
            result["python"] = self._dep_parser.parse_requirements_txt(req_file)

        # Python: additional requirements files
        for extra in [
            "requirements-dev.txt",
            "requirements-test.txt",
            "dev-requirements.txt",
        ]:
            extra_file = self.path / extra
            if extra_file.exists():
                result["python_dev"].extend(
                    self._dep_parser.parse_requirements_txt(extra_file)
                )

        # Python: pyproject.toml
        pyproject = self.path / "pyproject.toml"
        if pyproject.exists():
            parsed = self._dep_parser.parse_pyproject_toml(pyproject)
            # Merge with existing (pyproject deps take precedence for version info)
            existing_names = {d["name"] for d in result["python"]}
            for dep in parsed.get("dependencies", []):
                if dep["name"] not in existing_names:
                    result["python"].append(dep)
            result["python_dev"].extend(parsed.get("dev_dependencies", []))

        # Node: package.json
        pkg_json = self.path / "package.json"
        if pkg_json.exists():
            parsed = self._dep_parser.parse_package_json(pkg_json)
            result["node"] = parsed.get("dependencies", [])
            result["node_dev"] = parsed.get("dev_dependencies", [])

        # Fallback: extract from README pip install commands when no deps found
        if not result["python"]:
            readme_files = ["README.md", "README.rst", "README.txt", "README"]
            for filename in readme_files:
                readme_path = self.path / filename
                if readme_path.exists():
                    readme_deps = self._dep_parser.parse_readme_pip_install(readme_path)
                    if readme_deps:
                        result["python"] = readme_deps
                        logger.info(
                            f"Extracted {len(readme_deps)} deps from {filename} pip install commands"
                        )
                    break

        # System dependencies
        result["system"] = self._dep_parser.detect_system_dependencies(self.path)

        return result

    def _analyze_structure(self) -> Dict[str, Any]:
        """
        Detect architecture patterns from folders/files.

        Returns:
            {
                'type': 'python-cli',
                'patterns': ['python-cli', 'pytest-tests'],
                'entry_points': ['main.py'],
                'is_library': False,
                'confidence': 0.85,
            }
        """
        return self._structure_analyzer.detect_project_type()

    def _analyze_tests(self) -> Dict[str, Any]:
        """
        Find existing test patterns.

        Returns:
            {
                'framework': 'pytest',
                'test_files': 15,
                'patterns': ['unit', 'integration'],
                'has_fixtures': True,
                'has_conftest': True,
            }
        """
        return self._structure_analyzer.analyze_tests()

    def _extract_metadata(self) -> Dict[str, Any]:
        """
        Build unified metadata from all parsed sources.

        Returns:
            {
                'project_name': str,
                'tech_stack': ['python', 'fastapi', 'pytest', ...],
                'project_type': 'python-cli',
                'languages': ['python', 'javascript'],
                'frameworks': ['fastapi', 'react'],
                'has_tests': True,
                'has_docker': False,
            }
        """
        readme_data = self.context.get("readme", {})
        deps = self.context.get("dependencies", {})
        structure = self.context.get("structure", {})
        tests = self.context.get("test_patterns", {})

        # Merge tech stack from README + dependencies
        tech_stack = set(readme_data.get("tech_stack", []))

        # Add tech from Python dependencies
        python_dep_names = {d["name"] for d in deps.get("python", [])}
        dep_to_tech = {
            "fastapi": "fastapi",
            "flask": "flask",
            "django": "django",
            "click": "click",
            "typer": "typer",
            "argparse": "argparse",
            "pytest": "pytest",
            "torch": "pytorch",
            "pytorch": "pytorch",
            "tensorflow": "tensorflow",
            "sklearn": "sklearn",
            "scikit-learn": "sklearn",
            "transformers": "transformers",
            "redis": "redis",
            "celery": "celery",
            "sqlalchemy": "sqlalchemy",
            "pydantic": "pydantic",
            "google-generativeai": "gemini",
            "google-genai": "gemini",
            "openai": "openai",
            "anthropic": "anthropic",
            "langchain": "langchain",
            "langchain-core": "langchain",
            "websockets": "websocket",
            "httpx": "httpx",
            "aiohttp": "aiohttp",
            "uvicorn": "uvicorn",
            "gitpython": "gitpython",
            "mcp": "mcp",
            "groq": "groq",
            "perplexity": "perplexity",
        }
        for dep_name, tech_name in dep_to_tech.items():
            if dep_name in python_dep_names:
                tech_stack.add(tech_name)

        # Add tech from Node dependencies
        node_dep_names = {d["name"] for d in deps.get("node", [])}
        node_dep_to_tech = {
            "react": "react",
            "react-dom": "react",
            "vue": "vue",
            "next": "nextjs",
            "nuxt": "nuxt",
            "express": "express",
            "koa": "koa",
            "vite": "vite",
            "webpack": "webpack",
            "tailwindcss": "tailwindcss",
            "jest": "jest",
            "typescript": "typescript",
        }
        for dep_name, tech_name in node_dep_to_tech.items():
            if dep_name in node_dep_names:
                tech_stack.add(tech_name)

        # Detect languages
        languages = set()
        if deps.get("python") or (self.path / "requirements.txt").exists():
            languages.add("python")
        if deps.get("node") or (self.path / "package.json").exists():
            languages.add("javascript")
        if any(d["name"] == "typescript" for d in deps.get("node_dev", [])):
            languages.add("typescript")

        # Detect docker
        has_docker = (self.path / "Dockerfile").exists() or (
            self.path / "docker-compose.yml"
        ).exists()
        if has_docker:
            tech_stack.add("docker")

        # Add test framework
        test_framework = tests.get("framework")
        if test_framework:
            tech_stack.add(test_framework)

        # Determine project name
        project_name = readme_data.get("name", "") or self.path.name

        return {
            "project_name": project_name,
            "tech_stack": sorted(tech_stack),
            "project_type": structure.get("type", "unknown"),
            "languages": sorted(languages),
            "frameworks": sorted(
                tech_stack - languages - {"docker", "pytest", "jest", "unittest"}
            ),
            "has_tests": tests.get("test_files", 0) > 0,
            "has_docker": has_docker,
            "confidence": structure.get("confidence", 0.0),
        }
