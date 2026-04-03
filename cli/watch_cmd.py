"""prg watch — live mode: auto-reanalyze on file changes."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional

import click

# Files that trigger a re-analyze when modified or created
WATCH_FILES = {
    "README.md",
    "README.rst",
    "README.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-llm.txt",
    ".env",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
}

# Directory name prefixes that trigger on any new file inside them
WATCH_DIRS = {"tests", "test", "spec"}


def _should_trigger(path: str, project_path: Path) -> bool:
    """Return True if the changed file should trigger a re-analyze."""
    try:
        rel = Path(path).relative_to(project_path)
    except ValueError:
        return False

    parts = rel.parts
    name = rel.name

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
    """Watchdog-style event handler with debounce and re-entry guard."""

    def __init__(
        self,
        project_path: Path,
        delay: float,
        extra_args: List[str],
        verbose: bool,
    ):
        self._project_path = project_path
        self._delay = delay
        self._extra_args = extra_args
        self._verbose = verbose
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self._lock = threading.Lock()

    def on_change(self, path: str) -> None:
        """Called by the observer thread when a file change is detected."""
        if not _should_trigger(path, self._project_path):
            return
        if self._verbose:
            rel = Path(path).relative_to(self._project_path) if Path(path).is_relative_to(self._project_path) else path
            click.echo(f"[watch] Changed: {rel}")
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._trigger)
            self._timer.daemon = True
            self._timer.start()

    def _trigger(self) -> None:
        with self._lock:
            if self._running:
                if self._verbose:
                    click.echo("[watch] Already running, skipping.")
                return
            self._running = True
        try:
            click.echo("[watch] Running: prg analyze --incremental ...")
            cmd = [sys.executable, "-m", "cli.cli", "analyze", str(self._project_path), "--incremental"]
            cmd.extend(self._extra_args)
            result = subprocess.run(cmd, capture_output=False)
            if result.returncode != 0 and self._verbose:
                click.echo(f"[watch] analyze exited with code {result.returncode}", err=True)
            else:
                click.echo("[watch] Done.")
        finally:
            with self._lock:
                self._running = False

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

    Monitors README, pyproject.toml, requirements files, and test directories.
    Press Ctrl+C to stop.
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

    extra_args: List[str] = []
    if ide:
        extra_args += ["--ide", ide]

    handler_obj = _PRGHandler(path, delay, extra_args, verbose)

    class _EventBridge(FileSystemEventHandler):
        def on_modified(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                handler_obj.on_change(event.src_path)

        def on_created(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                handler_obj.on_change(event.src_path)

    observer = Observer()
    observer.schedule(_EventBridge(), str(path), recursive=True)
    observer.start()

    click.echo(f"[watch] Watching {path}  (delay={delay}s, Ctrl+C to stop)")

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
