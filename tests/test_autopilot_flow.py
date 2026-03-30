from unittest.mock import MagicMock, patch

import pytest

from generator.exceptions import SecurityError
from generator.planning.autopilot import AutopilotOrchestrator
from generator.planning.task_creator import TaskEntry, TaskManifest
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
            verbose=orchestrator.verbose,
        )
        mock_instance.run_setup.assert_called_once()
        assert manifest == expected_manifest


def test_execution_loop_happy_path(orchestrator):
    """Verify execution loop processes tasks and commits changes."""
    # Mock Manifest and Task
    mock_manifest = MagicMock(spec=TaskManifest)
    mock_task_entry = TaskEntry(id=1, title="Test Task", file="task_1.md", status="pending")

    # Mock SubTask details load
    mock_subtask = SubTask(
        id=1,
        title="Test Task",
        goal="Fix it",
        files=["test.py"],
        changes=["print('hello')"],
        tests=[],
        dependencies=[],
        estimated_minutes=10,
    )

    # Mock Components
    with patch("generator.planning.autopilot.TaskExecutor") as MockExecutor, patch(
        "generator.planning.autopilot.TaskImplementationAgent"
    ) as MockAgent, patch("generator.planning.autopilot.git_ops") as mock_git, patch(
        "generator.planning.autopilot.click.echo"
    ), patch(
        "click.prompt", return_value="a"
    ) as mock_prompt:

        # Setup Executor
        mock_executor_instance = MockExecutor.return_value
        mock_executor_instance.get_next_task.side_effect = [mock_task_entry, None]

        # Setup Agent
        mock_agent_instance = MockAgent.return_value
        mock_agent_instance.implement.return_value = {"test.py": "print('hello')"}

        # Setup Orchestrator methods
        orchestrator._load_subtask_details = MagicMock(return_value=mock_subtask)
        orchestrator._run_tests = MagicMock(return_value=(True, "all passed"))

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

        # 4. User prompt shown, task completed, branch merged
        mock_prompt.assert_called_once()
        mock_executor_instance.complete_task.assert_called_with(1)
        mock_git.merge_branch.assert_called_with("autopilot/task-1", orchestrator.project_path)
        mock_git.delete_branch.assert_called_with("autopilot/task-1", force=True, repo_path=orchestrator.project_path)


def test_validate_write_path_within_project(tmp_path):
    """Valid relative paths resolve inside project_path."""
    orch = AutopilotOrchestrator(project_path=tmp_path, verbose=False)
    result = orch._validate_write_path("src/foo.py")
    assert result == (tmp_path / "src" / "foo.py").resolve()


def test_validate_write_path_traversal_raises(tmp_path):
    """Path traversal attempt raises SecurityError."""
    orch = AutopilotOrchestrator(project_path=tmp_path, verbose=False)
    with pytest.raises(SecurityError):
        orch._validate_write_path("../../etc/passwd")


def test_load_subtask_details_structured(tmp_path):
    """Uses structured manifest fields when present."""
    orch = AutopilotOrchestrator(project_path=tmp_path, verbose=False)
    entry = TaskEntry(
        id=1,
        file="task001-test.md",
        title="My Task",
        goal="Do the thing",
        files=["a.py", "b.py"],
        changes=["Add function"],
        tests=["test_a.py"],
    )
    subtask = orch._load_subtask_details(entry)
    assert subtask.goal == "Do the thing"
    assert subtask.files == ["a.py", "b.py"]
    assert subtask.changes == ["Add function"]
    assert subtask.tests == ["test_a.py"]


def test_load_subtask_details_legacy_fallback(tmp_path):
    """Falls back to regex parsing when structured fields are empty."""
    orch = AutopilotOrchestrator(project_path=tmp_path, verbose=False)
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    task_md = task_dir / "task001-legacy.md"
    task_md.write_text(
        "# Task 1: Legacy\n\n**Goal:** Parse from markdown\n\n## Files\n- `legacy.py`\n",
        encoding="utf-8",
    )
    entry = TaskEntry(id=1, file="task001-legacy.md", title="Legacy")
    subtask = orch._load_subtask_details(entry)
    assert subtask.goal == "Parse from markdown"
    assert "legacy.py" in subtask.files


def test_execution_loop_rejection(orchestrator):
    """Verify rejection triggers rollback."""
    # Mock Manifest and Task
    mock_manifest = MagicMock(spec=TaskManifest)
    mock_task_entry = TaskEntry(id=1, title="Test Task", file="task_1.md", status="pending")

    # Mock SubTask
    mock_subtask = SubTask(
        id=1,
        title="Test Task",
        goal="Fix it",
        files=["test.py"],
        changes=[],
        tests=[],
        dependencies=[],
        estimated_minutes=10,
    )

    with patch("generator.planning.autopilot.TaskExecutor") as MockExecutor, patch(
        "generator.planning.autopilot.TaskImplementationAgent"
    ) as MockAgent, patch("generator.planning.autopilot.git_ops") as mock_git, patch(
        "generator.planning.autopilot.click.echo"
    ), patch(
        "click.prompt", return_value="q"
    ):  # User stops

        mock_executor_instance = MockExecutor.return_value
        mock_executor_instance.get_next_task.side_effect = [mock_task_entry]

        mock_agent_instance = MockAgent.return_value
        mock_agent_instance.implement.return_value = {}

        orchestrator._load_subtask_details = MagicMock(return_value=mock_subtask)
        orchestrator._run_tests = MagicMock(return_value=(True, "all passed"))
        mock_git.get_current_branch.return_value = "main"

        orchestrator.execution_loop(mock_manifest)

        # Verification: stop → rollback, delete branch, no complete
        mock_git.rollback_to_head.assert_called()
        mock_git.delete_branch.assert_called()
        mock_executor_instance.complete_task.assert_not_called()
