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
        from generator.utils.readme_bridge import find_readme

        readme_path = find_readme(self.path)
        if readme_path:
            try:
                from generator.analyzers.readme_parser import parse_readme

                return parse_readme(readme_path)
            except (OSError, ValueError) as e:
                logger.warning(f"README parsing failed: {e}")
                # Return raw content as fallback
                try:
                    content = readme_path.read_text(encoding="utf-8", errors="replace")
                    return {
                        "name": self.path.name,
                        "tech_stack": [],
                        "features": [],
                        "description": "",
                        "raw_readme": content[:4000],
                        "readme_path": str(readme_path),
                    }
                except OSError:
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
                result["python_dev"].extend(self._dep_parser.parse_requirements_txt(extra_file))

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

        # Spec file: merge dependencies declared in spec.yml / spec.yaml
        from generator.utils.readme_bridge import parse_spec_file

        spec_data = parse_spec_file(self.path)
        if spec_data["dependencies"]:
            existing_names = {d["name"].lower() for d in result["python"]}
            for dep_name in spec_data["dependencies"]:
                if dep_name not in existing_names:
                    result["python"].append({"name": dep_name, "version": "", "extras": []})
                    existing_names.add(dep_name)

        # Fallback: extract from README pip install commands when no deps found
        if not result["python"]:
            from generator.utils.readme_bridge import find_readme

            readme_path = find_readme(self.path)
            if readme_path:
                readme_deps = self._dep_parser.parse_readme_pip_install(readme_path)
                if readme_deps:
                    result["python"] = readme_deps
                    logger.info(f"Extracted {len(readme_deps)} deps from {readme_path.name} pip install commands")

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
            "langchain-openai": "langchain",
            "langchain-community": "langchain",
            "langgraph": "langgraph",
            "chromadb": "chromadb",
            "qdrant-client": "qdrant",
            "websockets": "websocket",
            "httpx": "httpx",
            "aiohttp": "aiohttp",
            "uvicorn": "uvicorn",
            "gitpython": "gitpython",
            "mcp": "mcp",
            "groq": "groq",
            "perplexity": "perplexity",
            "ezdxf": "dxf",
            "reportlab": "reportlab",
            "supabase": "supabase",
            "konva": "konva",
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
            "konva": "konva",
            "react-konva": "konva",
            "three": "threejs",
            "babylonjs": "babylon",
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

        # Supplement with README-based detection for specialized/CDN-loaded techs
        # (konva, canvas, DXF viewer, WebGL) that rarely appear in dep files
        raw_readme = readme_data.get("raw_readme", "")
        if not raw_readme:
            # Try to get from readme_path field
            readme_path_str = readme_data.get("readme_path")
            if readme_path_str:
                try:
                    raw_readme = Path(readme_path_str).read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
        if raw_readme:
            # R3 fix: use detect_tech_stack (the full infrastructure-aware
            # detector) instead of the narrow detect_from_readme + hardcoded
            # allow-list. detect_tech_stack already includes CDN/canvas techs
            # AND promotes infrastructure-category techs (docker, telegram,
            # linux, yaml, vite) from README when no dep files are present,
            # which is exactly what ops-heavy / agent-skills projects need.
            from generator.utils.tech_detector import detect_tech_stack as _detect_tech_full

            for tech in _detect_tech_full(self.path, readme_content=raw_readme):
                tech_stack.add(tech)

        # Detect docker
        has_docker = (self.path / "Dockerfile").exists() or (self.path / "docker-compose.yml").exists()
        if has_docker:
            tech_stack.add("docker")

        # Enrich from spec.yml / spec.yaml when present
        from generator.utils.readme_bridge import parse_spec_file as _parse_spec

        _spec = _parse_spec(self.path)
        for _tech in _spec.get("extra_tech", []):
            tech_stack.add(_tech)
        # spec.yml overrides the test framework when structure_analyzer guessed wrong
        _spec_framework = _spec.get("test_framework")
        if _spec_framework:
            tests = dict(tests)  # don't mutate the original
            tests["framework"] = _spec_framework

        # Add test framework
        test_framework = tests.get("framework")
        if test_framework:
            tech_stack.add(test_framework)

        # Determine project name
        project_name = readme_data.get("name", "") or self.path.name

        # Reconcile the two detectors via the declarative precedence table.
        # See ``generator/project_profile.py`` for the rules and
        # ``Plans/prg-systemic-bug-refactor.md`` (Phase 2) for the rationale.
        #
        # The function reconcile_project_type() is generic — it iterates rule
        # records and applies whichever matches first. Per-type policy lives
        # in DEFAULT_PROJECT_TYPE_PRECEDENCE; this call site only translates
        # detector outputs into the function's parameter shape.
        #
        # Default-asymmetry preserved from the original cascade:
        #   * missing structure_confidence  → assume confident (1.0)
        #     (don't override SA unless it explicitly says it's uncertain)
        #   * missing newer_confidence      → assume uncertain (0.0)
        #     (don't trust the newer detector unless it explicitly says so)
        structure_type = structure.get("type", "unknown")
        project_type = structure_type
        try:
            from generator.analyzers.project_type_detector import TYPE_LABEL_MAP as _PT_LABEL_MAP
            from generator.analyzers.project_type_detector import detect_project_type as _detect_pt
            from generator.project_profile import reconcile_project_type

            _readme_content = readme_data.get("raw_readme", "")
            _pt_meta = {"name": self.path.name, "tech_stack": list(tech_stack), "raw_readme": _readme_content}
            _newer = _detect_pt(_pt_meta, str(self.path))
            _newer_raw = _newer.get("primary_type", "")
            # Translate the detector's snake_case score key to the hyphenated
            # vocabulary StructureAnalyzer uses so the rule table works uniformly.
            _newer_type = _PT_LABEL_MAP.get(_newer_raw, _newer_raw)
            _newer_confidence = float(_newer.get("confidence", 0.0) or 0.0)
            _structure_confidence = float(structure.get("confidence", 1.0))

            _result = reconcile_project_type(
                structure_type=structure_type,
                structure_confidence=_structure_confidence,
                newer_type=_newer_type,
                newer_confidence=_newer_confidence,
            )
            project_type = _result.project_type
        except Exception:  # noqa: BLE001 — type override is best-effort; old detector result is still valid
            pass

        # Remove generic tokens that are not real package/framework identifiers.
        # These appear when the README parser does keyword extraction from prose
        # (e.g. "GPT" in a description → "gpt") but they pollute skill matching
        # with false-positive tech signals that have no corresponding package.
        # "jest" is also removed here when it leaked from Python test-file
        # pattern matching (guarded separately in structure_analyzer, but belt+suspenders).
        _noise_tokens = {"gpt", "jest"} - {test_framework} if test_framework != "jest" else {"gpt"}
        tech_stack -= _noise_tokens

        # Reflex uses React + Next.js internally but developers write pure Python.
        # Strip the JS ecosystem tokens that leak from README prerequisites
        # ("Node.js 16+") or from the generated .web/ directory being scanned.
        if "reflex" in tech_stack:
            tech_stack -= {"react", "node", "javascript", "typescript", "nextjs"}

        return {
            "project_name": project_name,
            "tech_stack": sorted(tech_stack),
            "project_type": project_type,
            "languages": sorted(languages),
            "frameworks": sorted(tech_stack - languages - {"docker", "pytest", "jest", "unittest"}),
            "has_tests": tests.get("test_files", 0) > 0,
            "has_docker": has_docker,
            "confidence": structure.get("confidence", 0.0),
        }
