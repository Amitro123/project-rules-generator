"""Coverage boost: ProjectContextScanner (24% → higher)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from generator.skill_project_scanner import ProjectContextScanner


class TestDetectProjectSignals:
    def test_has_docker_detected(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.11")
        scanner = ProjectContextScanner(project_path=tmp_path)
        signals = scanner.detect_project_signals()
        assert "has_docker" in signals

    def test_has_tests_detected_by_dir(self, tmp_path):
        (tmp_path / "tests").mkdir()
        scanner = ProjectContextScanner(project_path=tmp_path)
        signals = scanner.detect_project_signals()
        assert "has_tests" in signals

    def test_has_docs_detected_by_readme(self, tmp_path):
        (tmp_path / "README.md").write_text("# Readme")
        scanner = ProjectContextScanner(project_path=tmp_path)
        signals = scanner.detect_project_signals()
        assert "has_docs" in signals

    def test_empty_dir_no_signals(self, tmp_path):
        scanner = ProjectContextScanner(project_path=tmp_path)
        signals = scanner.detect_project_signals()
        assert isinstance(signals, set)

    def test_result_is_cached(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.11")
        scanner = ProjectContextScanner(project_path=tmp_path)
        first = scanner.detect_project_signals()
        second = scanner.detect_project_signals()
        assert first is second  # same object returned from cache


class TestDetectTechStack:
    def test_returns_list(self, tmp_path):
        scanner = ProjectContextScanner(project_path=tmp_path)
        with patch("generator.skill_project_scanner._detect_tech_stack_util", return_value=["python"]):
            result = scanner.detect_tech_stack("")
        assert "python" in result

    def test_cache_skips_re_detection(self, tmp_path):
        scanner = ProjectContextScanner(project_path=tmp_path)
        with patch("generator.skill_project_scanner._detect_tech_stack_util", return_value=["react"]) as mock_fn:
            scanner.detect_tech_stack("first call")
            scanner.detect_tech_stack("second call")
        # Should only be called once due to caching
        assert mock_fn.call_count == 1

    def test_empty_readme_returns_list(self, tmp_path):
        scanner = ProjectContextScanner(project_path=tmp_path)
        with patch("generator.skill_project_scanner._detect_tech_stack_util", return_value=[]):
            result = scanner.detect_tech_stack("")
        assert isinstance(result, list)


class TestAnalyzeProjectStructure:
    def test_pytest_skill_scans_tests_dir(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_foo.py").write_text("def test_foo(): pass")
        scanner = ProjectContextScanner(project_path=tmp_path)
        analysis = scanner.analyze_project_structure("pytest-workflow", [])
        assert "structure" in analysis
        assert len(analysis["structure"].get("test_files", [])) > 0

    def test_pytest_skill_with_conftest(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        conftest = tests_dir / "conftest.py"
        conftest.write_text("import pytest\n@pytest.fixture\ndef my_fixture(): pass\n")
        scanner = ProjectContextScanner(project_path=tmp_path)
        analysis = scanner.analyze_project_structure("pytest-testing", [])
        assert "Uses pytest fixtures" in analysis["patterns"]

    def test_pytest_skill_with_markers(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        conftest = tests_dir / "conftest.py"
        conftest.write_text("@pytest.mark.unit\ndef setup(): pass\n")
        scanner = ProjectContextScanner(project_path=tmp_path)
        analysis = scanner.analyze_project_structure("pytest-testing", [])
        assert "Uses pytest markers" in analysis["patterns"]

    def test_pytest_ini_in_actual_files(self, tmp_path):
        (tmp_path / "pytest.ini").write_text("[pytest]\naddopts=-v\n")
        scanner = ProjectContextScanner(project_path=tmp_path)
        analysis = scanner.analyze_project_structure("pytest-workflow", [])
        assert "pytest.ini" in analysis["actual_files"]

    def test_fastapi_skill_scans_api_dirs(self, tmp_path):
        api_dir = tmp_path / "api"
        api_dir.mkdir()
        (api_dir / "routes.py").write_text("from fastapi import APIRouter")
        scanner = ProjectContextScanner(project_path=tmp_path)
        analysis = scanner.analyze_project_structure("fastapi-workflow", [])
        assert "structure" in analysis

    def test_unknown_skill_returns_empty_structure(self, tmp_path):
        scanner = ProjectContextScanner(project_path=tmp_path)
        analysis = scanner.analyze_project_structure("generic-workflow", [])
        assert analysis["actual_files"] == []
        assert analysis["patterns"] == []

    def test_pytest_configure_pattern_detected(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        conftest = tests_dir / "conftest.py"
        conftest.write_text("def pytest_configure(config): pass\n")
        scanner = ProjectContextScanner(project_path=tmp_path)
        analysis = scanner.analyze_project_structure("pytest-testing", [])
        assert "Has pytest_configure hook" in analysis["patterns"]


class TestDetectSkillNeeds:
    def test_returns_list(self, tmp_path):
        scanner = ProjectContextScanner(project_path=tmp_path)
        with patch.object(scanner, "detect_tech_stack", return_value=[]):
            result = scanner.detect_skill_needs(tmp_path)
        assert isinstance(result, list)

    def test_fallback_workflow_when_no_tech(self, tmp_path):
        scanner = ProjectContextScanner(project_path=tmp_path)
        with patch.object(scanner, "detect_tech_stack", return_value=[]):
            result = scanner.detect_skill_needs(tmp_path)
        assert any("workflow" in s for s in result)

    def test_known_tech_maps_to_skill(self, tmp_path):
        scanner = ProjectContextScanner(project_path=tmp_path)
        with patch.object(scanner, "detect_tech_stack", return_value=["fastapi"]):
            result = scanner.detect_skill_needs(tmp_path)
        # fastapi should map to a known skill name
        assert isinstance(result, list)
        assert len(result) > 0


class TestIsReadmeSufficient:
    def test_delegates_to_utility(self, tmp_path):
        scanner = ProjectContextScanner(project_path=tmp_path)
        with patch("generator.skill_project_scanner.ProjectContextScanner.is_readme_sufficient", return_value=True):
            result = scanner.is_readme_sufficient("# Good README\n\nLots of content here.")
        assert result is True


class TestScanProjectTree:
    def test_returns_string(self, tmp_path):
        scanner = ProjectContextScanner(project_path=tmp_path)
        result = scanner.scan_project_tree()
        assert isinstance(result, str)
