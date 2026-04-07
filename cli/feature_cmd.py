"""prg feature — Set up a new Ralph feature folder, plan, and branch."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from cli.utils import detect_provider as _detect_provider
from cli.utils import has_api_key as _has_api_key
from cli.utils import set_api_key_env as _set_api_key
from prg_utils.git_ops import is_git_repo

logger = logging.getLogger(__name__)


def _create_feature_workspace(
    proj: Path,
    task_description: str,
    max_iterations: int,
    provider: str,
    api_key,
    verbose: bool = False,
):
    """Allocate a feature directory, generate plan, write STATE.json, create branch.

    Returns (feature_id, feature_dir, tasks_total).
    Raises ClickException on unrecoverable errors (e.g. retries exhausted).
    """
    from generator.ralph_engine import FeatureState, _save_tasks, next_feature_id, slugify

    features_dir = proj / "features"
    features_dir.mkdir(parents=True, exist_ok=True)

    for _attempt in range(5):
        feature_id = next_feature_id(features_dir)
        feature_dir = features_dir / feature_id
        try:
            feature_dir.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise click.ClickException("Could not allocate a unique feature directory after 5 retries.")

    (feature_dir / "CRITIQUES").mkdir(exist_ok=True)

    plan_path = feature_dir / "PLAN.md"
    tasks_path = feature_dir / "TASKS.yaml"
    tasks_total = 0

    try:
        from generator.task_decomposer import TaskDecomposer

        has_key = _has_api_key(provider, api_key)
        if not has_key and verbose:
            click.echo(
                "   ⚠️  No API key found — PLAN.md will be a generic template scaffold.\n"
                "   Set GEMINI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY for\n"
                "   a project-specific plan.",
            )
        decomposer = TaskDecomposer(provider=provider, api_key=api_key)
        subtasks = decomposer.decompose(task_description, project_path=proj)
        plan_path.write_text(
            decomposer.generate_plan_md(subtasks, user_task=task_description, is_template=not has_key),
            encoding="utf-8",
        )
        tasks_total = len(subtasks)
        _save_tasks(
            tasks_path,
            [
                {"id": s.id, "title": s.title, "status": "pending", "estimated_minutes": s.estimated_minutes}
                for s in subtasks
            ],
        )
    except Exception as exc:
        logger.warning("Plan generation failed: %s — writing placeholder.", exc)
        plan_path.write_text(
            f"# {task_description}\n\nPlan generation failed. Edit manually.\n", encoding="utf-8"
        )
        _save_tasks(tasks_path, [])

    slug = slugify(task_description)
    if not slug:
        raise click.UsageError("Task description must contain at least one alphanumeric character.")
    branch_name = f"ralph/{feature_id}-{slug}"

    state = FeatureState(
        feature_id=feature_id,
        task=task_description,
        branch_name=branch_name,
        status="planning_complete",
        tasks_total=tasks_total,
        max_iterations=max_iterations,
    )
    state.save(feature_dir / "STATE.json")

    try:
        import subprocess

        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=proj,
            check=True,
            capture_output=True,
            timeout=30,
        )
    except Exception as exc:
        logger.warning("Branch creation failed: %s", exc)

    return feature_id, feature_dir, tasks_total


@click.command(name="feature")
@click.argument("task_description")
@click.option(
    "--project",
    "-p",
    "project_path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project root directory (default: .)",
)
@click.option(
    "--max-iterations",
    default=20,
    show_default=True,
    help="Maximum loop iterations for this feature",
)
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI provider for plan generation",
)
@click.option("--api-key", default=None, help="API key (overrides env var)")
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def feature(task_description, project_path, max_iterations, provider, api_key, verbose):
    """Set up a new Ralph feature: plan, STATE.json, and git branch.

    Example:

        prg feature "Add loading states to forms"
    """
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING, format="%(message)s")

    project_path = Path(project_path).resolve()

    if not is_git_repo(project_path):
        raise click.ClickException(
            f"{project_path} is not a git repository.\n"
            "Ralph requires git for branch isolation and PR creation.\n"
            "Run `git init` first, or point --project at a git repo."
        )

    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    if verbose:
        click.echo("📝 Generating plan…")

    feature_id, feature_dir, tasks_total = _create_feature_workspace(
        proj=project_path,
        task_description=task_description,
        max_iterations=max_iterations,
        provider=provider,
        api_key=api_key,
        verbose=verbose,
    )

    click.echo(f"🆕 Feature ID: {feature_id}")
    if tasks_total:
        click.echo(f"   ✅ PLAN.md ({tasks_total} tasks)")
    click.echo("   ✅ STATE.json")
    click.echo(f"\n🎉 Feature ready! Start the loop with:\n\n    prg ralph run {feature_id}\n")
