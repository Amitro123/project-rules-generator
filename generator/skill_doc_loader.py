"""
Skill Doc Loader
================

Discovers and loads supplementary project documentation to ground
LLM-based skill generation in real project content.
Extracted from CoworkSkillCreator to keep each module focused.
"""

from pathlib import Path
from typing import Dict, List


class SkillDocLoader:
    """Discovers and loads project docs for LLM context."""

    # Max total chars for supplementary docs (to stay within token budget)
    SUPPLEMENTARY_BUDGET = 1500

    # Filenames that are noise — never useful as skill context
    _DOCS_SKIP = {
        "readme.md",
        "changelog.md",
        "changelog",
        "license.md",
        "license",
        "contributing.md",
        "contributors.md",
        "authors.md",
        "history.md",
        "news.md",
        "releases.md",
        "security.md",
        "code_of_conduct.md",
    }

    # Filename signals that indicate high-value context docs (any project)
    _DOCS_HIGH_VALUE = {
        "spec",
        "architecture",
        "design",
        "constitution",
        "features",
        "preferences",
        "coding",
        "style",
        "guide",
        "workflow",
        "overview",
        "plan",
        "roadmap",
        "rules",
        "standards",
        "conventions",
        "adr",
    }

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path

    def _score_doc(self, path: Path, content: str) -> int:
        """Score a supplementary doc by relevance. Higher = more useful."""
        stem = path.stem.lower()
        score = 0
        if any(kw in stem for kw in self._DOCS_HIGH_VALUE):
            score += 2
        if path.parent.name.lower() in ("docs", "doc", "documentation"):
            score += 1
        if len(content) < 200:
            score -= 1
        return score

    def discover_supplementary_docs(self) -> List[Path]:
        """Dynamically discover relevant .md docs in the project.

        Scans root + docs/ subdirectory, skips noise files (CHANGELOG, LICENSE …),
        and returns paths sorted by relevance score descending.
        Works for any project — no hardcoded filenames.
        """
        candidates: List[Path] = []

        search_dirs = [self.project_path] + [
            d for d in self.project_path.iterdir() if d.is_dir() and d.name.lower() in ("docs", "doc", "documentation")
        ]

        for directory in search_dirs:
            for md_file in directory.glob("*.md"):
                if md_file.name.lower() in self._DOCS_SKIP:
                    continue
                if md_file.name.lower() == "readme.md":
                    continue
                candidates.append(md_file)

        candidates.sort(key=lambda p: (-self._score_doc(p, ""), p.name))
        return candidates

    def load_key_files(self, skill_name: str) -> Dict[str, str]:
        """Load actual key project files to ground the LLM in real project content.

        Always includes: entry points + config + project tree +
        top supplementary docs discovered dynamically (no hardcoded names).
        Supplementary docs are capped at SUPPLEMENTARY_BUDGET total chars.
        """
        from generator.utils.readme_bridge import build_project_tree

        key_files: Dict[str, str] = {}
        skill_lower = skill_name.lower()

        candidates = ["main.py", "app.py", "pyproject.toml", "requirements.txt"]

        if any(w in skill_lower for w in ["backend", "api", "developer"]):
            candidates += ["project_rules_generator.py", "generator/__init__.py"]
        if "test" in skill_lower:
            candidates += ["pytest.ini", "tests/conftest.py"]
        if "cli" in skill_lower or "command" in skill_lower:
            candidates += ["main.py"]

        for candidate in candidates:
            path = self.project_path / candidate
            if path.exists() and path.is_file():
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    key_files[candidate] = content[:600]
                except OSError:
                    pass

        tree = build_project_tree(self.project_path, max_depth=3, max_items=60)
        key_files["project_tree"] = tree[:800]

        remaining_budget = self.SUPPLEMENTARY_BUDGET
        for doc_path in self.discover_supplementary_docs():
            if remaining_budget <= 0:
                break
            try:
                content = doc_path.read_text(encoding="utf-8", errors="ignore").strip()
                if not content:
                    continue
                if self._score_doc(doc_path, content) < 0:
                    continue
                rel = str(doc_path.relative_to(self.project_path))
                chunk = content[:remaining_budget]
                key_files[rel] = chunk
                remaining_budget -= len(chunk)
            except OSError:
                pass

        return key_files
