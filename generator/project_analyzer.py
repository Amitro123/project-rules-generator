"""Analyze project structure and context for skill generation."""

import json
from pathlib import Path
from typing import Dict, List, Optional


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
        structure = {
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
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        for filename in readme_files:
            readme_path = self.project_path / filename
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding="utf-8", errors="replace")
                    # Limit to 4000 chars to avoid token overflow
                    return content[:4000]
                except Exception:
                    pass
        return None

    def _detect_tech_stack(self) -> Dict[str, List[str]]:
        """Detect technologies from project files."""
        tech = {
            "backend": [],
            "frontend": [],
            "database": [],
            "infrastructure": [],
            "languages": [],
        }

        # From requirements.txt (Python)
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            tech["languages"].append("Python")
            try:
                req_content = req_file.read_text(
                    encoding="utf-8", errors="replace"
                ).lower()
                if "fastapi" in req_content:
                    tech["backend"].append("FastAPI")
                if "flask" in req_content:
                    tech["backend"].append("Flask")
                if "django" in req_content:
                    tech["backend"].append("Django")
                if "redis" in req_content:
                    tech["database"].append("Redis")
                if "postgresql" in req_content or "psycopg" in req_content:
                    tech["database"].append("PostgreSQL")
                if "mysql" in req_content or "pymysql" in req_content:
                    tech["database"].append("MySQL")
                if "whisper" in req_content or "openai-whisper" in req_content:
                    tech["backend"].append("Whisper")
                if "gemini" in req_content or "google-generativeai" in req_content:
                    tech["backend"].append("Gemini")
            except Exception:
                pass

        # From package.json (JavaScript/TypeScript)
        pkg_file = self.project_path / "package.json"
        if pkg_file.exists():
            tech["languages"].append("JavaScript/TypeScript")
            try:
                pkg_content = pkg_file.read_text(
                    encoding="utf-8", errors="replace"
                ).lower()
                if "react" in pkg_content:
                    tech["frontend"].append("React")
                if "vue" in pkg_content:
                    tech["frontend"].append("Vue")
                if "next" in pkg_content:
                    tech["frontend"].append("Next.js")
                if "vite" in pkg_content:
                    tech["frontend"].append("Vite")
                if "tailwind" in pkg_content:
                    tech["frontend"].append("TailwindCSS")
                if "node" in pkg_content:
                    tech["backend"].append("Node.js")
            except Exception:
                pass

        # Infrastructure
        if (self.project_path / "Dockerfile").exists():
            tech["infrastructure"].append("Docker")
        if (self.project_path / "docker-compose.yml").exists():
            tech["infrastructure"].append("Docker Compose")
        if (self.project_path / ".github" / "workflows").exists():
            tech["infrastructure"].append("GitHub Actions")

        # Deduplicate
        for key in tech:
            tech[key] = list(set(tech[key]))

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
                except Exception:
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
                except Exception:
                    pass

        # API routes sample (Python)
        api_files = list(self.project_path.glob("**/api/**/*.py"))
        if api_files:
            try:
                content = api_files[0].read_text(encoding="utf-8", errors="replace")
                files["api_sample"] = content[:800]
            except Exception:
                pass

        # Main entry point
        for filename in ["main.py", "app.py", "run.py", "index.js", "server.js"]:
            file_path = self.project_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    files[filename] = content[:800]
                    break  # Only one main file
                except Exception:
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
                pkg_data = json.loads(
                    pkg_file.read_text(encoding="utf-8", errors="replace")
                )
                if "scripts" in pkg_data:
                    for name, command in pkg_data["scripts"].items():
                        workflows.append(
                            {"type": "npm", "name": name, "command": command}
                        )
            except Exception:
                pass

        return workflows[:20]  # Limit to 20
