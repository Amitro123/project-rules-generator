import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
from generator.planning.autopilot import AutopilotOrchestrator
from generator.planning.task_creator import TaskManifest, TaskEntry
from generator.task_decomposer import SubTask

@pytest.fixture
def mock_project_path(tmp_path):
    return tmp_path / "test_project"

@pytest.fixture
def orchestrator(mock_project_path):
    return AutopilotOrchestrator(project_path=mock_project_path, verbose=False)

def test_discovery_phase(orchestrator):
    """Verify discovery phase initializes workflow and runs setup."""
    with patch("generator.planning.autopilot.AgentWorkflow") as MockWorkflow:
        mock_instance = MockWorkflow.return_value
        expected_manifest = TaskManifest(plan_file="PLAN.md", task_description="Test Task", tasks=[])
        mock_instance.run_setup.return_value = expected_manifest
        
        manifest = orchestrator.discovery(task_description="Test Task")
        
        MockWorkflow.assert_called_with(
            project_path=orchestrator.project_path,
            task_description="Test Task",
            provider=orchestrator.provider,
            api_key=orchestrator.api_key,
            verbose=orchestrator.verbose
        )
        mock_instance.run_setup.assert_called_once()
        assert manifest == expected_manifest

def test_execution_loop_happy_path(orchestrator):
    """Verify execution loop processes tasks and commits changes."""
    # Mock Manifest and Task
    mock_manifest = MagicMock(spec=TaskManifest)
    mock_task_entry = TaskEntry(id=1, title="Test Task", file="task_1.md", status="pending")
    
    # Mock SubTask details load
    mock_subtask = SubTask(id=1, title="Test Task", goal="Fix it", files=["test.py"], changes=["print('hello')"], tests=[], dependencies=[], estimated_minutes=10)
    
    # Mock Components
    with patch("generator.planning.autopilot.TaskExecutor") as MockExecutor, \
         patch("generator.planning.autopilot.TaskImplementationAgent") as MockAgent, \
         patch("generator.planning.autopilot.git_ops") as mock_git, \
         patch("generator.planning.autopilot.click.echo") as mock_echo, \
         patch("rich.prompt.Confirm.ask", return_value=True) as mock_confirm:
        
        # Setup Executor
        mock_executor_instance = MockExecutor.return_value
        mock_executor_instance.get_next_task.side_effect = [mock_task_entry, None] # One task, then finish
        
        # Setup Agent
        mock_agent_instance = MockAgent.return_value
        mock_agent_instance.implement.return_value = {"test.py": "print('hello')"}
        
        # Setup Orchestrator method to return mock subtask directly to avoid file reading
        orchestrator._load_subtask_details = MagicMock(return_value=mock_subtask)
        
        # Setup Git
        mock_git.get_current_branch.return_value = "main"

        # Run Loop
        orchestrator.execution_loop(mock_manifest)
        
        # Verifications
        # 1. Branching
        mock_git.create_branch.assert_called_with("autopilot/task-1", orchestrator.project_path)
        
        # 2. Agent Execution
        mock_agent_instance.implement.assert_called_once()
        
        # 3. File Writing
        output_file = orchestrator.project_path / "test.py"
        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8") == "print('hello')"
        
        # 4. Confirmation & Merge
        mock_confirm.assert_called_once()
        mock_executor_instance.complete_task.assert_called_with(1)
        mock_git.merge_branch.assert_called_with("autopilot/task-1", orchestrator.project_path)
        mock_git.delete_branch.assert_called_with("autopilot/task-1", force=True, repo_path=orchestrator.project_path)

def test_execution_loop_rejection(orchestrator):
    """Verify rejection triggers rollback."""
    # Mock Manifest and Task
    mock_manifest = MagicMock(spec=TaskManifest)
    mock_task_entry = TaskEntry(id=1, title="Test Task", file="task_1.md", status="pending")
    
    # Mock SubTask
    mock_subtask = SubTask(id=1, title="Test Task", goal="Fix it", files=["test.py"], changes=[], tests=[], dependencies=[], estimated_minutes=10)
    
    with patch("generator.planning.autopilot.TaskExecutor") as MockExecutor, \
         patch("generator.planning.autopilot.TaskImplementationAgent") as MockAgent, \
         patch("generator.planning.autopilot.git_ops") as mock_git, \
         patch("rich.prompt.Confirm.ask", return_value=False) as mock_confirm: # User rejects
        
        mock_executor_instance = MockExecutor.return_value
        mock_executor_instance.get_next_task.side_effect = [mock_task_entry] # Stop after rejection logic breaks loop
        
        mock_agent_instance = MockAgent.return_value
        mock_agent_instance.implement.return_value = {}
        
        orchestrator._load_subtask_details = MagicMock(return_value=mock_subtask)
        mock_git.get_current_branch.return_value = "main"

        orchestrator.execution_loop(mock_manifest)
        
        # Verification
        mock_git.rollback_to_head.assert_called()
        mock_git.delete_branch.assert_called()
        mock_executor_instance.complete_task.assert_not_called()
