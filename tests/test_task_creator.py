"""Tests for task file creator (agent workflow)."""
import pytest
from pathlib import Path

from generator.task_decomposer import SubTask
from generator.planning.task_creator import (
    TaskCreator,
    TaskEntry,
    TaskFileStatus,
    TaskManifest,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _sample_subtasks():
    """Create a list of sample SubTasks for testing."""
    return [
        SubTask(
            id=1,
            title="Research Redis caching",
            goal="Understand Redis patterns",
            files=["docs/redis.md"],
            changes=["Add research notes"],
            tests=["pytest tests/test_cache.py"],
            dependencies=[],
            estimated_minutes=3,
        ),
        SubTask(
            id=2,
            title="Implement cache layer",
            goal="Add Redis cache to API",
            files=["src/cache.py", "src/api.py"],
            changes=["Create cache module", "Wire cache into API"],
            tests=["pytest tests/test_cache.py"],
            dependencies=[1],
            estimated_minutes=5,
        ),
        SubTask(
            id=3,
            title="Write tests",
            goal="Cover cache functionality",
            files=["tests/test_cache.py"],
            changes=["Add cache tests"],
            tests=["pytest tests/"],
            dependencies=[2],
            estimated_minutes=4,
        ),
    ]


# ---------------------------------------------------------------------------
# TaskFileStatus
# ---------------------------------------------------------------------------

class TestTaskFileStatus:

    def test_enum_values(self):
        assert TaskFileStatus.pending.value == "pending"
        assert TaskFileStatus.in_progress.value == "in_progress"
        assert TaskFileStatus.done.value == "done"
        assert TaskFileStatus.blocked.value == "blocked"
        assert TaskFileStatus.skipped.value == "skipped"

    def test_from_string(self):
        assert TaskFileStatus("done") == TaskFileStatus.done


# ---------------------------------------------------------------------------
# TaskEntry
# ---------------------------------------------------------------------------

class TestTaskEntry:

    def test_to_dict(self):
        entry = TaskEntry(
            id=1, file="001-research.md", title="Research",
            dependencies=[],  estimated_minutes=3,
        )
        d = entry.to_dict()
        assert d["id"] == 1
        assert d["file"] == "001-research.md"
        assert d["status"] == "pending"
        assert "started_at" not in d  # omitted when None

    def test_roundtrip(self):
        entry = TaskEntry(
            id=2, file="002-impl.md", title="Implement",
            status=TaskFileStatus.in_progress,
            dependencies=[1], estimated_minutes=5,
            started_at="2025-01-01T00:00:00",
        )
        d = entry.to_dict()
        restored = TaskEntry.from_dict(d)
        assert restored.id == entry.id
        assert restored.status == TaskFileStatus.in_progress
        assert restored.started_at == "2025-01-01T00:00:00"


# ---------------------------------------------------------------------------
# TaskManifest
# ---------------------------------------------------------------------------

class TestTaskManifest:

    def test_creation_sets_timestamps(self):
        m = TaskManifest(plan_file="PLAN.md", task_description="Add cache")
        assert m.created != ""
        assert m.updated != ""

    def test_to_dict_roundtrip(self):
        entry = TaskEntry(id=1, file="001-x.md", title="X")
        m = TaskManifest(
            plan_file="PLAN.md",
            task_description="Do stuff",
            tasks=[entry],
        )
        d = m.to_dict()
        restored = TaskManifest.from_dict(d)
        assert restored.plan_file == "PLAN.md"
        assert len(restored.tasks) == 1
        assert restored.tasks[0].title == "X"

    def test_yaml_roundtrip(self, tmp_path):
        entry = TaskEntry(id=1, file="001-a.md", title="A", estimated_minutes=3)
        m = TaskManifest(
            plan_file="PLAN.md", task_description="Test",
            tasks=[entry],
        )
        yaml_path = tmp_path / "TASKS.yaml"
        m.save(yaml_path)

        assert yaml_path.exists()

        loaded = TaskManifest.from_yaml(yaml_path)
        assert loaded.plan_file == "PLAN.md"
        assert loaded.tasks[0].id == 1
        assert loaded.tasks[0].estimated_minutes == 3


# ---------------------------------------------------------------------------
# TaskCreator
# ---------------------------------------------------------------------------

class TestTaskCreator:

    def test_subtask_to_filename(self):
        st = SubTask(id=1, title="Research Redis caching", goal="g")
        name = TaskCreator._subtask_to_filename(st)
        assert name == "001-research-redis-caching.md"

    def test_subtask_to_filename_special_chars(self):
        st = SubTask(id=12, title="Implement API v2.0 (new!)", goal="g")
        name = TaskCreator._subtask_to_filename(st)
        assert name.startswith("012-")
        assert "(" not in name
        assert name.endswith(".md")

    def test_render_task_md(self):
        st = SubTask(
            id=1, title="Research", goal="Understand patterns",
            files=["docs/x.md"], changes=["Add notes"],
            tests=["pytest"], dependencies=[],
            estimated_minutes=3,
        )
        md = TaskCreator._render_task_md(st)
        assert "# Task 1: Research" in md
        assert "**Goal:** Understand patterns" in md
        assert "`docs/x.md`" in md
        assert "- [ ] Not started" in md

    def test_render_task_md_with_deps(self):
        st = SubTask(id=2, title="Impl", goal="Do it", dependencies=[1])
        md = TaskCreator._render_task_md(st)
        assert "#1" in md

    def test_create_from_subtasks(self, tmp_path):
        subtasks = _sample_subtasks()
        creator = TaskCreator()
        manifest = creator.create_from_subtasks(
            subtasks=subtasks,
            plan_file="PLAN.md",
            task_description="Add Redis cache",
            output_dir=tmp_path / "tasks",
        )

        # Manifest populated
        assert len(manifest.tasks) == 3
        assert manifest.plan_file == "PLAN.md"
        assert manifest.task_description == "Add Redis cache"

        # Files created
        task_dir = tmp_path / "tasks"
        assert task_dir.is_dir()
        assert (task_dir / "TASKS.yaml").exists()

        md_files = sorted(task_dir.glob("0*.md"))
        assert len(md_files) == 3
        assert md_files[0].name.startswith("001-")

        # Dependencies preserved
        assert manifest.tasks[1].dependencies == [1]
        assert manifest.tasks[2].dependencies == [2]

    def test_idempotent_directory_creation(self, tmp_path):
        """Creating tasks twice should overwrite existing files."""
        subtasks = _sample_subtasks()
        creator = TaskCreator()
        out_dir = tmp_path / "tasks"

        creator.create_from_subtasks(subtasks, "PLAN.md", output_dir=out_dir)
        creator.create_from_subtasks(subtasks, "PLAN.md", output_dir=out_dir)

        md_files = sorted(out_dir.glob("0*.md"))
        assert len(md_files) == 3
