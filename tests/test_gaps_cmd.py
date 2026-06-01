"""Tests for the ``prg gaps`` and ``prg spec`` commands (cli/gaps_cmd.py).

These commands were at 34% coverage (CR §4.4). Both require an AI provider and
collaborate with the requirements inferrer, the task manifest, and a
traceability matrix. We mock those collaborators so the branch logic — API-key
gating, spec parsing, gap reporting, and spec generation — is exercised without
network access.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.gaps_cmd import _generate_spec_with_llm, gaps, spec_cmd
from generator.requirements import Requirement

# ─── prg gaps ─────────────────────────────────────────────────────────────────


class TestGapsCommand:
    def test_missing_api_key_aborts_with_exit_1(self, tmp_path):
        """No provider key → clear error on stderr and exit code 1."""
        with (
            patch("cli.gaps_cmd._detect_provider", return_value="gemini"),
            patch("cli.gaps_cmd._set_api_key"),
            patch("cli.gaps_cmd._has_api_key", return_value=False),
        ):
            result = CliRunner().invoke(gaps, [str(tmp_path)])

        assert result.exit_code == 1
        assert "requires an AI provider API key" in result.output

    def test_no_manifest_reports_run_tasks_first(self, tmp_path):
        """With a key but no tasks/TASKS.yaml → guidance to run 'prg tasks'."""
        with (
            patch("cli.gaps_cmd._detect_provider", return_value="gemini"),
            patch("cli.gaps_cmd._set_api_key"),
            patch("cli.gaps_cmd._has_api_key", return_value=True),
            patch("cli.gaps_cmd.RequirementsInferrer") as inf_cls,
        ):
            inf_cls.return_value.infer.return_value = []
            result = CliRunner().invoke(gaps, [str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "No TASKS.yaml found" in result.output

    def _setup_manifest(self, tmp_path):
        """Create a placeholder tasks/TASKS.yaml so the existence check passes."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "TASKS.yaml").write_text("tasks: []\n")

    def test_reports_missing_requirements(self, tmp_path):
        """Gaps found by the matrix are listed with id + description."""
        self._setup_manifest(tmp_path)
        gap = MagicMock(id="R1", description="Login flow not covered")

        with (
            patch("cli.gaps_cmd._detect_provider", return_value="gemini"),
            patch("cli.gaps_cmd._set_api_key"),
            patch("cli.gaps_cmd._has_api_key", return_value=True),
            patch("cli.gaps_cmd.RequirementsInferrer") as inf_cls,
            patch("cli.gaps_cmd.TaskManifest") as manifest_cls,
            patch("cli.gaps_cmd.TraceabilityMatrix") as matrix_cls,
        ):
            inf_cls.return_value.infer.return_value = []
            manifest_cls.from_yaml.return_value.tasks = []
            matrix = matrix_cls.return_value
            matrix.format_table.return_value = "| matrix |"
            matrix.get_gaps.return_value = [gap]
            result = CliRunner().invoke(gaps, [str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "Found 1 missing requirements" in result.output
        assert "[R1] Login flow not covered" in result.output

    def test_reports_full_coverage(self, tmp_path):
        """No gaps from the matrix → 100% coverage message."""
        self._setup_manifest(tmp_path)

        with (
            patch("cli.gaps_cmd._detect_provider", return_value="gemini"),
            patch("cli.gaps_cmd._set_api_key"),
            patch("cli.gaps_cmd._has_api_key", return_value=True),
            patch("cli.gaps_cmd.RequirementsInferrer") as inf_cls,
            patch("cli.gaps_cmd.TaskManifest") as manifest_cls,
            patch("cli.gaps_cmd.TraceabilityMatrix") as matrix_cls,
        ):
            inf_cls.return_value.infer.return_value = []
            manifest_cls.from_yaml.return_value.tasks = []
            matrix = matrix_cls.return_value
            matrix.format_table.return_value = "| matrix |"
            matrix.get_gaps.return_value = []
            result = CliRunner().invoke(gaps, [str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "Requirement Coverage: 100%" in result.output

    def test_spec_file_entries_are_parsed(self, tmp_path):
        """ID/DESC blocks in --spec are parsed into requirements (no --infer)."""
        self._setup_manifest(tmp_path)
        spec = tmp_path / "spec.md"
        spec.write_text("ID: R1\nDESC: Build search\nID: R2\nDESC: Add cache\n")

        with (
            patch("cli.gaps_cmd._detect_provider", return_value="gemini"),
            patch("cli.gaps_cmd._set_api_key"),
            patch("cli.gaps_cmd._has_api_key", return_value=True),
            patch("cli.gaps_cmd.RequirementsInferrer") as inf_cls,
            patch("cli.gaps_cmd.TaskManifest") as manifest_cls,
            patch("cli.gaps_cmd.TraceabilityMatrix") as matrix_cls,
        ):
            manifest_cls.from_yaml.return_value.tasks = []
            matrix = matrix_cls.return_value
            matrix.format_table.return_value = "| matrix |"
            matrix.get_gaps.return_value = []
            result = CliRunner().invoke(gaps, [str(tmp_path), "--spec", str(spec)])

        assert result.exit_code == 0, result.output
        # Two parsed requirements were handed to the matrix; inference NOT called
        # because requirements were already present and --infer was not passed.
        inf_cls.return_value.infer.assert_not_called()
        passed_reqs = matrix_cls.call_args.kwargs["requirements"]
        assert [r.id for r in passed_reqs] == ["R1", "R2"]


# ─── prg spec ─────────────────────────────────────────────────────────────────


class TestSpecCommand:
    def test_without_generate_prints_hint(self, tmp_path):
        """Bare `prg spec` just points the user at --generate."""
        result = CliRunner().invoke(spec_cmd, [str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "Use --generate" in result.output

    def test_generate_without_api_key_aborts(self, tmp_path):
        """`prg spec --generate` with no key → error + exit 1."""
        with (
            patch("cli.gaps_cmd._detect_provider", return_value="gemini"),
            patch("cli.gaps_cmd._set_api_key"),
            patch("cli.gaps_cmd._has_api_key", return_value=False),
        ):
            result = CliRunner().invoke(spec_cmd, [str(tmp_path), "--generate"])

        assert result.exit_code == 1
        assert "requires an AI provider API key" in result.output

    def test_generate_with_provider_delegates_to_llm(self, tmp_path):
        """A provider routes to the LLM spec generator."""
        with (
            patch("cli.gaps_cmd._detect_provider", return_value="groq"),
            patch("cli.gaps_cmd._set_api_key"),
            patch("cli.gaps_cmd._has_api_key", return_value=True),
            patch("cli.gaps_cmd._generate_spec_with_llm") as gen,
        ):
            result = CliRunner().invoke(spec_cmd, [str(tmp_path), "--generate", "--provider", "groq"])

        assert result.exit_code == 0, result.output
        gen.assert_called_once()

    def test_generate_without_provider_uses_inference(self, tmp_path):
        """No provider → inference path writes a spec.md from requirements."""
        with (
            patch("cli.gaps_cmd._detect_provider", return_value=None),
            patch("cli.gaps_cmd._set_api_key"),
            patch("cli.gaps_cmd._has_api_key", return_value=True),
            patch("cli.gaps_cmd.RequirementsInferrer") as inf_cls,
        ):
            inf_cls.return_value.infer.return_value = [
                Requirement(id="R1", description="Do the thing", source="code"),
            ]
            result = CliRunner().invoke(spec_cmd, [str(tmp_path), "--generate"])

        assert result.exit_code == 0, result.output
        assert "Generated 1 requirements" in result.output
        spec_text = (tmp_path / "spec.md").read_text(encoding="utf-8")
        assert "ID: R1" in spec_text
        assert "DESC: Do the thing" in spec_text


# ─── _generate_spec_with_llm ──────────────────────────────────────────────────


class TestGenerateSpecWithLLM:
    def test_success_writes_spec(self, tmp_path, capsys):
        """A successful LLM call writes spec.md and reports its size.

        README.md and PLAN.md are seeded so the optional context-gathering
        branches (read README, read PLAN) are exercised too.
        """
        (tmp_path / "README.md").write_text("# Project\n\nDoes things.")
        (tmp_path / "PLAN.md").write_text("# Plan\n\nStep one.")
        client = MagicMock()
        client.generate.return_value = "# Spec\n\nFull structured content."
        with patch("generator.ai.factory.create_ai_client", return_value=client):
            _generate_spec_with_llm(tmp_path, "groq", api_key=None)

        out = capsys.readouterr().out
        assert "Generated spec.md" in out
        assert (tmp_path / "spec.md").read_text(encoding="utf-8").startswith("# Spec")

    def test_llm_failure_reports_and_writes_nothing(self, tmp_path, capsys):
        """If the LLM call raises, the error is surfaced and no file is written."""
        with patch(
            "generator.ai.factory.create_ai_client",
            side_effect=RuntimeError("provider exploded"),
        ):
            _generate_spec_with_llm(tmp_path, "groq", api_key=None)

        err = capsys.readouterr().err
        assert "LLM generation failed" in err
        assert not (tmp_path / "spec.md").exists()
