# ruff: noqa: E402
"""Entry point shim — real logic lives in cli/cli.py."""

import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

root_dir = Path(__file__).parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from cli.cli import cli  # noqa: E402 — path must be set first
from cli.cli import main as _cli_main  # noqa: E402

# Expose Click group as `main` for backward compat (tests use CliRunner().invoke(main))
main = cli

if __name__ == "__main__":
    _cli_main()
