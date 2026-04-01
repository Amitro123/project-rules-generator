"""Entry point shim — real logic lives in cli/cli.py."""

import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

from cli.cli import cli  # noqa: F401 — re-exported for tests
from cli.cli import main as _entry  # noqa: F401

# Tests use CliRunner().invoke(main) — expose the Click group under that name
main = cli

if __name__ == "__main__":
    _entry()
