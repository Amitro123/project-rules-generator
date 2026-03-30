"""
Rules Git Miner
===============

Extracts anti-patterns from git history (hot spots, large commits).
Extracted from CoworkRulesCreator to keep each module focused.
"""

import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from generator.rules_creator import Rule


class RulesGitMiner:
    """Mines git history to surface anti-patterns as rules."""

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        self.available = self._check_available()

    def _check_available(self) -> bool:
        """Check if git is available and project is a git repo."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_path,
                capture_output=True,
                timeout=2,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def extract_antipatterns(self) -> List["Rule"]:
        """Extract anti-patterns from git history.

        Returns empty list if git is unavailable.
        """
        from generator.rules_creator import Rule

        antipatterns: List[Rule] = []
        if not self.available:
            return antipatterns

        try:
            antipatterns.extend(self._find_hotspots())
            antipatterns.extend(self._find_large_commits())
        except (OSError, subprocess.SubprocessError):
            pass

        return antipatterns

    def _find_hotspots(self) -> List["Rule"]:
        """Detect frequently-modified files (hot spots)."""
        from generator.rules_creator import Rule

        result = subprocess.run(
            ["git", "log", "--pretty=format:", "--name-only"],
            cwd=self.project_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=5,
        )

        if result.returncode != 0:
            return []

        file_changes: Dict[str, int] = defaultdict(int)
        for line in result.stdout.split("\n"):
            if line.strip():
                file_changes[line] += 1

        hotspots = [f for f, count in file_changes.items() if count > 10]
        if not hotspots:
            return []

        return [
            Rule(
                f"\U0001f525 Hot spots detected: {', '.join(hotspots[:3])} - consider refactoring",
                priority="Medium",
                category="Anti-Patterns from History",
                source="git_history",
            )
        ]

    def _find_large_commits(self) -> List["Rule"]:
        """Detect commits with > 500 insertions."""
        from generator.rules_creator import Rule

        result = subprocess.run(
            ["git", "log", "--shortstat", "--oneline", "-10"],
            cwd=self.project_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=5,
        )

        if result.returncode != 0:
            return []

        large_commits = 0
        for line in result.stdout.split("\n"):
            m = re.search(r"(\d+) insertions?\(\+\)", line)
            if m and int(m.group(1)) > 500:
                large_commits += 1

        if large_commits <= 2:
            return []

        return [
            Rule(
                "\U0001f525 Large commits detected - break down changes into smaller commits",
                priority="Low",
                category="Anti-Patterns from History",
                source="git_history",
            )
        ]
