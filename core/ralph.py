"""core.ralph — canonical home of the Ralph Feature Loop Engine.

All logic lives in generator.ralph_engine; this module re-exports everything
so new code can import from ``core.ralph`` while existing imports from
``generator.ralph_engine`` keep working unchanged.
"""

from generator.ralph_engine import (  # noqa: F401
    FeatureState,
    RalphEngine,
    _load_tasks,
    _pending_tasks,
    _save_tasks,
    next_feature_id,
    slugify,
)

__all__ = [
    "RalphEngine",
    "FeatureState",
    "next_feature_id",
    "slugify",
    "_load_tasks",
    "_save_tasks",
    "_pending_tasks",
]
