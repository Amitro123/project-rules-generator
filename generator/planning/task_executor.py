"""Task executor — status tracker for task execution workflow."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .task_creator import TaskEntry, TaskFileStatus, TaskManifest


class TaskExecutor:
    """Track and update task execution status.

    This is a *status tracker*, not a code executor.  It marks tasks as
    in_progress / done and respects dependency ordering.  Agents or humans
    do the actual implementation work.
    """

    def __init__(self, manifest: TaskManifest):
        self.manifest = manifest
        self._index: Dict[int, TaskEntry] = {t.id: t for t in manifest.tasks}

    # -- Public API -------------------------------------------------------

    def execute_single(self, task_id: int) -> TaskEntry:
        """Mark *task_id* as ``in_progress`` after verifying dependencies.

        Raises ``ValueError`` if the task doesn't exist or has unmet deps.
        """
        entry = self._get_entry(task_id)

        unmet = self._unmet_deps(entry)
        if unmet:
            ids = ", ".join(f"#{d}" for d in unmet)
            raise ValueError(f"Task #{task_id} is blocked by unfinished deps: {ids}")

        entry.status = TaskFileStatus.in_progress
        entry.started_at = datetime.now().isoformat()
        return entry

    def complete_task(self, task_id: int) -> TaskEntry:
        """Mark *task_id* as ``done``."""
        entry = self._get_entry(task_id)
        entry.status = TaskFileStatus.done
        entry.completed_at = datetime.now().isoformat()
        return entry

    def skip_task(self, task_id: int) -> TaskEntry:
        """Mark *task_id* as ``skipped``."""
        entry = self._get_entry(task_id)
        entry.status = TaskFileStatus.skipped
        return entry

    def get_next_task(self) -> Optional[TaskEntry]:
        """Return the next pending task whose dependencies are all met."""
        for entry in self.manifest.tasks:
            if entry.status != TaskFileStatus.pending:
                continue
            if not self._unmet_deps(entry):
                return entry
        return None

    def get_progress_summary(self) -> Dict:
        """Return a dict with progress metrics."""
        total = len(self.manifest.tasks)
        done = sum(1 for t in self.manifest.tasks if t.status == TaskFileStatus.done)
        skipped = sum(
            1 for t in self.manifest.tasks if t.status == TaskFileStatus.skipped
        )
        in_progress = sum(
            1 for t in self.manifest.tasks if t.status == TaskFileStatus.in_progress
        )
        pending = total - done - skipped - in_progress

        est_remaining = sum(
            t.estimated_minutes
            for t in self.manifest.tasks
            if t.status in (TaskFileStatus.pending, TaskFileStatus.in_progress)
        )

        percent = int((done / total) * 100) if total else 100
        return {
            "total": total,
            "done": done,
            "skipped": skipped,
            "in_progress": in_progress,
            "pending": pending,
            "percent": percent,
            "est_remaining_minutes": est_remaining,
        }

    def save(self, path: Path) -> None:
        """Persist the manifest to disk."""
        self.manifest.save(path)

    # -- Helpers ----------------------------------------------------------

    def _get_entry(self, task_id: int) -> TaskEntry:
        entry = self._index.get(task_id)
        if entry is None:
            raise ValueError(f"Task #{task_id} not found in manifest.")
        return entry

    def _unmet_deps(self, entry: TaskEntry) -> List[int]:
        """Return IDs of dependencies that are not yet done/skipped."""
        unmet = []
        for dep_id in entry.dependencies:
            dep = self._index.get(dep_id)
            if dep is None:
                continue  # missing dep treated as met
            if dep.status not in (TaskFileStatus.done, TaskFileStatus.skipped):
                unmet.append(dep_id)
        return unmet
