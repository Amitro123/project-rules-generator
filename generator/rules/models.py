"""Data models for rules generation: Rule, RulesMetadata, QualityReport."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Rule:
    """Single coding rule with priority."""

    content: str
    priority: str = "Medium"  # High, Medium, Low
    category: str = "General"  # Coding Standards, Architecture, Testing, etc.
    source: str = "analysis"  # analysis, git_history, tech_stack


@dataclass
class RulesMetadata:
    """Structured metadata for rules generation."""

    project_name: str
    tech_stack: List[str] = field(default_factory=list)
    project_type: str = "unknown"
    priority_areas: List[str] = field(default_factory=list)  # async_patterns, rest_api, etc.
    detected_signals: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """Quality assessment of generated rules."""

    score: float  # 0-100
    passed: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    completeness: float = 0.0  # % of expected sections present
    conflicts: List[str] = field(default_factory=list)  # Contradictory rules
