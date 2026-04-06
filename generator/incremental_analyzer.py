"""Incremental analysis - only regenerate when project changes are detected."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# File patterns to include when computing the project hash
_HASH_PATTERNS = [
    "README.md",
    "README.rst",
    "README.txt",
    "requirements.txt",
    "requirements*.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env.example",
]

_SOURCE_GLOBS = [
    "*.py",
    "*.js",
    "*.ts",
    "*.jsx",
    "*.tsx",
    "*.go",
    "*.rs",
    "*.java",
    "*.rb",
]

# Sections that can be individually regenerated
SECTIONS = {"rules", "skills", "constitution", "clinerules_yaml"}

CACHE_FILENAME = ".prg-cache.json"


class IncrementalAnalyzer:
    """Detect project changes and skip unnecessary regeneration."""

    def __init__(self, project_path: Path, output_dir: Path):
        self.project_path = Path(project_path)
        self.output_dir = Path(output_dir)
        self.cache_path = self.output_dir / CACHE_FILENAME
        self._cached_changed: Optional[Set[str]] = None
        # Current hash computed during detect_changes() — reused by save_hash()
        self._current_hash: Optional[Dict[str, str]] = None

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    def compute_project_hash(self) -> Dict[str, str]:
        """Hash key project files grouped by section.

        Returns a dict like::

            {
                'deps': '<sha256>',      # dependency files
                'readme': '<sha256>',     # README content
                'source': '<sha256>',     # source code (shallow)
                'tests': '<sha256>',      # test files
                'structure': '<sha256>',  # directory layout
            }

        This method is intentionally NOT cached — it re-reads files on each call
        so it always reflects the current on-disk state. Use detect_changes() for
        the cached "what changed vs last run" result.
        """
        return {
            "deps": self._hash_deps(),
            "readme": self._hash_readme(),
            "source": self._hash_source(),
            "tests": self._hash_tests(),
            "structure": self._hash_structure(),
        }

    def _hash_deps(self) -> str:
        h = hashlib.sha256()
        dep_files = sorted(
            [
                "requirements.txt",
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "package.json",
                "Pipfile",
                "poetry.lock",
            ]
        )
        for name in dep_files:
            p = self.project_path / name
            if p.exists():
                h.update(p.read_bytes())
        return h.hexdigest()

    def _hash_readme(self) -> str:
        h = hashlib.sha256()
        from generator.utils.readme_bridge import find_readme

        p = find_readme(self.project_path)
        if p:
            h.update(p.read_bytes())
        return h.hexdigest()

    def _hash_source(self) -> str:
        """Shallow hash of source files (name + size, not full content for speed)."""
        h = hashlib.sha256()
        files = []
        for ext in ("*.py", "*.js", "*.ts", "*.go", "*.rs", "*.java"):
            files.extend(sorted(self.project_path.rglob(ext)))
        for f in files:
            # Skip venvs, node_modules, __pycache__
            parts = f.relative_to(self.project_path).parts
            if any(p in (".venv", "venv", "node_modules", "__pycache__", ".git") for p in parts):
                continue
            try:
                h.update(f"{f.relative_to(self.project_path)}:{f.stat().st_size}".encode())
            except OSError:
                pass
        return h.hexdigest()

    def _hash_tests(self) -> str:
        h = hashlib.sha256()
        test_dirs = [self.project_path / "tests", self.project_path / "test"]
        for td in test_dirs:
            if td.is_dir():
                for f in sorted(td.rglob("*.py")):
                    try:
                        h.update(f"{f.relative_to(self.project_path)}:{f.stat().st_size}".encode())
                    except OSError:
                        pass
        return h.hexdigest()

    def _hash_structure(self) -> str:
        """Hash the top-level directory names and key config files presence."""
        h = hashlib.sha256()
        top_items = sorted(
            [
                p.name
                for p in self.project_path.iterdir()
                if not p.name.startswith(".") and p.name not in ("__pycache__", "node_modules", ".venv", "venv")
            ]
        )
        h.update(",".join(top_items).encode())
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Cache I/O
    # ------------------------------------------------------------------

    def load_previous_hash(self) -> Optional[Dict[str, str]]:
        """Read the previously cached hash from .clinerules/.prg-cache.json."""
        if not self.cache_path.exists():
            return None
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return data.get("hashes")
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            logger.warning("Failed to read cache: %s", exc)
            return None

    def save_hash(self, hashes: Dict[str, str]) -> None:
        """Persist current hashes to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hashes": hashes,
        }
        self.cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Change detection
    # ------------------------------------------------------------------

    def detect_changes(self) -> Set[str]:
        """Compare current hashes with cached ones.

        Returns a set of changed section keys (e.g. ``{'deps', 'readme'}``).
        If no cache exists, returns *all* sections (full regen).
        Result is cached on the instance — safe to call multiple times with
        no performance penalty (hash is computed only once per analyzer lifetime).
        """
        if self._cached_changed is not None:
            return self._cached_changed

        current = self.compute_project_hash()
        self._current_hash = current  # store for save_hash() to reuse
        previous = self.load_previous_hash()

        if previous is None:
            self._cached_changed = set(current.keys())
        else:
            changed: Set[str] = set()
            for key, value in current.items():
                if previous.get(key) != value:
                    changed.add(key)
            self._cached_changed = changed

        return self._cached_changed

    def phases_to_run(self) -> Tuple[bool, bool, bool, bool]:
        """Return which pipeline phases need to run based on changed sections.

        Returns:
            (run_enhanced_parse, run_rules, run_constitution, run_skills_gen)

        Mapping logic:
        - ``readme`` or ``deps`` changed  → rules + constitution need regeneration
        - ``source`` or ``structure`` changed → enhanced parse + skills need regeneration
        - Nothing changed          → all False (should have exited earlier)
        """
        changed = self.detect_changes()
        readme_or_deps = bool(changed & {"readme", "deps"})
        source_or_structure = bool(changed & {"source", "structure", "tests"})

        run_enhanced_parse = readme_or_deps or source_or_structure
        run_rules = readme_or_deps
        run_constitution = bool(changed & {"readme"})
        run_skills_gen = readme_or_deps or source_or_structure

        return run_enhanced_parse, run_rules, run_constitution, run_skills_gen

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    @staticmethod
    def merge_rules(existing_content: str, new_content: str, changed_sections: Set[str]) -> str:
        """Merge new sections into existing rules.md.

        Strategy:
        - If 'readme' or 'deps' changed, replace the entire header/rules block.
        - If only 'source' or 'tests' changed, replace from ``# Agent Skills`` onward.
        - If only 'structure' changed, replace the CONTEXT STRATEGY section.

        Falls back to full replacement when the file cannot be cleanly split.
        """
        # Fast path: if most things changed, just return the new content
        if changed_sections >= {"readme", "deps"}:
            return new_content

        # Try to preserve header and merge skills section
        # Look for the Agent Skills section boundary
        for marker in ("# Agent Skills", "# 🧠 Agent Skills"):
            if marker in existing_content and marker in new_content:
                if changed_sections <= {"source", "tests"}:
                    # Keep rules header, replace skills section
                    old_before = existing_content.split(marker, 1)[0]
                    new_after = new_content.split(marker, 1)[1]
                    return old_before + marker + new_after

        # Context strategy only
        ctx_marker = "## CONTEXT STRATEGY"
        if changed_sections == {"structure"} and ctx_marker in existing_content and ctx_marker in new_content:
            # Extract new context strategy section
            new_parts = new_content.split(ctx_marker, 1)
            old_parts = existing_content.split(ctx_marker, 1)
            if len(new_parts) == 2 and len(old_parts) == 2:
                # Find the end of the context strategy (next ## heading)
                import re

                new_section = re.split(r"\n## ", new_parts[1], 1)
                old_section = re.split(r"\n## ", old_parts[1], 1)
                if len(old_section) == 2:
                    return old_parts[0] + ctx_marker + new_section[0] + "\n## " + old_section[1]

        # Fallback: full replacement
        return new_content
