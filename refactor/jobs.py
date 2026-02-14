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
    tasks_yaml = project_path / "tasks" / "TASKS.yaml"

    # Prefer TASKS.yaml if it exists
    if tasks_yaml.exists():
        from generator.planning.task_creator import TaskManifest
        from generator.planning.task_executor import TaskExecutor

        manifest = TaskManifest.from_yaml(tasks_yaml)
        executor = TaskExecutor(manifest)
        summary = executor.get_progress_summary()

        click.echo(f"Task Progress: {manifest.task_description}")
        click.echo(f"{'=' * 50}")
        click.echo(
            f"Overall: {summary['done']}/{summary['total']} done ({summary['percent']}%)"
        )
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
            click.echo(
                f"  {icon} #{entry.id} {entry.title} (~{entry.estimated_minutes}m)"
            )

        nxt = executor.get_next_task()
        if nxt:
            click.echo(f"\\nNext: #{nxt.id} {nxt.title}")
            click.echo(f"  Run: prg exec tasks/{nxt.file}")
        elif summary["done"] == summary["total"]:
            click.echo("\\nAll tasks complete!")
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
