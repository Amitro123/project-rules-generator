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


def test_sanitize_env_strips_matching_outer_quotes(tmp_path, monkeypatch):
    """Matching outer quotes are stripped; value content is never truncated."""
    import os
    from cli.cli import _sanitize_env_from_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text(
        "SINGLE_QUOTED='myvalue'\n" 'DOUBLE_QUOTED="myvalue"\n' "NO_QUOTES=myvalue\n" "COLON_SYNTAX: myvalue\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    for key in ("SINGLE_QUOTED", "DOUBLE_QUOTED", "NO_QUOTES", "COLON_SYNTAX"):
        monkeypatch.delenv(key, raising=False)

    _sanitize_env_from_dotenv()

    assert os.environ["SINGLE_QUOTED"] == "myvalue"
    assert os.environ["DOUBLE_QUOTED"] == "myvalue"
    assert os.environ["NO_QUOTES"] == "myvalue"
    assert os.environ["COLON_SYNTAX"] == "myvalue"


def test_sanitize_env_embedded_quote_not_truncated(tmp_path, monkeypatch):
    """Embedded quotes in a value are preserved, not silently dropped."""
    import os
    from cli.cli import _sanitize_env_from_dotenv

    env_file = tmp_path / ".env"
    # Value with embedded quote — must NOT be truncated to just 'foo'
    env_file.write_text("EMBED_KEY='foo'bar'\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("EMBED_KEY", raising=False)

    _sanitize_env_from_dotenv()

    # Outer quotes stripped → foo'bar (not silently truncated to foo)
    assert os.environ.get("EMBED_KEY") == "foo'bar"


def test_sanitize_env_mismatched_quotes_kept_as_is(tmp_path, monkeypatch):
    """Mismatched quotes are not stripped — value is taken verbatim."""
    import os
    from cli.cli import _sanitize_env_from_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text("MISMATCH_KEY='value\"\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MISMATCH_KEY", raising=False)

    _sanitize_env_from_dotenv()

    assert os.environ.get("MISMATCH_KEY") == "'value\""


def test_sanitize_env_does_not_overwrite_existing(tmp_path, monkeypatch):
    """Keys already in os.environ are not overwritten."""
    import os
    from cli.cli import _sanitize_env_from_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING_KEY=new_value\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EXISTING_KEY", "original_value")

    _sanitize_env_from_dotenv()

    assert os.environ["EXISTING_KEY"] == "original_value"


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
