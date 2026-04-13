"""Analyze project structure and context for skill generation."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProjectAnalyzer:
    """Extract comprehensive project context for LLM analysis."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)

    def analyze(self) -> Dict:
        """Run full project analysis."""
        return {
            "structure": self._analyze_structure(),
            "readme": self._get_readme(),
            "tech_stack": self._detect_tech_stack(),
            "key_files": self._get_key_files(),
            "workflows": self._extract_workflows(),
        }

    def _analyze_structure(self) -> Dict:
        """Analyze directory structure."""
        structure: Dict[str, Any] = {
            "has_backend": (self.project_path / "backend").exists(),
            "has_frontend": (self.project_path / "frontend").exists(),
            "has_api": (self.project_path / "api").exists(),
            "has_tests": (self.project_path / "tests").exists(),
            "has_docker": (self.project_path / "Dockerfile").exists(),
            "has_docker_compose": (self.project_path / "docker-compose.yml").exists(),
        }

        # Get main directories (exclude hidden, node_modules, venv, etc.)
        exclude = {
            ".git",
            "node_modules",
            "venv",
            "__pycache__",
            ".pytest_cache",
            "dist",
            "build",
            ".idea",
            ".vscode",
            "skills",
        }
        main_dirs = [
            d.name
            for d in self.project_path.iterdir()
            if d.is_dir() and d.name not in exclude and not d.name.startswith(".")
        ]
        structure["main_directories"] = main_dirs[:10]  # Limit to 10

        return structure

    def _get_readme(self) -> Optional[str]:
        """Get README content (truncated)."""
        from generator.utils.readme_bridge import find_readme

        readme_path = find_readme(self.project_path)
        if readme_path:
            try:
                content = readme_path.read_text(encoding="utf-8", errors="replace")
                return content[:4000]
            except OSError:
                pass
        return None

    def _detect_tech_stack(self) -> Dict[str, List[str]]:
        """Detect technologies from project files.

        Data-driven: all detection rules live in generator/tech/profiles.py.
        To add a new technology, add a TechProfile entry there — no code changes needed here.
        """
        from generator.tech.lookups import (
            DIR_DETECTION_MAP,
            FILE_DETECTION_MAP,
            PKG_MAP,
            REGISTRY,
            TECH_CATEGORIES,
            TECH_DISPLAY_NAMES,
        )

        tech: Dict[str, List[str]] = {
            "backend": [],
            "frontend": [],
            "database": [],
            "infrastructure": [],
            "languages": [],
            "testing": [],
            "ml": [],
            "ai": [],
        }
        detected: set = set()

        def _add_tech(tech_name: str) -> None:
            """Bucket a detected tech name into the correct category list."""
            if tech_name in detected or tech_name not in REGISTRY:
                return
            detected.add(tech_name)
            category = TECH_CATEGORIES.get(tech_name, "backend")
            if category not in tech:
                tech[category] = []
            display = TECH_DISPLAY_NAMES.get(tech_name, tech_name.title())
            tech[category].append(display)

        # 1. Python dependency files — scan concatenated text for package names
        dep_content = ""
        python_dep_files = ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.cfg", "Pipfile"]
        for dep_file in python_dep_files:
            dep_path = self.project_path / dep_file
            if dep_path.exists():
                if "Python" not in tech["languages"]:
                    tech["languages"].append("Python")
                try:
                    dep_content += dep_path.read_text(encoding="utf-8", errors="replace").lower()
                except OSError:
                    pass
        if dep_content:
            for pkg, tech_name in PKG_MAP.items():
                if pkg.lower() in dep_content:
                    _add_tech(tech_name)

        # 2. package.json (JavaScript / TypeScript)
        pkg_file = self.project_path / "package.json"
        if pkg_file.exists():
            if "JavaScript/TypeScript" not in tech["languages"]:
                tech["languages"].append("JavaScript/TypeScript")
            try:
                pkg_content = pkg_file.read_text(encoding="utf-8", errors="replace").lower()
                for pkg, tech_name in PKG_MAP.items():
                    if pkg.lower() in pkg_content:
                        _add_tech(tech_name)
            except OSError:
                pass

        # 3. File / directory presence (infrastructure tools, config-file signals)
        for filename, tech_name in FILE_DETECTION_MAP.items():
            if (self.project_path / filename).exists():
                _add_tech(tech_name)
        for dirname, tech_name in DIR_DETECTION_MAP.items():
            if (self.project_path / dirname).is_dir():
                _add_tech(tech_name)

        # Deduplicate and sort for stable output
        for key in tech:
            tech[key] = sorted(set(tech[key]))

        return tech

    def _get_key_files(self) -> Dict[str, str]:
        """Extract snippets from important files."""
        files = {}

        # Dependencies
        for filename in ["requirements.txt", "package.json", "pyproject.toml"]:
            file_path = self.project_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    files[filename] = content[:1000]  # Limit
                except OSError:
                    pass

        # Config files
        for filename in [
            ".env.example",
            "config.py",
            "settings.py",
            "vite.config.ts",
            "vite.config.js",
        ]:
            file_path = self.project_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    files[filename] = content[:500]
                except OSError:
                    pass

        # API routes sample (Python).
        # Avoid unbounded ** globs — they walk the entire tree and block on large repos.
        # Instead, probe specific shallow locations that cover ~95% of real project layouts.
        api_candidates = [
            self.project_path / "api",
            self.project_path / "backend" / "api",
            self.project_path / "src" / "api",
            self.project_path / "app" / "api",
            self.project_path / "app" / "routes",
        ]
        api_file = None
        for api_dir in api_candidates:
            if api_dir.is_dir():
                api_file = next(api_dir.glob("*.py"), None)
                if api_file:
                    break
        if api_file:
            try:
                content = api_file.read_text(encoding="utf-8", errors="replace")
                files["api_sample"] = content[:800]
            except OSError:
                pass

        # Main entry point
        for filename in ["main.py", "app.py", "run.py", "index.js", "server.js"]:
            file_path = self.project_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    files[filename] = content[:800]
                    break  # Only one main file
                except OSError:
                    pass

        # Sample up to 3 source files from the main source directories
        # to give the LLM real project patterns (CLI commands, generators, etc.)
        source_dirs = ["generator", "cli", "src", "app", "backend", "lib"]
        sampled = 0
        for src_dir_name in source_dirs:
            src_dir = self.project_path / src_dir_name
            if not src_dir.is_dir() or sampled >= 3:
                break
            for py_file in sorted(src_dir.glob("*.py"))[:2]:
                if py_file.name.startswith("_"):
                    continue
                try:
                    content = py_file.read_text(encoding="utf-8", errors="replace")
                    if len(content) > 100:  # skip empty/tiny files
                        rel = str(py_file.relative_to(self.project_path))
                        files[rel] = content[:600]
                        sampled += 1
                        if sampled >= 3:
                            break
                except OSError:
                    pass

        return files

    def _extract_workflows(self) -> List[Dict]:
        """Extract common workflows from scripts and package.json."""
        workflows = []

        # From scripts/ directory
        scripts_dir = self.project_path / "scripts"
        if scripts_dir.exists():
            for script in scripts_dir.glob("*"):
                if script.suffix in [".sh", ".bash", ".ps1", ".bat"]:
                    workflows.append(
                        {
                            "type": "script",
                            "name": script.stem,
                            "path": str(script.relative_to(self.project_path)),
                        }
                    )

        # From package.json scripts
        pkg_file = self.project_path / "package.json"
        if pkg_file.exists():
            try:
                pkg_data = json.loads(pkg_file.read_text(encoding="utf-8", errors="replace"))
                if "scripts" in pkg_data:
                    for name, command in pkg_data["scripts"].items():
                        workflows.append({"type": "npm", "name": name, "command": command})
            except (OSError, ValueError):
                pass

        return workflows[:20]  # Limit to 20
