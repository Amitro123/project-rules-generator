"""Tests for the ``prg tasks`` command (cli/tasks_cmd.py).

This command was at 29% coverage (CR §4.4). It gathers requirements (either by
inferring them via an LLM or by parsing ``spec.md``), decomposes them into tasks,
and writes a task manifest. We exercise every branch with the LLM/decomposer/
creator collaborators mocked so no network or API key is needed:

- spec.md present but empty            → "No requirements found" early return
- spec.md with ID/DESC entries         → parse + decompose + create
- --infer-spec, inferrer raises        → "Cannot infer requirements" early return
- --infer-spec, inferrer succeeds      → decompose + create
"""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cli.tasks_cmd import tasks_cmd


def _patches():
    """Patch the four collaborators imported into cli.tasks_cmd.

    Returns the patch context managers so a test can enter them and configure
    the returned mocks.
    """
    return (
        patch("cli.tasks_cmd._detect_provider", return_value="gemini"),
        patch("cli.tasks_cmd._set_api_key"),
        patch("cli.tasks_cmd.RequirementsInferrer"),
        patch("cli.tasks_cmd.TaskDecomposer"),
        patch("cli.tasks_cmd.TaskCreator"),
    )


class TestTasksCmd:
    def test_spec_present_but_empty_reports_no_requirements(self, tmp_path):
        """An existing spec.md with no ID/DESC blocks → early 'No requirements'."""
        (tmp_path / "spec.md").write_text("Just some prose, no structured entries.")

        p_detect, p_setkey, p_inf, p_dec, p_create = _patches()
        with p_detect, p_setkey, p_inf, p_dec, p_create:
            result = CliRunner().invoke(tasks_cmd, [str(tmp_path), "--quiet"])

        assert result.exit_code == 0, result.output
        assert "No requirements found" in result.output

    def test_spec_with_entries_decomposes_and_creates(self, tmp_path):
        """spec.md with ID/DESC lines is parsed, decomposed, and written out."""
        (tmp_path / "spec.md").write_text("ID: R1\nDESC: Build the login flow\nID: R2\nDESC: Add logout\n")

        p_detect, p_setkey, p_inf, p_dec, p_create = _patches()
        with p_detect, p_setkey, p_inf, p_dec as dec_cls, p_create as create_cls:
            dec_cls.return_value.decompose.return_value = [MagicMock(), MagicMock(), MagicMock()]
            result = CliRunner().invoke(tasks_cmd, [str(tmp_path), "--quiet"])

        assert result.exit_code == 0, result.output
        assert "Generated 3 tasks" in result.output
        # The two parsed requirement descriptions are fed to the decomposer.
        dec_cls.return_value.decompose.assert_called_once()
        create_cls.return_value.create_from_subtasks.assert_called_once()

    def test_infer_spec_value_error_aborts_with_guidance(self, tmp_path):
        """When inference raises ValueError, the command prints API-key guidance."""
        p_detect, p_setkey, p_inf, p_dec, p_create = _patches()
        with p_detect, p_setkey, p_inf as inf_cls, p_dec, p_create:
            inf_cls.return_value.infer.side_effect = ValueError("no API key configured")
            result = CliRunner().invoke(tasks_cmd, [str(tmp_path), "--infer-spec", "--quiet"])

        assert result.exit_code == 0, result.output
        assert "Cannot infer requirements" in result.output
        assert "Set an API key" in result.output

    def test_infer_spec_success_decomposes(self, tmp_path):
        """A successful inference flows into decomposition and file creation."""
        p_detect, p_setkey, p_inf, p_dec, p_create = _patches()
        with p_detect, p_setkey, p_inf as inf_cls, p_dec as dec_cls, p_create as create_cls:
            inf_cls.return_value.infer.return_value = ["Implement search", "Add caching"]
            dec_cls.return_value.decompose.return_value = [MagicMock(), MagicMock()]
            result = CliRunner().invoke(tasks_cmd, [str(tmp_path), "--infer-spec", "--verbose"])

        assert result.exit_code == 0, result.output
        assert "Inferring requirements" in result.output
        assert "Generated 2 tasks" in result.output
        create_cls.return_value.create_from_subtasks.assert_called_once()

    def test_infer_empty_requirements_reports_none(self, tmp_path):
        """Inference returning nothing → 'No requirements found' early return."""
        p_detect, p_setkey, p_inf, p_dec, p_create = _patches()
        with p_detect, p_setkey, p_inf as inf_cls, p_dec, p_create:
            inf_cls.return_value.infer.return_value = []
            result = CliRunner().invoke(tasks_cmd, [str(tmp_path), "--infer-spec", "--quiet"])

        assert result.exit_code == 0, result.output
        assert "No requirements found" in result.output
