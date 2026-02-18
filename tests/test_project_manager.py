import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
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
    with patch("generator.planning.project_manager.click.echo") as mock_echo, \
         patch("generator.planning.project_manager.ProjectManager._generate_missing_docs") as mock_gen, \
         patch("generator.planning.project_manager.ProjectManager._update_manager_checklist") as mock_update:
        
        manager.phase1_setup()
        
        # Should call update checklist twice (before and after generation)
        assert mock_update.call_count == 2
        # Should call generate missing docs because project is empty
        mock_gen.assert_called_once()

def test_phase2_verify(manager):
    """Verify Phase 2 runs preflight check."""
    with patch("generator.planning.project_manager.PreflightChecker") as MockChecker, \
         patch("generator.planning.project_manager.click.echo"):
        
        mock_instance = MockChecker.return_value
        mock_instance.run_checks.return_value.all_passed = True
        
        manager.phase2_verify()
        
        MockChecker.assert_called_once()
        mock_instance.run_checks.assert_called_once()

def test_phase3_copilot(manager):
    """Verify Phase 3 delegates to AutopilotOrchestrator."""
    with patch("generator.planning.project_manager.AutopilotOrchestrator") as MockOrch, \
         patch("generator.planning.project_manager.TaskManifest") as MockManifest, \
         patch("generator.planning.project_manager.click.echo"):
        
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
    with patch("generator.planning.project_manager.click.echo"):
        manager.phase4_summary()
        
        report_path = manager.project_path / "PROJECT-COMPLETION.md"
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "# Project Completion Report" in content
        assert "Generated Artifacts" in content
