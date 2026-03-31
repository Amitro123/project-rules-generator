from unittest.mock import MagicMock, patch

import pytest

from generator.planning.project_manager import ProjectManager


@pytest.fixture
def mock_project_path(tmp_path):
    return tmp_path / "test_project"


@pytest.fixture
def manager(mock_project_path):
    mock_project_path.mkdir()
    return ProjectManager(project_path=mock_project_path, verbose=False)


def test_phase1_setup(manager):
    """Verify Phase 1 setup generates missing docs."""
    with patch("generator.planning.project_manager.ProjectManager._generate_missing_docs") as mock_gen, patch(
        "generator.planning.project_manager.ProjectManager._update_manager_checklist"
    ) as mock_update:

        manager.phase1_setup()

        # Should call update checklist twice (before and after generation)
        assert mock_update.call_count == 2
        # Should call generate missing docs because project is empty
        mock_gen.assert_called_once()


def test_phase2_verify(manager):
    """Verify Phase 2 runs preflight check."""
    with patch("generator.planning.project_manager.PreflightChecker") as MockChecker:

        mock_instance = MockChecker.return_value
        mock_instance.run_checks.return_value.all_passed = True

        manager.phase2_verify()

        MockChecker.assert_called_once()
        mock_instance.run_checks.assert_called_once()


def test_phase3_copilot(manager):
    """Verify Phase 3 delegates to AutopilotOrchestrator."""
    with patch("generator.planning.project_manager.AutopilotOrchestrator") as MockOrch, patch(
        "generator.planning.project_manager.TaskManifest"
    ) as MockManifest:

        # Create dummy TASKS.yaml so logic proceeds
        (manager.project_path / "tasks").mkdir()
        (manager.project_path / "tasks" / "TASKS.yaml").touch()

        mock_orch_instance = MockOrch.return_value

        manager.phase3_copilot()

        MockOrch.assert_called_once()
        # Should load manifest and run execution_loop
        MockManifest.from_yaml.assert_called_once()
        mock_orch_instance.execution_loop.assert_called_once()


def test_phase4_summary(manager):
    """Verify Phase 4 generates completion report."""
    manager.phase4_summary()

    report_path = manager.project_path / "PROJECT-COMPLETION.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Project Completion Report" in content
    assert "Generated Artifacts" in content


def test_generate_rules_and_skills_calls_generator_directly(manager):
    """Verify _generate_rules_and_skills uses generator functions, not CliRunner."""
    mock_creator = MagicMock()
    mock_creator.create_rules.return_value = ("content", MagicMock(), MagicMock())
    mock_skills_mgr = MagicMock()

    with (
        patch("generator.rules_creator.CoworkRulesCreator", return_value=mock_creator),
        patch("generator.skills_manager.SkillsManager", return_value=mock_skills_mgr),
        patch("generator.utils.readme_bridge.find_readme", return_value=None),
        patch("generator.parsers.enhanced_parser.EnhancedProjectParser") as MockParser,
    ):
        MockParser.return_value.extract_full_context.return_value = {}
        manager._generate_rules_and_skills()

    # Must call CoworkRulesCreator directly — no CliRunner involved
    mock_creator.create_rules.assert_called_once()
    mock_creator.export_to_file.assert_called_once()
    mock_skills_mgr.save_triggers_json.assert_called_once()
    mock_skills_mgr.generate_perfect_index.assert_called_once()
