"""Tests for generator.interactive — the user-facing README prompt flow and the
generated-files summary renderer.

These two functions are the interactive front door (``prg`` asks the user four
questions, then prints a success table). They were previously at 0% coverage
(CR §4.4). We drive ``create_readme_interactive`` by scripting ``Prompt.ask`` and
assert the returned dict; we capture the rich console to assert the summary
renderer's name→purpose mapping and per-stat skill breakdown branches.
"""

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

import generator.interactive as interactive

# ─── create_readme_interactive ────────────────────────────────────────────────


class TestCreateReadmeInteractive:
    """The four-question interactive README flow."""

    def _run(self, answers, project_path):
        """Invoke create_readme_interactive with ``Prompt.ask`` scripted to
        return ``answers`` in order.

        ``sys.stdin`` is patched because the function calls ``sys.stdin.flush()``
        to drain buffered input, and pytest's captured stdin raises
        ``UnsupportedOperation`` on flush.
        """
        with patch.object(interactive.Prompt, "ask", side_effect=answers), patch("sys.stdin"):
            return interactive.create_readme_interactive(project_path)

    def test_returns_all_expected_keys(self, tmp_path):
        """The result dict carries every key the README templates rely on."""
        result = self._run(
            ["MyProj", "Does things", "Solves X", "python,fastapi"],
            tmp_path,
        )
        assert set(result) == {
            "name",
            "description",
            "purpose",
            "problem",
            "tech_stack",
            "features",
        }

    def test_maps_problem_to_purpose_and_problem(self, tmp_path):
        """The single 'problem' answer feeds both ``purpose`` and ``problem``
        (template compatibility shim)."""
        result = self._run(
            ["MyProj", "Desc", "Solve world hunger", "python"],
            tmp_path,
        )
        assert result["purpose"] == "Solve world hunger"
        assert result["problem"] == "Solve world hunger"

    def test_tech_stack_parsed_into_clean_list(self, tmp_path):
        """Comma-separated tech is split, stripped, and emptied entries dropped."""
        result = self._run(
            ["MyProj", "Desc", "Problem", " fastapi , python ,, postgresql "],
            tmp_path,
        )
        assert result["tech_stack"] == ["fastapi", "python", "postgresql"]

    def test_answers_are_stripped(self, tmp_path):
        """Leading/trailing whitespace on free-text answers is trimmed."""
        result = self._run(
            ["  Padded Name  ", "  spacey desc  ", "  problem  ", "python"],
            tmp_path,
        )
        assert result["name"] == "Padded Name"
        assert result["description"] == "spacey desc"

    def test_features_key_is_always_empty_string(self, tmp_path):
        """``features`` is seeded empty so downstream templates never KeyError."""
        result = self._run(["N", "D", "P", "python"], tmp_path)
        assert result["features"] == ""

    def test_empty_tech_stack_yields_empty_list(self, tmp_path):
        """An all-whitespace tech answer parses to an empty list, not ['']."""
        result = self._run(["N", "D", "P", "   "], tmp_path)
        assert result["tech_stack"] == []


# ─── show_generated_files ─────────────────────────────────────────────────────


@pytest.fixture
def captured_console(monkeypatch):
    """Swap the module console for a StringIO-backed one and return a getter."""
    buf = io.StringIO()
    test_console = Console(file=buf, force_terminal=False, width=200)
    monkeypatch.setattr(interactive, "console", test_console)
    return buf


class TestShowGeneratedFiles:
    """The success summary table + skills breakdown renderer."""

    def test_renders_file_purposes_for_known_names(self, captured_console):
        """Each recognised filename gets its descriptive purpose in the table."""
        files = [
            Path(".clinerules"),
            Path("project-rules.md"),
            Path("project-skills.md"),
            Path("skills.json"),
            Path("skills.yaml"),
            Path("README.md"),
        ]
        interactive.show_generated_files(files, {})
        out = captured_console.getvalue()

        assert "Files Generated" in out
        assert "AI agents auto-load" in out
        assert "Human-readable project guidelines" in out
        assert "Detailed skills library reference" in out
        assert "Skills export (JSON)" in out
        assert "Skills export (YAML)" in out
        assert "Project documentation" in out

    def test_unknown_filename_falls_back_to_unknown_purpose(self, captured_console):
        """A filename matching none of the branches renders 'Unknown'."""
        interactive.show_generated_files([Path("mystery.txt")], {})
        assert "Unknown" in captured_console.getvalue()

    def test_all_skill_stats_branches_render(self, captured_console):
        """Positive learned/builtin/generated counts each emit their line."""
        interactive.show_generated_files(
            [Path("README.md")],
            {"learned": 3, "builtin": 5, "generated": 2},
        )
        out = captured_console.getvalue()
        assert "3" in out and "LEARNED" in out
        assert "5" in out and "BUILTIN" in out
        assert "2" in out and "newly generated" in out

    def test_zero_counts_suppress_skill_lines(self, captured_console):
        """Zero counts skip their branch — no LEARNED/BUILTIN/generated lines."""
        interactive.show_generated_files(
            [Path("README.md")],
            {"learned": 0, "builtin": 0, "generated": 0},
        )
        out = captured_console.getvalue()
        assert "LEARNED" not in out
        assert "BUILTIN" not in out
        assert "newly generated" not in out

    def test_missing_stats_keys_are_safe(self, captured_console):
        """An empty stats dict (no keys) renders without raising."""
        interactive.show_generated_files([Path("README.md")], {})
        out = captured_console.getvalue()
        # Next-steps footer always prints regardless of stats.
        assert "Next steps" in out
