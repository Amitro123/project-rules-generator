"""Task file creator — converts SubTask list into tasks/ directory with TASKS.yaml."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from generator.task_decomposer import SubTask


class TaskFileStatus(str, Enum):
    """Status of an individual task file."""

    pending = "pending"
    in_progress = "in_progress"
    done = "done"
    blocked = "blocked"
    skipped = "skipped"


@dataclass
class TaskEntry:
    """A single entry in the task manifest."""

    id: int
    file: str
    title: str
    status: TaskFileStatus = TaskFileStatus.pending
    dependencies: List[int] = field(default_factory=list)
    estimated_minutes: int = 5
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        d = {
            "id": self.id,
            "file": self.file,
            "title": self.title,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "estimated_minutes": self.estimated_minutes,
        }
        if self.started_at:
            d["started_at"] = self.started_at
        if self.completed_at:
            d["completed_at"] = self.completed_at
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "TaskEntry":
        return cls(
            id=data["id"],
            file=data["file"],
            title=data["title"],
            status=TaskFileStatus(data.get("status", "pending")),
            dependencies=data.get("dependencies", []),
            estimated_minutes=data.get("estimated_minutes", 5),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class TaskManifest:
    """Manifest tracking all task files and their statuses."""

    plan_file: str
    task_description: str
    created: str = ""
    updated: str = ""
    tasks: List[TaskEntry] = field(default_factory=list)

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().isoformat()
        if not self.updated:
            self.updated = self.created

    def to_dict(self) -> Dict:
        return {
            "plan_file": self.plan_file,
            "task_description": self.task_description,
            "created": self.created,
            "updated": self.updated,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TaskManifest":
        return cls(
            plan_file=data.get("plan_file", ""),
            task_description=data.get("task_description", ""),
            created=data.get("created", ""),
            updated=data.get("updated", ""),
            tasks=[TaskEntry.from_dict(t) for t in data.get("tasks", [])],
        )

    def save(self, path: Path) -> None:
        """Write manifest to a YAML file."""
        self.updated = datetime.now().isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(self.to_dict(), default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

    @classmethod
    def from_yaml(cls, path: Path) -> "TaskManifest":
        """Load manifest from a YAML file."""
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.from_dict(data)


class TaskCreator:
    """Create individual task files and a TASKS.yaml manifest from SubTasks."""

    def create_from_subtasks(
        self,
        subtasks: List[SubTask],
        plan_file: str,
        task_description: str = "",
        output_dir: Optional[Path] = None,
    ) -> TaskManifest:
        """Convert a SubTask list into a tasks/ directory with .md files + TASKS.yaml.

        Args:
            subtasks: List of SubTask objects from TaskDecomposer.
            plan_file: Name of the originating PLAN.md file.
            task_description: Human-readable task description.
            output_dir: Directory to write task files into (default: tasks/).

        Returns:
            The populated TaskManifest.
        """
        if output_dir is None:
            output_dir = Path("tasks")

        output_dir.mkdir(parents=True, exist_ok=True)

        entries: List[TaskEntry] = []
        for subtask in subtasks:
            filename = self._subtask_to_filename(subtask)
            md_content = self._render_task_md(subtask)

            filepath = output_dir / filename
            filepath.write_text(md_content, encoding="utf-8")

            entries.append(
                TaskEntry(
                    id=subtask.id,
                    file=filename,
                    title=subtask.title,
                    status=TaskFileStatus.pending,
                    dependencies=list(subtask.dependencies),
                    estimated_minutes=subtask.estimated_minutes,
                )
            )

        manifest = TaskManifest(
            plan_file=plan_file,
            task_description=task_description or plan_file,
            tasks=entries,
        )

        manifest.save(output_dir / "TASKS.yaml")
        return manifest

    @staticmethod
    def _subtask_to_filename(subtask: SubTask) -> str:
        """Generate a filename like ``task001-research-redis.py`` from a SubTask."""
        slug = re.sub(r"[^a-z0-9]+", "-", subtask.title.lower()).strip("-")
        # Truncate to keep filenames reasonable
        slug = slug[:50].rstrip("-")
        return f"task{subtask.id:03d}-{slug}.{subtask.type}"

    @staticmethod
    def _render_task_md(subtask: SubTask) -> str:
        """Render a single SubTask as a markdown or python file."""
        lines = [
            f"# Task {subtask.id}: {subtask.title}",
            "",
            f"**Goal:** {subtask.goal}",
            f"**Estimated:** ~{subtask.estimated_minutes} min",
        ]

        if subtask.dependencies:
            dep_str = ", ".join(f"#{d}" for d in subtask.dependencies)
            lines.append(f"**Depends on:** {dep_str}")

        lines.append("")

        if subtask.files:
            lines.append("## Files")
            for f in subtask.files:
                lines.append(f"- `{f}`")
            lines.append("")

        if subtask.changes:
            lines.append("## Changes")
            for c in subtask.changes:
                lines.append(f"- {c}")
            lines.append("")

        if subtask.tests:
            lines.append("## Tests")
            for t in subtask.tests:
                lines.append(f"- {t}")
            lines.append("")

        lines.append("## Status")
        lines.append("- [ ] Not started")
        lines.append("")

        content = "\n".join(lines)
        
        if subtask.type == "py":
            return f'"""\n{content}\n"""\n\nif __name__ == "__main__":\n    print("Task: {subtask.title}")\n    print("Goal: {subtask.goal}")\n'
        
        return content
