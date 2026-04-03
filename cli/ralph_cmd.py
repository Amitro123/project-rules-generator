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


@click.group(name="ralph")
def ralph_group():
    """Ralph Feature Loop Engine — autonomous feature-scoped iteration.

    \b
    Commands:
      run     Start the Ralph loop for a feature
      status  Show current loop progress
      resume  Continue an interrupted loop
      stop    Emergency stop
      approve Merge the feature branch → main
    """


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

        main = git_ops.get_current_branch(project_path)  # likely already on feature branch
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
