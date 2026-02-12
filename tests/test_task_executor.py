"""Tests for task executor (status tracker)."""
import pytest

from generator.planning.task_creator import TaskEntry, TaskFileStatus, TaskManifest
from generator.planning.task_executor import TaskExecutor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_manifest(statuses=None):
    """Build a TaskManifest with 3 tasks in a dependency chain: 1 -> 2 -> 3."""
    if statuses is None:
        statuses = ["pending", "pending", "pending"]
    tasks = [
        TaskEntry(id=1, file="001-a.md", title="Research",
                  status=TaskFileStatus(statuses[0]),
                  dependencies=[], estimated_minutes=3),
        TaskEntry(id=2, file="002-b.md", title="Implement",
                  status=TaskFileStatus(statuses[1]),
                  dependencies=[1], estimated_minutes=5),
        TaskEntry(id=3, file="003-c.md", title="Test",
                  status=TaskFileStatus(statuses[2]),
                  dependencies=[2], estimated_minutes=4),
    ]
    return TaskManifest(
        plan_file="PLAN.md",
        task_description="Add cache",
        tasks=tasks,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTaskExecutor:

    def test_execute_first_task(self):
        manifest = _make_manifest()
        executor = TaskExecutor(manifest)
        entry = executor.execute_single(1)
        assert entry.status == TaskFileStatus.in_progress
        assert entry.started_at is not None

    def test_execute_blocked_task_raises(self):
        manifest = _make_manifest()
        executor = TaskExecutor(manifest)
        with pytest.raises(ValueError, match="blocked"):
            executor.execute_single(2)

    def test_execute_after_deps_done(self):
        manifest = _make_manifest(["done", "pending", "pending"])
        executor = TaskExecutor(manifest)
        entry = executor.execute_single(2)
        assert entry.status == TaskFileStatus.in_progress

    def test_complete_task(self):
        manifest = _make_manifest(["in_progress", "pending", "pending"])
        executor = TaskExecutor(manifest)
        entry = executor.complete_task(1)
        assert entry.status == TaskFileStatus.done
        assert entry.completed_at is not None

    def test_skip_task(self):
        manifest = _make_manifest()
        executor = TaskExecutor(manifest)
        entry = executor.skip_task(1)
        assert entry.status == TaskFileStatus.skipped

    def test_skip_unblocks_dependents(self):
        """Skipping a dependency should unblock the next task."""
        manifest = _make_manifest()
        executor = TaskExecutor(manifest)
        executor.skip_task(1)
        # Task 2 depends on 1 which is now skipped -> should be unblocked
        entry = executor.execute_single(2)
        assert entry.status == TaskFileStatus.in_progress

    def test_get_next_task_initial(self):
        manifest = _make_manifest()
        executor = TaskExecutor(manifest)
        nxt = executor.get_next_task()
        assert nxt is not None
        assert nxt.id == 1

    def test_get_next_task_after_first_done(self):
        manifest = _make_manifest(["done", "pending", "pending"])
        executor = TaskExecutor(manifest)
        nxt = executor.get_next_task()
        assert nxt.id == 2

    def test_get_next_task_all_done(self):
        manifest = _make_manifest(["done", "done", "done"])
        executor = TaskExecutor(manifest)
        assert executor.get_next_task() is None

    def test_get_next_skips_in_progress(self):
        manifest = _make_manifest(["in_progress", "pending", "pending"])
        executor = TaskExecutor(manifest)
        nxt = executor.get_next_task()
        # Task 2 is blocked by 1 (in_progress), so no next
        assert nxt is None

    def test_nonexistent_task_raises(self):
        manifest = _make_manifest()
        executor = TaskExecutor(manifest)
        with pytest.raises(ValueError, match="not found"):
            executor.execute_single(99)

    def test_progress_summary_initial(self):
        manifest = _make_manifest()
        executor = TaskExecutor(manifest)
        s = executor.get_progress_summary()
        assert s["total"] == 3
        assert s["done"] == 0
        assert s["pending"] == 3
        assert s["percent"] == 0
        assert s["est_remaining_minutes"] == 12

    def test_progress_summary_partial(self):
        manifest = _make_manifest(["done", "in_progress", "pending"])
        executor = TaskExecutor(manifest)
        s = executor.get_progress_summary()
        assert s["done"] == 1
        assert s["in_progress"] == 1
        assert s["pending"] == 1
        assert s["percent"] == 33
        assert s["est_remaining_minutes"] == 9  # 5 + 4

    def test_progress_summary_all_done(self):
        manifest = _make_manifest(["done", "done", "done"])
        executor = TaskExecutor(manifest)
        s = executor.get_progress_summary()
        assert s["percent"] == 100
        assert s["est_remaining_minutes"] == 0

    def test_save_and_reload(self, tmp_path):
        manifest = _make_manifest()
        executor = TaskExecutor(manifest)
        executor.execute_single(1)
        executor.complete_task(1)

        yaml_path = tmp_path / "TASKS.yaml"
        executor.save(yaml_path)

        loaded = TaskManifest.from_yaml(yaml_path)
        assert loaded.tasks[0].status == TaskFileStatus.done
        assert loaded.tasks[0].completed_at is not None
