"""prg watch — live mode: auto-reanalyze on file changes."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional

import click
import pathspec

# Files that trigger a re-analyze when modified or created
WATCH_FILES = {
    "README.md",
    "README.rst",
    "README.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-llm.txt",
    ".env",
    ".gitignore",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
    "Gemini.md",
    "CLAUDE.md",
}

# Directory name prefixes that trigger on any new file inside them
WATCH_DIRS = {"tests", "test", "spec"}

# Paths to always ignore (gitignore-like noise filter)
_IGNORE_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".clinerules",
    ".claude",
}


def _load_gitignore_spec(project_path: Path):
    """Load .gitignore patterns using pathspec (returns None if unavailable)."""
    try:
        import pathspec

        gitignore = project_path / ".gitignore"
        if gitignore.exists():
            return pathspec.PathSpec.from_lines("gitignore", gitignore.read_text(encoding="utf-8").splitlines())
    except Exception:
        pass
    return None


def _should_trigger(path: str, project_path: Path, gitignore_spec=None) -> bool:
    """Return True if the changed file should trigger a re-analyze."""
    try:
        rel = Path(path).relative_to(project_path)
    except ValueError:
        return False

    parts = rel.parts
    name = rel.name

    # Always ignore known noise directories
    if parts and parts[0] in _IGNORE_DIRS:
        return False

    # Filter via .gitignore patterns
    if gitignore_spec and gitignore_spec.match_file(str(rel)):
        return False

    # Top-level watched files
    if len(parts) == 1 and name in WATCH_FILES:
        return True

    # Files inside watched directories (tests/, test/, spec/)
    if parts and parts[0].lower() in WATCH_DIRS:
        return True

    # Common test file patterns anywhere in the tree
    stem = Path(name).stem
    if stem.startswith("test_") or stem.endswith("_test") or name.endswith(".spec.ts") or name.endswith(".test.ts"):
        return True

    return False


class _PRGHandler:
    """Watchdog event handler with debounce and dirty-bit re-run logic.

    Bug fixes vs. v1:
    - Issue #1 (race condition): replaced _running bool with dirty-bit system.
      If a change arrives while an analysis is running, _needs_rerun is set so
      one final run executes after the current one completes — no drops.
    - Issue #2 (gitignore): gitignore_spec is loaded once and passed to _should_trigger.
    - Issue #3 (lock files): handled in WATCH_FILES constant above.
    - Issue #4 (moved/deleted): on_change() is called for all event types.
    """

    def __init__(
        self,
        project_path: Path,
        delay: float,
        extra_args: List[str],
        verbose: bool,
        gitignore_spec=None,
    ):
        self._project_path = project_path
        self._delay = delay
        self._extra_args = extra_args
        self._verbose = verbose
        self._gitignore_spec = gitignore_spec
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self._needs_rerun = False
        self._lock = threading.Lock()

    def on_change(self, path: str) -> None:
        """Called by the observer thread when a file change is detected."""
        if not _should_trigger(path, self._project_path, self._gitignore_spec):
            return
        if self._verbose:
            try:
                rel = Path(path).relative_to(self._project_path)
            except ValueError:
                rel = path  # type: ignore[assignment]
            click.echo(f"[watch] Changed: {rel}")
        with self._lock:
            if self._running:
                # Analysis in progress — set dirty bit so we re-run after it finishes
                self._needs_rerun = True
                return
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._trigger)
            self._timer.daemon = True
            self._timer.start()

    def _trigger(self) -> None:
        while True:
            with self._lock:
                self._running = True
                self._needs_rerun = False

            try:
                click.echo("[watch] Running incremental analysis...")
                cmd = [sys.executable, "-m", "cli.cli", "analyze", str(self._project_path), "--incremental"]
                cmd.extend(self._extra_args)
                result = subprocess.run(cmd, capture_output=False)
                if result.returncode != 0 and self._verbose:
                    click.echo(f"[watch] analyze exited with code {result.returncode}", err=True)
                else:
                    click.echo("[watch] Done.")
            except Exception as e:
                click.echo(f"[watch] Error during analysis: {e}", err=True)
            finally:
                with self._lock:
                    if not self._needs_rerun:
                        self._running = False
                        return
                    # Another change arrived while we were running
                    self._needs_rerun = False
                    if self._verbose:
                        click.echo("[watch] Change detected during run — re-running...")

    def cancel(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()


@click.command(name="watch")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--delay", default=2.0, type=float, show_default=True, help="Debounce delay in seconds.")
@click.option(
    "--ide",
    type=click.Choice(["antigravity", "cursor", "windsurf", "vscode", "none"]),
    default=None,
    help="IDE target (passed to analyze).",
)
@click.option("--quiet", is_flag=True, default=False, help="Suppress change notifications.")
def watch(project_path: str, delay: float, ide: Optional[str], quiet: bool) -> None:
    """Watch project files and auto-run 'prg analyze --incremental' on changes.

    Monitors README, pyproject.toml, lock files, requirements, Dockerfile,
    and test directories. Respects .gitignore to skip noise. Press Ctrl+C to stop.
    """
    try:
        from watchdog.events import FileSystemEvent, FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        click.echo("Error: watchdog is required for watch mode.", err=True)
        click.echo("Install it with:  pip install watchdog", err=True)
        raise SystemExit(1)

    path = Path(project_path).resolve()
    verbose = not quiet
    gitignore_spec = _load_gitignore_spec(path)

    extra_args: List[str] = []
    if ide:
        extra_args += ["--ide", ide]

    handler_obj = _PRGHandler(path, delay, extra_args, verbose, gitignore_spec)

    class _EventBridge(FileSystemEventHandler):
        def on_modified(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                handler_obj.on_change(event.src_path)

        def on_created(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                handler_obj.on_change(event.src_path)

        def on_deleted(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                handler_obj.on_change(event.src_path)

        def on_moved(self, event: FileSystemEvent) -> None:
            # Both source and destination may be relevant
            if not event.is_directory:
                handler_obj.on_change(event.src_path)
                handler_obj.on_change(event.dest_path)

    observer = Observer()
    observer.schedule(_EventBridge(), str(path), recursive=True)
    observer.start()

    gitignore_note = " (respecting .gitignore)" if gitignore_spec else ""
    click.echo(f"[watch] Watching {path}{gitignore_note}  (delay={delay}s, Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        handler_obj.cancel()
        observer.stop()
        observer.join()
        click.echo("[watch] Stopped.")
