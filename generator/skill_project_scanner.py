"""Project context scanner — detects tech stack, signals, and structure."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from generator.utils.tech_detector import detect_tech_stack as _detect_tech_stack_util

logger = logging.getLogger(__name__)


class ProjectContextScanner:
    """Scans a project directory for tech stack, signals, and file structure.

    Extracted from CoworkSkillCreator to give it a single responsibility.
    Results are cached to avoid redundant filesystem calls.
    """

    PROJECT_SIGNALS = {
        "has_docker": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
        "has_tests": ["tests/", "test/", "pytest.ini", "conftest.py"],
        "has_ci": [".github/workflows/", ".gitlab-ci.yml", ".circleci/"],
        "has_docs": ["docs/", "README.md", "CONTRIBUTING.md"],
        "has_api": ["api/", "routes/", "endpoints/", "app.py", "main.py"],
        "has_frontend": ["frontend/", "src/components/", "public/"],
        "has_database": ["migrations/", "alembic/", "models.py", "schema.sql"],
        "monorepo": ["packages/", "apps/", "workspaces"],
    }

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self._detected_signals: Optional[Set[str]] = None
        self._tech_stack: Optional[Set[str]] = None

    def detect_skill_needs(self, project_path: Path) -> List[str]:
        """Detect needed skills based on tech stack and context.

        Uses SkillGenerator.TECH_SKILL_NAMES as the single source of truth for
        the tech→skill mapping (covers 40+ technologies).
        """
        # Lazy import to avoid circular dependency
        # (skill_generator → strategies → cowork_strategy → skill_creator)
        from generator.skill_generator import SkillGenerator

        readme_path = project_path / "README.md"
        readme_content = readme_path.read_text(encoding="utf-8", errors="ignore") if readme_path.exists() else ""

        tech_stack = self.detect_tech_stack(readme_content)
        skill_names = []

        if not tech_stack:
            skill_names.append(f"{project_path.name}-workflow")
        else:
            for tech in tech_stack:
                skill_name = SkillGenerator.TECH_SKILL_NAMES.get(tech.lower())
                if skill_name:
                    skill_names.append(skill_name)

            # If nothing matched, fall back to a generic project workflow
            if not skill_names:
                skill_names.append(f"{project_path.name}-workflow")

        return list(set(skill_names))

    def analyze_project_structure(self, skill_name: str, tech_stack: Optional[List[str]]) -> Dict:
        """Analyze ACTUAL project structure — no hallucinations.

        This is critical for project-specific skills.
        """
        analysis: Dict[str, Any] = {
            "actual_files": [],
            "patterns": [],
            "structure": {},
        }

        skill_lower = skill_name.lower()

        if "pytest" in skill_lower or "test" in skill_lower:
            test_dirs = []
            conftest_files = []
            test_files = []

            for test_dir in ["tests", "test"]:
                test_path = self.project_path / test_dir
                if test_path.exists():
                    test_dirs.append(str(test_path.relative_to(self.project_path)))

                    if test_path.is_dir():
                        conftest = test_path / "conftest.py"
                        if conftest.exists():
                            conftest_files.append(str(conftest.relative_to(self.project_path)))

                        for test_file in test_path.glob("test_*.py"):
                            test_files.append(str(test_file.relative_to(self.project_path)))

            pytest_ini = self.project_path / "pytest.ini"
            if pytest_ini.exists():
                analysis["actual_files"].append("pytest.ini")

            analysis["structure"] = {
                "test_dirs": test_dirs,
                "conftest_files": conftest_files,
                "test_files": test_files[:5],
            }

            if conftest_files:
                try:
                    conftest_content = (self.project_path / conftest_files[0]).read_text(
                        encoding="utf-8", errors="ignore"
                    )
                    if "pytest.fixture" in conftest_content:
                        analysis["patterns"].append("Uses pytest fixtures")
                    if "@pytest.mark" in conftest_content:
                        analysis["patterns"].append("Uses pytest markers")
                    if "pytest_configure" in conftest_content:
                        analysis["patterns"].append("Has pytest_configure hook")
                except OSError:
                    pass

        elif "fastapi" in skill_lower or "api" in skill_lower:
            api_files = []
            for api_dir in ["api", "app", "src"]:
                api_path = self.project_path / api_dir
                if api_path.exists() and api_path.is_dir():
                    for py_file in api_path.rglob("*.py"):
                        api_files.append(str(py_file.relative_to(self.project_path)))

            analysis["structure"]["api_files"] = api_files[:10]

        return analysis

    def detect_tech_stack(self, readme_content: str) -> List[str]:
        """Auto-detect tech stack from README AND actual project files.

        Delegates to generator.utils.tech_detector.detect_tech_stack().
        Result is cached for the lifetime of this instance.
        """
        if self._tech_stack:
            return list(self._tech_stack)
        detected = set(_detect_tech_stack_util(self.project_path, readme_content))
        self._tech_stack = detected
        return list(detected)

    def detect_project_signals(self) -> Set[str]:
        """Detect project structure signals (has_docker, has_tests, etc.)."""
        if self._detected_signals:
            return self._detected_signals

        signals = set()
        for signal_name, indicators in self.PROJECT_SIGNALS.items():
            for indicator in indicators:
                if (self.project_path / indicator).exists():
                    signals.add(signal_name)
                    break

        self._detected_signals = signals
        return signals

    def is_readme_sufficient(self, readme_content: str) -> bool:
        """Return True if README has enough content for meaningful skill generation."""
        from generator.utils.readme_bridge import is_readme_sufficient

        return is_readme_sufficient(readme_content)

    def scan_project_tree(self, max_depth: int = 3, max_items: int = 60) -> str:
        """Walk the project directory and produce a structured tree for LLM context."""
        from generator.utils.readme_bridge import build_project_tree

        return build_project_tree(self.project_path, max_depth=max_depth, max_items=max_items)
