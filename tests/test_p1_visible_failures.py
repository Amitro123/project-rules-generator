"""Tests for P1: visible failure modes — warnings always on stderr, programming
errors propagate instead of being silently swallowed.

Covers:
- _phase_enhanced_parse: OSError/ValueError/RuntimeError → stderr warning + None
- _phase_enhanced_parse: AttributeError (programming error) → propagates
- _phase_enhanced_parse: warning emitted regardless of verbose flag
- READMEStrategy.generate(): narrowed catch still handles ImportError/ValueError
- cowork_strategy: TypeError on path coerce is caught and returns None
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# _phase_enhanced_parse
# ---------------------------------------------------------------------------


def test_enhanced_parse_oserror_emits_stderr_warning(tmp_path, capsys):
    """OSError during parsing: returns None and emits a warning to stderr."""
    from cli.analyze_pipeline import _phase_enhanced_parse

    with patch("cli.analyze_pipeline.EnhancedProjectParser") as mock_ep:
        mock_ep.return_value.extract_full_context.side_effect = OSError("disk read error")
        result = _phase_enhanced_parse(tmp_path, run_enhanced=True, verbose=False)

    assert result is None
    captured = capsys.readouterr()
    assert "Enhanced analysis failed" in captured.err
    assert "disk read error" in captured.err


def test_enhanced_parse_valueerror_emits_stderr_warning(tmp_path, capsys):
    """ValueError during parsing: returns None and emits a warning to stderr."""
    from cli.analyze_pipeline import _phase_enhanced_parse

    with patch("cli.analyze_pipeline.EnhancedProjectParser") as mock_ep:
        mock_ep.return_value.extract_full_context.side_effect = ValueError("malformed data")
        result = _phase_enhanced_parse(tmp_path, run_enhanced=True, verbose=False)

    assert result is None
    captured = capsys.readouterr()
    assert "Enhanced analysis failed" in captured.err


def test_enhanced_parse_runtimeerror_emits_stderr_warning(tmp_path, capsys):
    """RuntimeError during parsing: returns None and emits a warning to stderr."""
    from cli.analyze_pipeline import _phase_enhanced_parse

    with patch("cli.analyze_pipeline.EnhancedProjectParser") as mock_ep:
        mock_ep.return_value.extract_full_context.side_effect = RuntimeError("parser crashed")
        result = _phase_enhanced_parse(tmp_path, run_enhanced=True, verbose=False)

    assert result is None
    captured = capsys.readouterr()
    assert "Enhanced analysis failed" in captured.err


def test_enhanced_parse_warning_emitted_regardless_of_verbose(tmp_path, capsys):
    """The failure warning is emitted even when verbose=False.

    Before P1-A, this warning was only shown with --verbose, hiding failures
    from users running without the flag.
    """
    from cli.analyze_pipeline import _phase_enhanced_parse

    with patch("cli.analyze_pipeline.EnhancedProjectParser") as mock_ep:
        mock_ep.return_value.extract_full_context.side_effect = OSError("silent before P1")
        result = _phase_enhanced_parse(tmp_path, run_enhanced=True, verbose=False)

    assert result is None
    captured = capsys.readouterr()
    # Must appear in stderr even with verbose=False
    assert "Enhanced analysis failed" in captured.err
    assert captured.out == ""  # nothing on stdout


def test_enhanced_parse_attribute_error_propagates(tmp_path):
    """AttributeError (programming error in parser) must propagate, not be swallowed.

    Silent swallowing of AttributeError hides bugs in EnhancedProjectParser.
    """
    from cli.analyze_pipeline import _phase_enhanced_parse

    with patch("cli.analyze_pipeline.EnhancedProjectParser") as mock_ep:
        mock_ep.return_value.extract_full_context.side_effect = AttributeError("parser bug")
        with pytest.raises(AttributeError, match="parser bug"):
            _phase_enhanced_parse(tmp_path, run_enhanced=True, verbose=False)


def test_enhanced_parse_skipped_returns_none_no_warning(tmp_path, capsys):
    """When run_enhanced=False (incremental skip), returns None with no stderr warning."""
    from cli.analyze_pipeline import _phase_enhanced_parse

    result = _phase_enhanced_parse(tmp_path, run_enhanced=False, verbose=False)

    assert result is None
    captured = capsys.readouterr()
    assert "Enhanced analysis failed" not in captured.err


def test_enhanced_parse_success_returns_context(tmp_path):
    """Happy path: returns the context dict from EnhancedProjectParser."""
    from cli.analyze_pipeline import _phase_enhanced_parse

    expected = {"tech_stack": ["python"], "structure": {}}
    with patch("cli.analyze_pipeline.EnhancedProjectParser") as mock_ep:
        mock_ep.return_value.extract_full_context.return_value = expected
        result = _phase_enhanced_parse(tmp_path, run_enhanced=True, verbose=False)

    assert result == expected


# ---------------------------------------------------------------------------
# READMEStrategy — narrowed catch still handles expected failure modes
# ---------------------------------------------------------------------------


def test_readme_strategy_importerror_returns_none(tmp_path):
    """ImportError from the readme_parser module falls back gracefully.

    extract_purpose is imported inside the function body, so we make the
    whole module import fail via sys.modules injection.
    """
    import sys

    from generator.strategies.readme_strategy import READMEStrategy

    strategy = READMEStrategy()
    # Temporarily hide the readme_parser module to trigger ImportError
    real_module = sys.modules.pop("generator.analyzers.readme_parser", None)
    try:
        sys.modules["generator.analyzers.readme_parser"] = None  # type: ignore[assignment]
        result = strategy.generate(
            skill_name="my-skill",
            from_readme="# My Project\nDoes things.",
            project_path=tmp_path,
            provider="groq",
        )
    finally:
        if real_module is not None:
            sys.modules["generator.analyzers.readme_parser"] = real_module
        else:
            sys.modules.pop("generator.analyzers.readme_parser", None)
    assert result is None


def test_readme_strategy_valueerror_returns_none(tmp_path):
    """ValueError during parsing falls back gracefully."""
    from generator.strategies.readme_strategy import READMEStrategy

    strategy = READMEStrategy()
    # Patch at the source module since the import happens inside the function
    with patch(
        "generator.analyzers.readme_parser.extract_purpose",
        side_effect=ValueError("bad data"),
    ):
        result = strategy.generate(
            skill_name="my-skill",
            from_readme="# My Project\nDoes things.",
            project_path=tmp_path,
            provider="groq",
        )
    assert result is None


# ---------------------------------------------------------------------------
# CoworkStrategy — TypeError on path coerce is caught
# ---------------------------------------------------------------------------


def test_cowork_strategy_invalid_path_type_returns_none():
    """Non-path, non-string project_path triggers TypeError which is caught."""
    from generator.strategies.cowork_strategy import CoworkStrategy

    strategy = CoworkStrategy()
    # Pass an object that Path() cannot coerce
    result = strategy.generate(
        skill_name="my-skill",
        project_path=12345,  # int — Path(12345) raises TypeError
        provider="groq",
        from_readme="# My Project",
        use_ai=False,
    )
    assert result is None
