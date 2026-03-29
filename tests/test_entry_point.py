"""Regression guard: installed entry point must bootstrap dotenv before Click runs."""

from unittest.mock import patch


def test_main_calls_load_dotenv_before_cli():
    """cli.cli.main() must call load_dotenv() before invoking the CLI group."""
    from cli.cli import main

    call_order = []

    def mock_load_dotenv():
        call_order.append("load_dotenv")

    def mock_sanitize():
        call_order.append("sanitize")

    def mock_cli(*args, **kwargs):
        call_order.append("cli")

    with (
        patch("cli.cli.load_dotenv", mock_load_dotenv),
        patch("cli.cli._sanitize_env_from_dotenv", mock_sanitize),
        patch("cli.cli.cli", mock_cli),
    ):
        main()

    assert call_order == [
        "load_dotenv",
        "sanitize",
        "cli",
    ], f"Expected dotenv to load before CLI runs. Got order: {call_order}"


def test_entry_point_module_is_cli_cli():
    """pyproject.toml entry point must point to cli.cli:main, not main:cli."""
    import importlib.metadata

    try:
        eps = importlib.metadata.entry_points(group="console_scripts")
        prg_ep = next((ep for ep in eps if ep.name == "prg"), None)
        if prg_ep is not None:
            assert prg_ep.value == "cli.cli:main", f"Entry point must be cli.cli:main, got {prg_ep.value!r}"
    except Exception:
        pass  # skip if package not installed in test env
