"""Ralph Feature Loop Engine — backward-compatibility shim.

All logic has moved to generator/ralph/:
  generator/ralph/state.py   — FeatureState dataclass
  generator/ralph/tasks.py   — TASKS.yaml helpers + feature ID utilities
  generator/ralph/engine.py  — RalphEngine class

This file re-exports everything so existing imports continue to work unchanged.
"""

from generator.ralph import (  # noqa: F401
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
