"""Helper functions for the plan command.

Extracted from cli/agent.py to keep each module focused.
Covers: status reporting, roadmap-from-readme, TASKS.json writing, interactive mode.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click


def handle_plan_status(project_path: Path) -> None:
    """Print plan progress for all PLAN.md files found in *project_path* and exit."""
    from generator.planning import PlanParser

    parser = PlanParser()
    plan_files = parser.find_plans(project_path)

    if not plan_files:
        click.echo("No plan files found in project directory.")
        click.echo("Tip: Generate a plan with 'prg plan <task>' or 'prg plan --from-readme README.md'")
        sys.exit(0)

    for plan_file in plan_files:
        plan_status = parser.parse_plan(plan_file)
        report = parser.format_status_report(plan_status)
        click.echo(report)
        click.echo()

    sys.exit(0)


def handle_plan_from_readme(
    from_readme: str,
    project_path: Path,
    provider: str,
    api_key: Optional[str],
    output: Optional[str],
    output_format: str,
    verbose: bool,
    version: str,
) -> None:
    """Generate a project roadmap from README.md and exit."""
    from generator.planning import ProjectPlanner

    if verbose:
        click.echo(f"Project Rules Generator v{version} — Roadmap Generator")
        click.echo(f"From README: {from_readme}")
        click.echo(f"Project: {project_path}")
        click.echo(f"Generating roadmap with {provider}...")

    planner = ProjectPlanner(provider=provider, api_key=api_key)
    plan_obj = planner.generate_roadmap_from_readme(Path(from_readme), project_path=project_path)

    output_file = output or "PROJECT-ROADMAP.md"
    output_path = Path(output_file)
    if not output_path.is_absolute():
        output_path = project_path / output_path

    plan_obj.save(output_path, fmt=output_format)
    if verbose and output_format == "mermaid":
        click.echo("   Format: Mermaid diagram")

    tasks_path = output_path.with_name("TASKS.json")
    task_id = 0
    roadmap_tasks: List[Dict[str, Any]] = []
    for phase in plan_obj.phases:
        for task in phase.tasks:
            task_id += 1
            roadmap_tasks.append(
                {
                    "id": task_id,
                    "phase": phase.name,
                    "title": task.description,
                    "subtasks": task.subtasks,
                    "completed": task.completed,
                    "status": "done" if task.completed else "pending",
                }
            )

    tasks_data: Dict[str, Any] = {
        "plan_file": output_path.name,
        "created": datetime.now().isoformat(),
        "task": plan_obj.title,
        "tasks": roadmap_tasks,
    }
    tasks_path.write_text(json.dumps(tasks_data, indent=2), encoding="utf-8")

    click.echo("\n✅ Generated roadmap:")
    click.echo(f"   Title: {plan_obj.title}")
    click.echo(f"   Phases: {len(plan_obj.phases)}")
    total_tasks = sum(len(p.tasks) for p in plan_obj.phases)
    click.echo(f"   Tasks: {total_tasks}")
    click.echo(f"   Saved to: {output_path}")
    click.echo(f"   Tasks manifest: {tasks_path}")

    sys.exit(0)


def write_tasks_manifest(output_path: Path, user_task_label: str, subtasks: List[Any]) -> Path:
    """Serialise *subtasks* to TASKS.json next to *output_path*.

    Returns the path of the written manifest file.
    """
    tasks_path = output_path.with_name("TASKS.json")
    tasks_data: Dict[str, Any] = {
        "plan_file": output_path.name,
        "created": datetime.now().isoformat(),
        "task": user_task_label,
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "goal": t.goal,
                "files": t.files,
                "dependencies": t.dependencies,
                "estimated_minutes": t.estimated_minutes,
                "status": "pending",
            }
            for t in subtasks
        ],
    }
    tasks_path.write_text(json.dumps(tasks_data, indent=2), encoding="utf-8")
    return tasks_path


def run_interactive_mode(subtasks: List[Any], project_path: Path, auto_execute: bool) -> None:
    """Open files in the detected IDE for each subtask in sequence."""
    import shutil
    import subprocess

    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        for candidate in ["code", "cursor", "subl", "vim", "notepad"]:
            if shutil.which(candidate):
                editor = candidate
                break

    click.echo(f"\n--- Interactive Mode (editor: {editor or 'none'}) ---")
    for task in subtasks:
        click.echo(f"\nTask {task.id}: {task.title}")
        click.echo(f"  Goal: {task.goal}")
        if task.files and editor:
            for fpath in task.files:
                full_path = project_path / fpath
                action = "Open" if full_path.exists() else "Create"
                click.echo(f"  [{action}] {fpath}")
                if auto_execute and not full_path.exists():
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(f"# TODO: {task.title}\n", encoding="utf-8")
                try:
                    subprocess.Popen([editor, str(full_path)])
                except Exception as e:
                    click.echo(f"  Could not open {fpath}: {e}")
        elif task.files:
            for fpath in task.files:
                full_path = project_path / fpath
                action = "Open" if full_path.exists() else "Create"
                click.echo(f"  [{action}] {fpath} (no editor detected)")
        if not auto_execute:
            try:
                input("  Press Enter for next task...")
            except (EOFError, KeyboardInterrupt):
                click.echo("\nAborted.")
                break
