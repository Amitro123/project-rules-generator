"""Job execution commands for project rules generator."""

import sys
from pathlib import Path

import click


@click.command(name="exec")
@click.argument("task_file", type=click.Path(dir_okay=False))
@click.option("--complete", is_flag=True, help="Mark the task as done")
@click.option("--skip", is_flag=True, help="Skip the task")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
def exec_task(task_file, complete, skip, project_path):
    """Start or complete a task from the manifest."""
    project_path = Path(project_path).resolve()
    tasks_yaml = project_path / "tasks" / "TASKS.yaml"

    if not tasks_yaml.exists():
        click.echo("No TASKS.yaml found. Run 'prg setup <task>' first.", err=True)
        sys.exit(1)

    from generator.planning.task_creator import TaskManifest
    from generator.planning.task_executor import TaskExecutor

    manifest = TaskManifest.from_yaml(tasks_yaml)
    executor = TaskExecutor(manifest)

    # Find the task by filename
    task_filename = Path(task_file).name
    entry = None
    for t in manifest.tasks:
        if t.file == task_filename:
            entry = t
            break

    if entry is None:
        click.echo(f"Task file '{task_filename}' not found in TASKS.yaml.", err=True)
        sys.exit(1)

    try:
        if complete:
            executor.complete_task(entry.id)
            click.echo(f"Task #{entry.id} '{entry.title}' marked as done.")
        elif skip:
            executor.skip_task(entry.id)
            click.echo(f"Task #{entry.id} '{entry.title}' skipped.")
        else:
            executor.execute_single(entry.id)
            click.echo(f"Task #{entry.id} '{entry.title}' started.")
            click.echo(f"  File: tasks/{entry.file}")
            if entry.dependencies:
                dep_str = ", ".join(f"#{d}" for d in entry.dependencies)
                click.echo(f"  Deps: {dep_str}")
            click.echo(f"\\nWhen done, run: prg exec {task_file} --complete")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    executor.save(tasks_yaml)

    # Show progress
    summary = executor.get_progress_summary()
    click.echo(
        f"\\nProgress: {summary['done']}/{summary['total']} done ({summary['percent']}%), "
        f"~{summary['est_remaining_minutes']} min remaining"
    )

    nxt = executor.get_next_task()
    if nxt:
        click.echo(f"Next: #{nxt.id} {nxt.title} -> prg exec tasks/{nxt.file}")


@click.command(name="status")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
def status(project_path):
    """Show progress on current tasks or plans."""
    project_path = Path(project_path).resolve()

    # Candidate paths for task manifests
    candidates = [
        project_path / "tasks" / "TASKS.yaml",
        project_path / ".clinerules" / "tasks" / "TASKS.yaml",
        project_path / "TASKS.json",
        project_path / ".clinerules" / "TASKS.json",
    ]

    manifest_path = None
    for cand in candidates:
        if cand.exists():
            manifest_path = cand
            break

    if manifest_path:
        if manifest_path.suffix == ".json":
            _show_json_status(manifest_path)
        else:
            _show_yaml_status(manifest_path)
        return

    # Fallback to PlanParser for PLAN.md files
    from generator.planning import PlanParser

    parser = PlanParser()
    plan_files = parser.find_plans(project_path)

    if not plan_files:
        click.echo("No tasks or plans found.")
        click.echo("Tip: Run 'prg setup <task>' or 'prg plan <task>' first.")
        sys.exit(0)

    for plan_file in plan_files:
        plan_status = parser.parse_plan(plan_file)
        report = parser.format_status_report(plan_status)
        click.echo(report)
        click.echo()


def _show_yaml_status(tasks_yaml):
    from generator.planning.task_creator import TaskManifest
    from generator.planning.task_executor import TaskExecutor

    manifest = TaskManifest.from_yaml(tasks_yaml)
    executor = TaskExecutor(manifest)
    summary = executor.get_progress_summary()

    click.echo(f"Task Progress: {manifest.task_description}")
    click.echo(f"{'=' * 50}")
    click.echo(f"Overall: {summary['done']}/{summary['total']} done ({summary['percent']}%)")
    click.echo(f"Estimated remaining: ~{summary['est_remaining_minutes']} min")
    click.echo()

    for entry in manifest.tasks:
        if entry.status.value == "done":
            icon = "[x]"
        elif entry.status.value == "in_progress":
            icon = "[>]"
        elif entry.status.value == "skipped":
            icon = "[-]"
        elif entry.status.value == "blocked":
            icon = "[!]"
        else:
            icon = "[ ]"
        click.echo(f"  {icon} #{entry.id} {entry.title} (~{entry.estimated_minutes}m)")

    nxt = executor.get_next_task()
    if nxt:
        click.echo(f"\nNext: #{nxt.id} {nxt.title}")
        click.echo(f"  Run: prg exec tasks/{nxt.file}")
    elif summary["done"] == summary["total"]:
        click.echo("\nAll tasks complete!")


def _show_json_status(tasks_json):
    import json

    data = json.loads(tasks_json.read_text(encoding="utf-8"))

    click.echo(f"Task Progress: {data.get('task', 'Untitled Plan')}")
    click.echo(f"{'=' * 50}")

    tasks = data.get("tasks", [])
    done = sum(1 for t in tasks if t.get("status") in ["done", "completed"])
    total = len(tasks)
    percent = int((done / total) * 100) if total > 0 else 0

    click.echo(f"Overall: {done}/{total} done ({percent}%)")
    click.echo()

    for t in tasks:
        status = t.get("status", "pending")
        if status in ["done", "completed"]:
            icon = "[x]"
        elif status == "in_progress":
            icon = "[>]"
        else:
            icon = "[ ]"

        click.echo(f"  {icon} #{t.get('id')} {t.get('title')}")

    # Simplified "next" for JSON
    pending = [t for t in tasks if t.get("status") == "pending"]
    if pending:
        nxt = pending[0]
        click.echo(f"\nNext: #{nxt.get('id')} {nxt.get('title')}")


@click.command(name="next")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
def next_task(project_path):
    """Execute the next pending task."""
    project_path = Path(project_path).resolve()
    # For now, we reuse the logic from status to find manifest
    tasks_yaml = project_path / "tasks" / "TASKS.yaml"
    if not tasks_yaml.exists():
        tasks_yaml = project_path / ".clinerules" / "tasks" / "TASKS.yaml"

    if not tasks_yaml.exists():
        # Try JSON
        tasks_json = project_path / "TASKS.json"
        if not tasks_json.exists():
            tasks_json = project_path / ".clinerules" / "TASKS.json"

        if tasks_json.exists():
            import json

            data = json.loads(tasks_json.read_text(encoding="utf-8"))
            tasks = data.get("tasks", [])
            pending = [t for t in tasks if t.get("status") == "pending"]
            if not pending:
                click.echo("No pending tasks found.")
                return
            nxt = pending[0]
            click.echo(f"Executing next task: #{nxt.get('id')} {nxt.get('title')}")
            # For JSON we don't have a file mapping usually, so just echo
            return

    from generator.planning.task_creator import TaskManifest
    from generator.planning.task_executor import TaskExecutor

    manifest = TaskManifest.from_yaml(tasks_yaml)
    executor = TaskExecutor(manifest)

    nxt = executor.get_next_task()
    if not nxt:
        click.echo("No pending tasks found.")
        return

    click.echo(f"Executing next task: #{nxt.id} {nxt.title}")
    click.echo(f"Run: prg exec tasks/{nxt.file}")


@click.command(name="query")
@click.argument("search_term")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
def query_tasks(search_term, project_path):
    """Search for a task by title or goal."""
    project_path = Path(project_path).resolve()

    # Try all candidate catalogs
    catalog = None
    tasks_yaml = project_path / "tasks" / "TASKS.yaml"
    if not tasks_yaml.exists():
        tasks_yaml = project_path / ".clinerules" / "tasks" / "TASKS.yaml"

    if tasks_yaml.exists():
        from generator.planning.task_creator import TaskManifest

        catalog = TaskManifest.from_yaml(tasks_yaml).tasks
    else:
        # Try JSON
        tasks_json = project_path / "TASKS.json"
        if not tasks_json.exists():
            tasks_json = project_path / ".clinerules" / "TASKS.json"

        if tasks_json.exists():
            import json

            data = json.loads(tasks_json.read_text(encoding="utf-8"))
            catalog = data.get("tasks", [])

    if not catalog:
        click.echo("No tasks found to query.")
        return

    click.echo(f"Searching for '{search_term}'...")

    # Keyword overlap scoring (Simple Fallback)
    query_words = [w.lower() for w in search_term.split() if w]
    matches = []

    for t in catalog:
        # Handle both object and dict (YAML vs JSON)
        title = (getattr(t, "title", t.get("title") if isinstance(t, dict) else "") or "").lower()
        goal = (getattr(t, "goal", t.get("goal") if isinstance(t, dict) else "") or "").lower()

        # Calculate score: count keyword occurrences in title and goal
        score = 0
        for word in query_words:
            if word in title:
                score += 1.0
            if word in goal:
                score += 0.5  # Goal matches carry slightly less weight than title

        if score > 0:
            # Normalize score roughly for display (0.0 to 1.0 scale is hard with keywords, so we'll just show raw/count)
            # Actually, let's normalize by query length for a "similarity-ish" feel
            similarity = score / len(query_words) if query_words else 0
            matches.append((t, similarity))

    # Sort by similarity descending
    matches.sort(key=lambda x: x[1], reverse=True)

    if not matches:
        click.echo("No matching tasks found.")
        return

    best_task, best_score = matches[0]
    best_id = getattr(best_task, "id", best_task.get("id"))
    best_title = getattr(best_task, "title", best_task.get("title"))
    best_status = getattr(best_task, "status", best_task.get("status"))
    if hasattr(best_status, "value"):  # Enum
        best_status = best_status.value

    # Try to find file mapping (mostly for YAML/TASKS.yaml)
    best_file = getattr(best_task, "file", best_task.get("file", "N/A"))
    if best_file != "N/A" and not (best_file.startswith("tasks/") or best_file.startswith(".")):
        best_file = f"tasks/{best_file}"

    click.echo(f'\n🎯 Best Match: Task #{best_id} "{best_title}" ({best_score:.2f})')
    click.echo(f"Title: {best_title}")
    click.echo(f"Status: {best_status}")
    click.echo(f"File: {best_file}")

    click.echo(f"\n✅ Execute: prg exec {best_file}")

    # Show runners up if any
    if len(matches) > 1:
        click.echo("\nOther matches:")
        for t, score in matches[1:4]:
            tid = getattr(t, "id", t.get("id"))
            ttitle = getattr(t, "title", t.get("title"))
            click.echo(f"  - Task #{tid}: {ttitle} ({score:.2f})")


@click.command(name="leaderboard")
def leaderboard():
    """Open the Opik dashboard to see project metrics."""
    from generator.integrations.opik_client import OpikEvaluator

    click.echo("🚀 Opening Comet Opik Dashboard...")
    client = OpikEvaluator()
    url = client.get_dashboard_url()

    click.echo(f"Dashboard: {url}")
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        pass
