"""generator.tasks — task decomposition package.

Re-exports all public names so generator.task_decomposer shim continues to work.
"""

from generator.tasks.decomposer import TaskDecomposer
from generator.tasks.subtask_model import SubTask

# TraceabilityMatrix is loaded lazily to avoid a circular import:
#   task_creator → task_decomposer → tasks → traceability → task_creator
def __getattr__(name: str):
    if name == "TraceabilityMatrix":
        from generator.tasks.traceability import TraceabilityMatrix  # noqa: PLC0415
        return TraceabilityMatrix
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SubTask",
    "TaskDecomposer",
    "TraceabilityMatrix",
]
