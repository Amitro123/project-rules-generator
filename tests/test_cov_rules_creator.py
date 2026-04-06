"""Coverage boost: CoworkRulesCreator pure methods."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from generator.rules_creator import CoworkRulesCreator, Rule, RulesMetadata


def _creator(tmp_path):
    """Build a creator without triggering real LLM or git."""
    with patch("generator.rules_creator.RulesGitMiner") as MockMiner:
        MockMiner.return_value.available = False
        MockMiner.return_value.extract_antipatterns.return_value = []
        c = CoworkRulesCreator(project_path=tmp_path, provider="groq")
    return c


class TestDetectTechStack:
    def test_merges_enhanced_context_tech(self, tmp_path):
        c = _creator(tmp_path)
        ctx = {"metadata": {"tech_stack": ["fastapi", "pydantic"]}}
        result = c._detect_tech_stack("", ctx)
        assert "fastapi" in result
        assert "pydantic" in result

    def test_returns_sorted_deduped_list(self, tmp_path):
        c = _creator(tmp_path)
        ctx = {"metadata": {"tech_stack": ["python", "python", "click"]}}
        result = c._detect_tech_stack("", ctx)
        assert result == sorted(set(result))
        assert result.count("python") == 1

    def test_empty_context_returns_empty(self, tmp_path):
        c = _creator(tmp_path)
        result = c._detect_tech_stack("", {})
        assert isinstance(result, list)

    def test_uses_tech_detector_util(self, tmp_path):
        c = _creator(tmp_path)
        with patch("generator.utils.tech_detector.detect_tech_stack", return_value=["react"]):
            result = c._detect_tech_stack("some readme content", {})
        assert isinstance(result, list)


class TestDetectProjectType:
    def test_delegates_to_detector(self, tmp_path):
        c = _creator(tmp_path)
        with patch(
            "generator.analyzers.project_type_detector.detect_project_type", return_value={"primary_type": "python-api"}
        ):
            result = c._detect_project_type(["fastapi"], {})
        assert result == "python-api"

    def test_returns_library_on_exception(self, tmp_path):
        c = _creator(tmp_path)
        with patch("generator.analyzers.project_type_detector.detect_project_type", return_value={}):
            result = c._detect_project_type(["fastapi"], {})
        # Returns result.get("primary_type", "python-library") — empty dict → fallback
        assert result == "python-library"


class TestIdentifyPriorityAreas:
    def test_fastapi_maps_to_rest_api_patterns(self, tmp_path):
        c = _creator(tmp_path)
        areas = c._identify_priority_areas(["fastapi"], "python-api")
        assert "rest_api_patterns" in areas

    def test_pytest_maps_to_test_coverage(self, tmp_path):
        c = _creator(tmp_path)
        areas = c._identify_priority_areas(["pytest"], "python-cli")
        assert "test_coverage" in areas

    def test_react_maps_to_hooks_patterns(self, tmp_path):
        c = _creator(tmp_path)
        areas = c._identify_priority_areas(["react"], "react-app")
        assert "hooks_patterns" in areas

    def test_no_duplicates(self, tmp_path):
        c = _creator(tmp_path)
        areas = c._identify_priority_areas(["fastapi", "flask"], "python-api")
        assert len(areas) == len(set(areas))

    def test_empty_tech_returns_list(self, tmp_path):
        c = _creator(tmp_path)
        areas = c._identify_priority_areas([], "unknown")
        assert isinstance(areas, list)


class TestDetectSignals:
    def test_has_tests_detected(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        c = CoworkRulesCreator.__new__(CoworkRulesCreator)
        c.project_path = tmp_path
        signals = c._detect_signals()
        assert "has_tests" in signals

    def test_has_docker_detected(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.11")
        c = CoworkRulesCreator.__new__(CoworkRulesCreator)
        c.project_path = tmp_path
        signals = c._detect_signals()
        assert "has_docker" in signals

    def test_no_signals_empty_dir(self, tmp_path):
        c = CoworkRulesCreator.__new__(CoworkRulesCreator)
        c.project_path = tmp_path
        signals = c._detect_signals()
        assert isinstance(signals, list)


class TestGenerateGenericRules:
    def test_returns_three_rules(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="P", tech_stack=[], project_type="unknown", priority_areas=[], detected_signals=[]
        )
        rules = c._generate_generic_rules(meta)
        assert len(rules) == 3

    def test_all_rules_are_rule_instances(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="P", tech_stack=[], project_type="unknown", priority_areas=[], detected_signals=[]
        )
        rules = c._generate_generic_rules(meta)
        assert all(isinstance(r, Rule) for r in rules)


class TestGenerateArchitectureRules:
    def test_python_api_returns_route_rules(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="P", tech_stack=["fastapi"], project_type="python-api", priority_areas=[], detected_signals=[]
        )
        rules = c._generate_architecture_rules(meta)
        assert len(rules) > 0
        assert any("route" in r.content.lower() or "layer" in r.content.lower() for r in rules)

    def test_python_cli_returns_click_rules(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="P", tech_stack=["click"], project_type="python-cli", priority_areas=[], detected_signals=[]
        )
        rules = c._generate_architecture_rules(meta)
        assert any("cli" in r.content.lower() or "command" in r.content.lower() for r in rules)

    def test_unknown_type_returns_generic_rules(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="P", tech_stack=[], project_type="unknown", priority_areas=[], detected_signals=[]
        )
        rules = c._generate_architecture_rules(meta)
        assert isinstance(rules, list)


class TestGenerateTestingRules:
    def test_pytest_project_returns_pytest_rules(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="P", tech_stack=["pytest"], project_type="python-cli", priority_areas=[], detected_signals=[]
        )
        rules = c._generate_testing_rules(meta)
        assert any("pytest" in r.content.lower() for r in rules)

    def test_jest_project_returns_jest_rules(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="P", tech_stack=["jest"], project_type="react-app", priority_areas=[], detected_signals=[]
        )
        rules = c._generate_testing_rules(meta)
        assert any("jest" in r.content.lower() for r in rules)

    def test_returns_list(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="P", tech_stack=[], project_type="unknown", priority_areas=[], detected_signals=[]
        )
        rules = c._generate_testing_rules(meta)
        assert isinstance(rules, list)


class TestExportToFile:
    def test_creates_file(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="Proj", tech_stack=[], project_type="unknown", priority_areas=[], detected_signals=[]
        )
        path = c.export_to_file("# Content\n", meta, tmp_path)
        assert path.exists()

    def test_file_contains_content(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="Proj", tech_stack=[], project_type="unknown", priority_areas=[], detected_signals=[]
        )
        path = c.export_to_file("# My Rules\n", meta, tmp_path)
        assert "# My Rules" in path.read_text(encoding="utf-8")

    def test_custom_filename(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="Proj", tech_stack=[], project_type="unknown", priority_areas=[], detected_signals=[]
        )
        path = c.export_to_file("content", meta, tmp_path, filename="custom.md")
        assert path.name == "custom.md"

    def test_creates_output_directory(self, tmp_path):
        c = _creator(tmp_path)
        meta = RulesMetadata(
            project_name="Proj", tech_stack=[], project_type="unknown", priority_areas=[], detected_signals=[]
        )
        out_dir = tmp_path / "subdir" / "rules"
        path = c.export_to_file("content", meta, out_dir)
        assert path.exists()


class TestBuildMetadata:
    def test_returns_rules_metadata(self, tmp_path):
        c = _creator(tmp_path)
        with patch.object(c, "_detect_tech_stack", return_value=["python"]):
            with patch.object(c, "_detect_project_type", return_value="python-cli"):
                with patch.object(c, "_identify_priority_areas", return_value=["testing"]):
                    with patch.object(c, "_detect_signals", return_value=["has_tests"]):
                        meta = c._build_metadata("readme", ["python"], {})
        assert isinstance(meta, RulesMetadata)
        assert meta.project_name == tmp_path.name

    def test_metadata_has_tech_stack(self, tmp_path):
        c = _creator(tmp_path)
        with patch.object(c, "_detect_tech_stack", return_value=["fastapi"]):
            with patch.object(c, "_detect_project_type", return_value="python-api"):
                with patch.object(c, "_identify_priority_areas", return_value=["rest_api"]):
                    with patch.object(c, "_detect_signals", return_value=[]):
                        meta = c._build_metadata("readme", ["fastapi"], {})
        assert "fastapi" in meta.tech_stack
