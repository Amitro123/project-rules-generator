import logging
import sys


def ensure_utf8_streams() -> None:
    """Force sys.stdout/stderr to UTF-8 on Windows.

    Windows consoles default to cp1252, which crashes on emoji/astral chars
    that appear in logger output (e.g. generator/ralph/engine.py uses
    "🚀", "✅", "📊"). Calling this from any entry point that may emit
    such chars — CLI, test runner, library consumer — is safe and
    idempotent. On non-Windows or pre-3.7 Python it is a no-op.

    Separate from setup_logging() so library consumers that already
    configure their own logging can still get the encoding fix.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)  # UTF-8 codepage
    except (AttributeError, OSError):
        pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass


def setup_logging(verbose: bool = False):
    """Configure the root logger."""
    level = logging.DEBUG if verbose else logging.INFO

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Create formatter
    # Using a simple format for CLI friendliness
    formatter = logging.Formatter("%(levelname)s: %(name)s - %(message)s")
    handler.setFormatter(formatter)

    # Configure root logger
    root = logging.getLogger("project_rules_generator")
    root.setLevel(level)

    # Avoid duplicate handlers
    if not root.handlers:
        root.addHandler(handler)

    # Set external libraries to warning to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
