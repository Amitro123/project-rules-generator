"""Configuration for analyzer and planning modules."""

from dataclasses import dataclass


@dataclass
class AnalyzerConfig:
    """Configuration for ContentAnalyzer."""

    # Scoring thresholds
    low_score_threshold: int = 85
    excellent_threshold: int = 90
    good_threshold: int = 85
    needs_improvement_threshold: int = 70

    # Opik integration
    enable_opik: bool = False

    # AI parameters
    ai_temperature: float = 0.3
    ai_max_tokens: int = 2000
    patch_max_tokens: int = 8000

    # Analysis limits — Llama 3.1 8B has 128K context on Groq,
    # so we can afford to analyze much more than the old 3000-char limit.
    max_content_length: int = 12000
    max_readme_excerpt: int = 1000
    max_suggestions: int = 5

    # Heuristic scoring defaults
    default_score_per_criterion: int = 10

    @property
    def total_default_score(self) -> int:
        """Total score when all criteria use default."""
        return self.default_score_per_criterion * 5


@dataclass
class PlannerConfig:
    """Configuration for ProjectPlanner."""

    # AI parameters
    ai_temperature: float = 0.5
    roadmap_max_tokens: int = 3000
    task_plan_max_tokens: int = 2500

    # Content limits
    max_readme_content: int = 2000
    max_readme_excerpt: int = 1000
    max_features: int = 10

    # Plan structure
    min_phases: int = 3
    max_phases: int = 5
    min_tasks_per_phase: int = 2
    max_tasks_per_phase: int = 7
