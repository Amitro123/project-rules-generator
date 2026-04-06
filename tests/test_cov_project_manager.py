"""Coverage boost: ProjectManager (0% covered, 112 miss)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from generator.planning.project_manager import ProjectManager


def _manager(tmp_path, provider=None, verbose=False):
    return ProjectManager(project_path=tmp_path, provider=provider, api_key=None, verbose=verbose)


class TestProjectManagerInit:
    def test_project_path_resolved(self, tmp_path):
        pm = _manager(tmp_path)
        assert pm.project_path.is_absolute()

    def test_provider_stored(self, tmp_path):
        pm = ProjectManager(project_path=tmp_path, provider="groq")
        assert pm.provider == "groq"


class TestExistsHelper:
    def test_returns_true_for_existing_file(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Test")
        pm = _manager(tmp_path)
        assert pm._exists("README.md") is True

    def test_returns_false_for_missing_file(self, tmp_path):
        pm = _manager(tmp_path)
        assert pm._exists("missing.md") is False

    def test_returns_true_for_existing_dir(self, tmp_path):
        (tmp_path / "tests").mkdir()
        pm = _manager(tmp_path)
        assert pm._exists("tests/") is True

    def test_returns_false_for_missing_dir(self, tmp_path):
        pm = _manager(tmp_path)
        assert pm._exists("tests/") is False


class TestMissingArtifacts:
    def test_returns_missing_list(self, tmp_path):
        pm = _manager(tmp_path)
        missing = pm._missing_artifacts()
        assert isinstance(missing, list)
        assert "README.md" in missing

    def test_empty_when_all_present(self, tmp_path):
        # Create all required artifacts
        readme = tmp_path / "README.md"
        readme.write_text("# Project")
        clinerules = tmp_path / ".clinerules"
        clinerules.mkdir()
        (clinerules / "rules.md").write_text("# Rules")
        skills_dir = clinerules / "skills"
        skills_dir.mkdir()
        (skills_dir / "index.md").write_text("# Index")
        (tmp_path / "tests").mkdir()
        (tmp_path / "pytest.ini").write_text("[pytest]\n")

        pm = _manager(tmp_path)
        missing = pm._missing_artifacts()
        assert missing == []


class TestArtifactStatus:
    def test_returns_dict_with_all_artifacts(self, tmp_path):
        pm = _manager(tmp_path)
        status = pm.artifact_status()
        assert isinstance(status, dict)
        assert "README.md" in status
        assert "tests/" in status

    def test_values_are_booleans(self, tmp_path):
        pm = _manager(tmp_path)
        for key, val in pm.artifact_status().items():
            assert isinstance(val, bool)


class TestGenerateMissing:
    def test_scaffolds_tests_dir(self, tmp_path):
        pm = _manager(tmp_path)
        pm._generate_missing(["tests/"])
        assert (tmp_path / "tests").is_dir()
        assert (tmp_path / "tests" / "__init__.py").exists()

    def test_scaffolds_pytest_ini(self, tmp_path):
        pm = _manager(tmp_path)
        pm._generate_missing(["pytest.ini"])
        assert (tmp_path / "pytest.ini").exists()
        content = (tmp_path / "pytest.ini").read_text()
        assert "[pytest]" in content

    def test_warns_when_readme_missing(self, tmp_path, caplog):
        import logging

        pm = _manager(tmp_path)
        with caplog.at_level(logging.WARNING):
            pm._generate_missing(["README.md"])
        assert any("README.md" in record.message for record in caplog.records)

    def test_generates_rules_when_clinerules_missing(self, tmp_path):
        pm = _manager(tmp_path)
        with patch.object(pm, "_generate_rules_and_skills") as mock_gen:
            pm._generate_missing([".clinerules/rules.md"])
        mock_gen.assert_called_once()

    def test_warns_spec_when_no_provider(self, tmp_path, caplog):
        import logging

        pm = _manager(tmp_path, provider=None)
        with caplog.at_level(logging.WARNING):
            pm._generate_missing(["spec.md"])
        assert any("spec.md" in record.message for record in caplog.records)


class TestPhase1Setup:
    def test_no_generation_when_all_present(self, tmp_path):
        pm = _manager(tmp_path)
        with patch.object(pm, "_missing_artifacts", return_value=[]):
            with patch.object(pm, "_generate_missing") as mock_gen:
                pm.phase1_setup()
        mock_gen.assert_not_called()

    def test_generates_when_missing(self, tmp_path):
        pm = _manager(tmp_path)
        with patch.object(pm, "_missing_artifacts", side_effect=[["tests/"], []]):
            with patch.object(pm, "_generate_missing") as mock_gen:
                pm.phase1_setup()
        mock_gen.assert_called_once_with(["tests/"])

    def test_warns_when_still_missing_after_generation(self, tmp_path, caplog):
        import logging

        pm = _manager(tmp_path)
        with patch.object(pm, "_missing_artifacts", return_value=["spec.md"]):
            with patch.object(pm, "_generate_missing"):
                with caplog.at_level(logging.WARNING):
                    pm.phase1_setup()
        assert any("Could not generate" in record.message for record in caplog.records)


class TestPhase2Verify:
    def test_passes_when_all_checks_pass(self, tmp_path):
        pm = _manager(tmp_path)
        mock_report = MagicMock()
        mock_report.all_passed = True
        mock_report.format_report.return_value = "All checks passed"

        with patch("generator.planning.project_manager.PreflightChecker") as MockChecker:
            MockChecker.return_value.run_checks.return_value = mock_report
            pm.phase2_verify()  # Should not raise

    def test_raises_when_checks_fail(self, tmp_path):
        pm = _manager(tmp_path)
        mock_report = MagicMock()
        mock_report.all_passed = False
        mock_report.format_report.return_value = "Checks failed"
        failed_check = MagicMock()
        failed_check.name = "Rules file"
        mock_report.failed_checks = [failed_check]

        with patch("generator.planning.project_manager.PreflightChecker") as MockChecker:
            MockChecker.return_value.run_checks.return_value = mock_report
            with pytest.raises(RuntimeError, match="Readiness verification failed"):
                pm.phase2_verify()


class TestRun:
    def test_run_calls_phase1_setup(self, tmp_path):
        pm = _manager(tmp_path)
        with patch.object(pm, "phase1_setup") as mock_setup:
            pm.run()
        mock_setup.assert_called_once()


class TestPrintStatus:
    def test_does_not_raise(self, tmp_path):
        pm = _manager(tmp_path)
        pm.print_status()  # Should not raise
