"""Entry point for `python main.py` and legacy script invocations."""

import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

from cli.cli import main

if __name__ == "__main__":
    main()
