"""TechProfile dataclass — single metadata model for one technology."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TechProfile:
    """Complete metadata for one technology."""

    name: str
    """Canonical tech identifier (e.g. 'fastapi')."""

    skill_name: str = ""
    """Preferred skill filename stem (e.g. 'fastapi-endpoints'). Empty = no skill."""

    packages: List[str] = field(default_factory=list)
    """Package names in requirements.txt / pyproject.toml that signal this tech."""

    readme_keywords: List[str] = field(default_factory=list)
    """Keywords that appear in README prose to confirm detection."""

    tools: List[str] = field(default_factory=list)
    """CLI/shell tools associated with this tech (used in skill metadata)."""

    rules: Dict[str, List[str]] = field(default_factory=dict)
    """Coding rules keyed by priority: {'high': [...], 'medium': [...], 'low': [...]}."""

    import_name: str = ""
    """Python import keyword when it differs from the pip package name.
    E.g. gitpython is installed as 'gitpython' but imported as 'git'.
    Leave empty to derive from packages[0] (stripping hyphens, taking first segment).
    """

    display_name: str = ""
    """Human-readable label used in tech_stack output (e.g. 'FastAPI', 'Next.js').
    Falls back to name.title() when empty."""

    category: str = "backend"
    """Bucket in the tech_stack dict returned by ProjectAnalyzer.
    Valid values: backend | frontend | database | infrastructure | ml | ai | testing | language
    """

    detection_files: List[str] = field(default_factory=list)
    """File paths relative to project root whose existence signals this tech
    (used for infrastructure tools that aren't pip/npm packages, e.g. 'Dockerfile')."""

    detection_dirs: List[str] = field(default_factory=list)
    """Directory paths relative to project root whose existence signals this tech
    (e.g. '.github/workflows' for GitHub Actions)."""
