"""AI-powered task decomposition — backward-compatibility shim.

All logic has moved to generator/tasks/:
  generator/tasks/subtask_model.py — SubTask Pydantic model
  generator/tasks/decomposer.py    — TaskDecomposer class

This file re-exports everything so existing imports continue to work unchanged.
"""

from generator.tasks import SubTask, TaskDecomposer  # noqa: F401

__all__ = [
    "SubTask",
    "TaskDecomposer",
]
