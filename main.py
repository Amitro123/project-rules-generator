"""CLI orchestrator for project rules and skills generator."""

import sys

if sys.platform == "win32":
    # type: ignore # reconfigure is valid on TextIOWrapper but mypy sees TextIO
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
from pathlib import Path

root_dir = Path(__file__).parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from refactor.analyze_cmd import load_config

# Redirect to refactored CLI
from refactor.cli import cli

# Expose click command object as `main` for tests expecting a Click command
main = cli

if __name__ == "__main__":
    cli()
