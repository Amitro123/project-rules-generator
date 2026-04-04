"""prg ralph — Manage the Ralph Feature Loop Engine."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import click

from cli.utils import detect_provider as _detect_provider
from cli.utils import set_api_key_env as _set_api_key

logger = logging.getLogger(__name__)


def _load_state_dict(feature_dir: Path) -> dict:
    state_path = feature_dir / "STATE.json"
    if not state_path.exists():
        raise click.ClickException(f"STATE.json not found in {feature_dir}. Did you run `prg feature`?")
    return json.loads(state_path.read_text(encoding="utf-8"))


def _feature_dir(project_path: Path, feature_id: str) -> Path:
    return project_path / "features" / feature_id


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


class _RalphGroup(click.Group):
    """Click group that runs a full feature lifecycle when given a task string."""

    def parse_args(self, ctx, args):
        # If the first arg doesn't match a known subcommand and doesn't start
        # with '-', treat it as a task description and route to `go`.
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["go"] + list(args)
        return super().parse_args(ctx, args)


@click.group(name="ralph", cls=_RalphGroup)
def ralph_group():
    """Ralph Feature Loop Engine — autonomous feature-scoped iteration.

    \b
    Quickstart (one command, full lifecycle):
      prg ralph "Add loading states to all forms"

    \b
    Sub-commands:
      go        Create feature + run loop immediately (default)
      discover  Scan project and queue multiple features
      run       Start loop for an existing FEATURE-XXX
      status    Show loop progress
      resume    Continue an interrupted loop
      stop      Emergency stop
      approve   Merge the feature branch → main
    """


# ---------------------------------------------------------------------------
# go  (default: prg ralph "task description")
# ---------------------------------------------------------------------------


@ralph_group.command(name="go")
@click.argument("task_description")
@click.option(
    "--project", "-p", "project_path",
    type=click.Path(exists=True, file_okay=False), default=".",
)
@click.option("--max-iterations", default=20, show_default=True)
@click.option("--provider", type=click.Choice(["gemini", "groq", "anthropic", "openai"]), default=None)
@click.option("--api-key", default=None)
@click.option("--verbose/--quiet", default=True)
def ralph_go(task_description, project_path, max_iterations, provider, api_key, verbose):
    """Create a feature and run its loop immediately — the one-command workflow.

    \b
    Example:
      prg ralph "Add loading states to all forms"
    """
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")

    from pathlib import Path as _Path

    from cli.feature_cmd import feature as _feature_cmd
    from cli.utils import detect_provider as _dp
    from cli.utils import set_api_key_env as _sk

    _dp_val = _dp(provider, api_key)
    _sk(_dp_val, api_key)

    proj = _Path(project_path).resolve()
    features_dir = proj / "features"

    from generator.ralph_engine import FeatureState, RalphEngine, _save_tasks, next_feature_id, slugify

    # 1. Create feature workspace (same logic as `prg feature`)
    feature_id = next_feature_id(features_dir)
    feature_dir = features_dir / feature_id
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "CRITIQUES").mkdir(exist_ok=True)

    click.echo(f"[ralph] Feature: {feature_id} — {task_description}")

    plan_path = feature_dir / "PLAN.md"
    tasks_path = feature_dir / "TASKS.yaml"
    tasks_total = 0

    try:
        from generator.task_decomposer import TaskDecomposer

        dec = TaskDecomposer(provider=_dp_val, api_key=api_key)
        subtasks = dec.decompose(task_description, project_path=proj)
        plan_path.write_text(dec.generate_plan_md(subtasks, user_task=task_description), encoding="utf-8")
        tasks_total = len(subtasks)
        _save_tasks(tasks_path, [
            {"id": s.id, "title": s.title, "status": "pending", "estimated_minutes": s.estimated_minutes}
            for s in subtasks
        ])
        click.echo(f"[ralph] Plan: {tasks_total} tasks")
    except Exception as exc:
        logger.warning("Plan generation failed: %s — placeholder written.", exc)
        plan_path.write_text(f"# {task_description}\n\nPlan generation failed. Edit manually.\n", encoding="utf-8")
        _save_tasks(tasks_path, [])

    branch_name = f"ralph/{feature_id}-{slugify(task_description)}"
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
        import subprocess as _sp

        _sp.run(["git", "checkout", "-b", branch_name], cwd=proj, check=True, capture_output=True)
        click.echo(f"[ralph] Branch: {branch_name}")
    except Exception as exc:
        logger.warning("Branch creation failed: %s", exc)

    # 2. Run the loop
    engine = RalphEngine(
        feature_id=feature_id,
        project_path=proj,
        provider=_dp_val or "groq",
        api_key=api_key,
        verbose=verbose,
    )
    engine.run_loop(max_iterations=max_iterations)


# ---------------------------------------------------------------------------
# discover  (manager replacement: prg ralph discover)
# ---------------------------------------------------------------------------


@ralph_group.command(name="discover")
@click.option(
    "--project", "-p", "project_path",
    type=click.Path(exists=True, file_okay=False), default=".",
)
@click.option("--provider", type=click.Choice(["gemini", "groq", "anthropic", "openai"]), default=None)
@click.option("--api-key", default=None)
@click.option(
    "--run/--no-run", "auto_run", default=False, show_default=True,
    help="Automatically start the Ralph loop for each discovered feature.",
)
@click.option("--verbose/--quiet", default=True)
def ralph_discover(project_path, provider, api_key, auto_run, verbose):
    """Scan the project and queue multiple Ralph features.

    Reads README.md and any spec files to extract a list of pending features,
    then calls 'prg feature' for each one. Pass --run to execute them in sequence.

    \b
    Replaces: prg manager
    Example:
      prg ralph discover
      prg ralph discover --run
    """
    import subprocess as _sp
    from pathlib import Path as _Path

    from cli.utils import detect_provider as _dp
    from cli.utils import set_api_key_env as _sk

    proj = _Path(project_path).resolve()
    _dp_val = _dp(provider, api_key)
    _sk(_dp_val, api_key)

    # Read project context
    readme = proj / "README.md"
    spec = proj / "spec.md"
    context = ""
    for p in (readme, spec):
        if p.exists():
            context += p.read_text(encoding="utf-8", errors="replace")[:3000] + "\n\n"

    if not context.strip():
        click.echo("No README.md or spec.md found — nothing to discover.", err=True)
        raise SystemExit(1)

    # Use TaskDecomposer to extract feature tasks from the README/spec
    features_found = []
    try:
        from generator.task_decomposer import TaskDecomposer

        dec = TaskDecomposer(provider=_dp_val, api_key=api_key)
        subtasks = dec.decompose(
            "Extract the list of pending features or improvements from this project context",
            project_path=proj,
        )
        features_found = [s.title for s in subtasks if s.title]
        click.echo(f"[discover] Found {len(features_found)} feature(s):")
        for f in features_found:
            click.echo(f"  • {f}")
    except Exception as exc:
        click.echo(f"[discover] AI extraction failed: {exc}", err=True)
        click.echo("[discover] Try: prg ralph \"<specific task>\" instead.")
        raise SystemExit(1)

    if not features_found:
        click.echo("[discover] No features identified.")
        return

    if not auto_run:
        click.echo("\nRun each feature with:")
        for f in features_found:
            click.echo(f'  prg ralph "{f}"')
        return

    # --run: execute each feature sequentially
    for f in features_found:
        click.echo(f"\n[discover] Starting: {f}")
        result = _sp.run(
            ["prg", "ralph", f],
            cwd=proj,
        )
        if result.returncode != 0:
            click.echo(f"[discover] Feature failed: {f} — stopping.", err=True)
            break


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@ralph_group.command(name="run")
@click.argument("feature_id")
@click.option(
    "--project",
    "-p",
    "project_path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project root directory",
)
@click.option("--max-iterations", default=None, type=int, help="Override max iterations from STATE.json")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
)
@click.option("--api-key", default=None)
@click.option("--verbose/--quiet", default=True)
def ralph_run(feature_id, project_path, max_iterations, provider, api_key, verbose):
    """Start the Ralph loop for FEATURE_ID.

    Example:

        prg ralph run FEATURE-001
    """
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")

    project_path = Path(project_path).resolve()
    fdir = _feature_dir(project_path, feature_id)
    state_dict = _load_state_dict(fdir)

    # Checkout the feature branch
    branch = state_dict.get("branch_name", f"ralph/{feature_id}")
    try:
        import subprocess

        subprocess.run(
            ["git", "checkout", branch],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
    except Exception as exc:
        click.echo(f"⚠️  Could not checkout branch {branch}: {exc}")

    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    from generator.ralph_engine import RalphEngine

    engine = RalphEngine(
        feature_id=feature_id,
        project_path=project_path,
        provider=provider or "groq",
        api_key=api_key,
        verbose=verbose,
    )
    engine.run_loop(max_iterations=max_iterations)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@ralph_group.command(name="status")
@click.argument("feature_id")
@click.option(
    "--project",
    "-p",
    "project_path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
)
def ralph_status(feature_id, project_path):
    """Show progress for FEATURE_ID."""
    project_path = Path(project_path).resolve()
    fdir = _feature_dir(project_path, feature_id)
    state = _load_state_dict(fdir)

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f"Ralph Status — {feature_id}", show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        for k, v in state.items():
            table.add_row(str(k), str(v))
        console.print(table)
    except ImportError:
        click.echo(f"\n[Ralph Status: {feature_id}]")
        for k, v in state.items():
            click.echo(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


@ralph_group.command(name="resume")
@click.argument("feature_id")
@click.option(
    "--project",
    "-p",
    "project_path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
)
@click.option("--max-iterations", default=None, type=int)
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
)
@click.option("--api-key", default=None)
@click.option("--verbose/--quiet", default=True)
def ralph_resume(feature_id, project_path, max_iterations, provider, api_key, verbose):
    """Continue an interrupted Ralph loop for FEATURE_ID."""
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")

    project_path = Path(project_path).resolve()
    fdir = _feature_dir(project_path, feature_id)
    state_dict = _load_state_dict(fdir)

    # Reset stopped status so the loop can re-enter
    if state_dict.get("status") in ("stopped",):
        from generator.ralph_engine import FeatureState

        state = FeatureState.load(fdir / "STATE.json")
        state.status = "running"
        state.exit_condition = None
        state.consecutive_test_failures = 0
        state.save(fdir / "STATE.json")
        click.echo(f"🔄 Cleared 'stopped' status for {feature_id} — resuming.")

    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    from generator.ralph_engine import RalphEngine

    engine = RalphEngine(
        feature_id=feature_id,
        project_path=project_path,
        provider=provider or "groq",
        api_key=api_key,
        verbose=verbose,
    )
    engine.run_loop(max_iterations=max_iterations)


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------


@ralph_group.command(name="stop")
@click.argument("feature_id")
@click.option(
    "--project",
    "-p",
    "project_path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
)
@click.option("--reason", default="user_requested", show_default=True, help="Reason for stopping")
def ralph_stop(feature_id, project_path, reason):
    """Emergency stop — save state and checkout main branch.

    Example:

        prg ralph stop FEATURE-001 --reason "scope changed"
    """
    project_path = Path(project_path).resolve()
    fdir = _feature_dir(project_path, feature_id)

    from generator.ralph_engine import FeatureState

    state = FeatureState.load(fdir / "STATE.json")
    state.status = "stopped"
    state.exit_condition = reason
    state.save(fdir / "STATE.json")
    click.echo(f"🛑 {feature_id} stopped. Reason: {reason}")

    # Checkout main/master
    try:
        import subprocess

        from prg_utils import git_ops

        for candidate in ("main", "master"):
            try:
                subprocess.run(
                    ["git", "checkout", candidate],
                    cwd=project_path,
                    check=True,
                    capture_output=True,
                )
                click.echo(f"🌿 Checked out {candidate}")
                break
            except Exception:
                continue
    except Exception as exc:
        click.echo(f"⚠️  Could not switch branch: {exc}")


# ---------------------------------------------------------------------------
# approve
# ---------------------------------------------------------------------------


@ralph_group.command(name="approve")
@click.argument("feature_id")
@click.option(
    "--project",
    "-p",
    "project_path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
)
@click.option("--target-branch", default="main", show_default=True, help="Branch to merge into")
def ralph_approve(feature_id, project_path, target_branch):
    """Merge the feature branch into TARGET_BRANCH and create a PR.

    Example:

        prg ralph approve FEATURE-001
    """
    project_path = Path(project_path).resolve()
    fdir = _feature_dir(project_path, feature_id)
    state_dict = _load_state_dict(fdir)
    branch = state_dict.get("branch_name", f"ralph/{feature_id}")
    task = state_dict.get("task", feature_id)

    try:
        import subprocess

        from prg_utils import git_ops

        git_ops.checkout(target_branch, project_path)
        git_ops.merge_branch(branch, project_path)
        click.echo(f"✅ Merged {branch} → {target_branch}")

        # Update state
        from generator.ralph_engine import FeatureState

        state = FeatureState.load(fdir / "STATE.json")
        state.status = "success"
        state.exit_condition = "human_approved"
        state.human_feedback = "approved"
        state.save(fdir / "STATE.json")

        # Try PR creation
        subprocess.run(
            [
                "gh", "pr", "create",
                "--title", f"Ralph: {task}",
                "--body", f"Approved by human. Feature: {feature_id}",
                "--head", branch,
                "--base", target_branch,
            ],
            cwd=project_path,
            capture_output=True,
        )
        click.echo("📬 PR created (if gh CLI is available).")
    except Exception as exc:
        click.echo(f"❌ Approval failed: {exc}", err=True)
