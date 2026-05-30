"""Regression tests for the ``--ide`` flag on ``prg analyze``.

Code-review finding (Tier-2 #8): ``prg analyze . --ide cursor`` (or windsurf /
vscode) was *silently accepted as a no-op* — the "not supported" warning was
gated behind ``--verbose``, and the flag itself accepted any free-form string
while ``prg watch`` already restricted it to ``Choice(['antigravity', 'none'])``.

These tests lock in the resolution:
  * ``--ide`` is a restricted ``click.Choice`` consistent with ``prg watch``.
  * The registration helper never fails silently for an unsupported IDE.
"""

from __future__ import annotations

import click

from cli.analyze_cmd import _register_ide_rules, analyze


def _ide_param() -> click.Parameter:
    return next(p for p in analyze.params if p.name == "ide")


def test_ide_flag_is_restricted_choice() -> None:
    """--ide must be a click.Choice limited to the IDEs we actually support,
    matching ``prg watch`` (which already used Choice(['antigravity', 'none']))."""
    param = _ide_param()
    assert isinstance(param.type, click.Choice)
    assert set(param.type.choices) == {"antigravity", "none"}


def test_register_antigravity_writes_agents_file(tmp_path) -> None:
    output_dir = tmp_path / ".clinerules"
    output_dir.mkdir()
    (output_dir / "rules.md").write_text("# rules", encoding="utf-8")

    dest = _register_ide_rules("antigravity", tmp_path, "myproj", output_dir, verbose=False)

    assert dest == tmp_path / ".agents" / "rules" / "myproj.md"
    assert dest.read_text(encoding="utf-8") == "# rules"


def test_register_none_skips_without_writing(tmp_path) -> None:
    output_dir = tmp_path / ".clinerules"
    output_dir.mkdir()

    result = _register_ide_rules("none", tmp_path, "myproj", output_dir, verbose=False)

    assert result is None
    assert not (tmp_path / ".agents").exists()


def test_register_unsupported_ide_warns_even_without_verbose(tmp_path, capsys) -> None:
    """The original bug: unsupported IDEs were a silent no-op unless --verbose.
    The warning must now appear even with verbose=False and tell the user what
    to do instead."""
    output_dir = tmp_path / ".clinerules"
    output_dir.mkdir()

    result = _register_ide_rules("cursor", tmp_path, "myproj", output_dir, verbose=False)

    assert result is None
    out = capsys.readouterr().out
    assert "cursor" in out
    assert ".clinerules" in out  # points the user at the manual fallback
