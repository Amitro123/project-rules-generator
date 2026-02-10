"""Tests for planning modules (project planner and plan parser)."""

import pytest
from pathlib import Path
from src.planning import (
    ProjectPlanner,
    Plan,
    Phase,
    Task,
    PlanParser,
    PlanStatus,
    PhaseStatus,
    TaskStatus
)


class TestTask:
    """Test Task dataclass."""
    
    def test_task_to_markdown_simple(self):
        """Test simple task markdown conversion."""
        task = Task("Implement feature", [])
        md = task.to_markdown()
        assert md == "- [ ] Implement feature"
    
    def test_task_to_markdown_with_subtasks(self):
        """Test task with subtasks markdown conversion."""
        task = Task("Implement feature", ["Write code", "Add tests"])
        md = task.to_markdown()
        assert "- [ ] Implement feature" in md
        assert "  - [ ] Write code" in md
        assert "  - [ ] Add tests" in md
    
    def test_task_completed(self):
        """Test completed task markdown."""
        task = Task("Implement feature", [], completed=True)
        md = task.to_markdown()
        assert md == "- [x] Implement feature"


class TestPhase:
    """Test Phase dataclass."""
    
    def test_phase_to_markdown(self):
        """Test phase markdown conversion."""
        tasks = [
            Task("Task 1", ["Subtask 1.1"]),
            Task("Task 2", [])
        ]
        phase = Phase("Phase 1: Setup", "Set up the project", tasks)
        md = phase.to_markdown()
        
        assert "## Phase 1: Setup" in md
        assert "Set up the project" in md
        assert "- [ ] Task 1" in md
        assert "- [ ] Task 2" in md


class TestPlan:
    """Test Plan dataclass."""
    
    def test_plan_to_markdown(self):
        """Test plan markdown conversion."""
        tasks = [Task("Task 1", [])]
        phases = [Phase("Phase 1", "Description", tasks)]
        plan = Plan("Test Plan", "Plan description", phases)
        
        md = plan.to_markdown()
        
        assert "# Test Plan" in md
        assert "Plan description" in md
        assert "## Phase 1" in md
    
    def test_plan_save(self, tmp_path):
        """Test saving plan to file."""
        tasks = [Task("Task 1", [])]
        phases = [Phase("Phase 1", "Description", tasks)]
        plan = Plan("Test Plan", "Plan description", phases)
        
        filepath = tmp_path / "test_plan.md"
        plan.save(filepath)
        
        assert filepath.exists()
        content = filepath.read_text(encoding='utf-8')
        assert "# Test Plan" in content


class TestProjectPlanner:
    """Test ProjectPlanner functionality."""
    
    @pytest.fixture
    def planner(self):
        """Create planner instance."""
        return ProjectPlanner()
    
    @pytest.fixture
    def sample_readme(self, tmp_path):
        """Create a sample README file."""
        readme = tmp_path / "README.md"
        readme.write_text("""# Test Project

A test project for testing.

## Features
- Feature 1: User authentication
- Feature 2: Data processing
- Feature 3: API endpoints

## TODO
- Add caching
- Improve performance
""", encoding='utf-8')
        return readme
    
    def test_extract_features_from_readme(self, planner, sample_readme):
        """Test feature extraction from README."""
        content = sample_readme.read_text(encoding='utf-8')
        features = planner._extract_features_from_readme(content)
        
        assert len(features) > 0
        assert any("authentication" in f.lower() for f in features)
        assert any("processing" in f.lower() for f in features)
    
    def test_generate_template_roadmap(self, planner, sample_readme):
        """Test template-based roadmap generation."""
        content = sample_readme.read_text(encoding='utf-8')
        features = planner._extract_features_from_readme(content)
        plan = planner._generate_template_roadmap(features, content)
        
        assert isinstance(plan, Plan)
        assert len(plan.phases) >= 3
        assert "Foundation" in plan.phases[0].name or "Phase 1" in plan.phases[0].name
    
    def test_generate_template_task_plan(self, planner):
        """Test template-based task plan generation."""
        plan = planner._generate_template_task_plan("Add Redis cache")
        
        assert isinstance(plan, Plan)
        assert "Redis cache" in plan.title
        assert len(plan.phases) >= 3
        assert any("Preparation" in p.name for p in plan.phases)
        assert any("Implementation" in p.name for p in plan.phases)


class TestTaskStatus:
    """Test TaskStatus dataclass."""
    
    def test_is_blocking_true(self):
        """Test blocking task detection."""
        task = TaskStatus(
            description="Task 1",
            completed=False,
            subtasks_total=2,
            subtasks_completed=2
        )
        assert task.is_blocking is True
    
    def test_is_blocking_false_incomplete_subtasks(self):
        """Test non-blocking when subtasks incomplete."""
        task = TaskStatus(
            description="Task 1",
            completed=False,
            subtasks_total=2,
            subtasks_completed=1
        )
        assert task.is_blocking is False
    
    def test_is_blocking_false_completed(self):
        """Test non-blocking when task completed."""
        task = TaskStatus(
            description="Task 1",
            completed=True,
            subtasks_total=2,
            subtasks_completed=2
        )
        assert task.is_blocking is False


class TestPhaseStatus:
    """Test PhaseStatus dataclass."""
    
    def test_progress_calculation(self):
        """Test progress percentage calculation."""
        tasks = [
            TaskStatus("Task 1", True, 0, 0),
            TaskStatus("Task 2", True, 0, 0),
            TaskStatus("Task 3", False, 0, 0),
            TaskStatus("Task 4", False, 0, 0),
        ]
        phase = PhaseStatus("Phase 1", tasks)
        
        assert phase.total_tasks == 4
        assert phase.completed_tasks == 2
        assert phase.progress_percent == 50


class TestPlanStatus:
    """Test PlanStatus dataclass."""
    
    @pytest.fixture
    def sample_plan_status(self, tmp_path):
        """Create a sample plan status."""
        tasks1 = [
            TaskStatus("Task 1", True, 0, 0),
            TaskStatus("Task 2", False, 2, 1),
        ]
        tasks2 = [
            TaskStatus("Task 3", False, 0, 0),
        ]
        phases = [
            PhaseStatus("Phase 1", tasks1),
            PhaseStatus("Phase 2", tasks2),
        ]
        return PlanStatus("Test Plan", tmp_path / "plan.md", phases)
    
    def test_total_tasks(self, sample_plan_status):
        """Test total tasks calculation."""
        assert sample_plan_status.total_tasks == 3
    
    def test_completed_tasks(self, sample_plan_status):
        """Test completed tasks calculation."""
        assert sample_plan_status.completed_tasks == 1
    
    def test_progress_percent(self, sample_plan_status):
        """Test progress percentage."""
        assert sample_plan_status.progress_percent == 33  # 1/3 = 33%
    
    def test_current_task(self, sample_plan_status):
        """Test current task detection."""
        current = sample_plan_status.current_task
        assert current is not None
        assert current.description == "Task 2"
    
    def test_blocking_tasks(self):
        """Test blocking tasks detection."""
        tasks = [
            TaskStatus("Task 1", False, 2, 2),  # Blocking
            TaskStatus("Task 2", False, 2, 1),  # Not blocking
        ]
        phases = [PhaseStatus("Phase 1", tasks)]
        status = PlanStatus("Test", Path("plan.md"), phases)
        
        blocking = status.blocking_tasks
        assert len(blocking) == 1
        assert blocking[0][1].description == "Task 1"


class TestPlanParser:
    """Test PlanParser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PlanParser()
    
    @pytest.fixture
    def sample_plan_file(self, tmp_path):
        """Create a sample plan file."""
        plan_content = """# Task: Add Redis Cache

Implementation plan for adding Redis caching.

---

## Phase 1: Preparation
- [x] Research Redis integration
  - [x] Review documentation
  - [x] Check compatibility
- [ ] Set up development environment
  - [ ] Install Redis
  - [ ] Configure connection

## Phase 2: Implementation
- [ ] Implement cache wrapper
  - [ ] Create cache class
  - [ ] Add error handling
- [ ] Integrate with existing code

## Phase 3: Testing
- [ ] Write unit tests
- [ ] Performance testing
"""
        plan_file = tmp_path / "PLAN-redis.md"
        plan_file.write_text(plan_content, encoding='utf-8')
        return plan_file
    
    def test_parse_plan(self, parser, sample_plan_file):
        """Test parsing a plan file."""
        status = parser.parse_plan(sample_plan_file)
        
        assert status.title == "Task: Add Redis Cache"
        assert len(status.phases) == 3
        assert status.phases[0].name == "Phase 1: Preparation"
    
    def test_parse_tasks(self, parser, sample_plan_file):
        """Test task parsing."""
        status = parser.parse_plan(sample_plan_file)
        
        phase1 = status.phases[0]
        assert len(phase1.tasks) == 2
        assert phase1.tasks[0].completed is True
        assert phase1.tasks[1].completed is False
    
    def test_parse_subtasks(self, parser, sample_plan_file):
        """Test subtask parsing."""
        status = parser.parse_plan(sample_plan_file)
        
        task1 = status.phases[0].tasks[0]
        assert task1.subtasks_total == 2
        assert task1.subtasks_completed == 2
        
        task2 = status.phases[0].tasks[1]
        assert task2.subtasks_total == 2
        assert task2.subtasks_completed == 0
    
    def test_find_plans(self, parser, tmp_path):
        """Test finding plan files."""
        # Create some plan files
        (tmp_path / "PLAN-feature.md").write_text("# Plan", encoding='utf-8')
        (tmp_path / "PROJECT-ROADMAP.md").write_text("# Roadmap", encoding='utf-8')
        (tmp_path / "README.md").write_text("# Not a plan", encoding='utf-8')
        
        plans = parser.find_plans(tmp_path)
        
        assert len(plans) == 2
        assert any("PLAN" in str(p) for p in plans)
        assert any("ROADMAP" in str(p) for p in plans)
    
    def test_format_status_report(self, parser, sample_plan_file):
        """Test status report formatting."""
        status = parser.parse_plan(sample_plan_file)
        report = parser.format_status_report(status)
        
        assert "Plan Progress" in report
        assert "Overall:" in report
        assert "Current:" in report
        assert "Phase Breakdown:" in report
    
    def test_create_progress_bar(self, parser):
        """Test progress bar creation."""
        bar = parser._create_progress_bar(50, width=10)
        assert "█" in bar
        assert "░" in bar
        assert "50%" in bar
