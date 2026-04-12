"""TASKS.yaml I/O helpers and feature ID utilities for Ralph."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

import yaml


def next_feature_id(features_dir: Path) -> str:
    """Return the next available FEATURE-XXX identifier."""
    existing: List[int] = []
    if features_dir.exists():
        for entry in features_dir.iterdir():
            if entry.is_dir():
                m = re.match(r"FEATURE-(\d+)", entry.name)
                if m:
                    existing.append(int(m.group(1)))
    n = max(existing, default=0) + 1
    return f"FEATURE-{n:03d}"


def slugify(text: str) -> str:
    """Convert a task description to a git-branch-friendly slug (max 40 chars)."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40]


def _load_tasks(tasks_yaml: Path) -> List[dict]:
    """Load tasks list from TASKS.yaml.  Returns [] if file absent."""
    if not tasks_yaml.exists():
        return []
    raw = yaml.safe_load(tasks_yaml.read_text(encoding="utf-8")) or {}
    return raw.get("tasks", [])


def _save_tasks(tasks_yaml: Path, tasks: List[dict]) -> None:
    tasks_yaml.parent.mkdir(parents=True, exist_ok=True)
    tmp = tasks_yaml.with_suffix(".tmp")
    tmp.write_text(yaml.dump({"tasks": tasks}, default_flow_style=False), encoding="utf-8")
    os.replace(tmp, tasks_yaml)


def _pending_tasks(tasks: List[dict]) -> List[dict]:
    return [t for t in tasks if t.get("status", "pending") == "pending"]
