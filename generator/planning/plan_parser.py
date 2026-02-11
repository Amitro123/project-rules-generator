"""Plan parser for tracking progress on existing plans."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import re


@dataclass
class TaskStatus:
    """Status of a single task."""
    description: str
    completed: bool
    subtasks_total: int
    subtasks_completed: int
    
    @property
    def is_blocking(self) -> bool:
        """Check if this task is blocking progress.
        
        A task is blocking only if:
        - It is not completed
        - It has subtasks (subtasks_total > 0)
        - All its subtasks are completed
        """
        return (not self.completed and 
                self.subtasks_total > 0 and 
                self.subtasks_completed == self.subtasks_total)


@dataclass
class PhaseStatus:
    """Status of a phase."""
    name: str
    tasks: List[TaskStatus]
    
    @property
    def total_tasks(self) -> int:
        """Total number of tasks in phase."""
        return len(self.tasks)
    
    @property
    def completed_tasks(self) -> int:
        """Number of completed tasks."""
        return sum(1 for t in self.tasks if t.completed)
    
    @property
    def progress_percent(self) -> int:
        """Progress percentage."""
        if self.total_tasks == 0:
            return 100
        return int((self.completed_tasks / self.total_tasks) * 100)


@dataclass
class PlanStatus:
    """Overall plan status."""
    title: str
    filepath: Path
    phases: List[PhaseStatus]
    
    @property
    def total_tasks(self) -> int:
        """Total number of tasks across all phases."""
        return sum(p.total_tasks for p in self.phases)
    
    @property
    def completed_tasks(self) -> int:
        """Number of completed tasks."""
        return sum(p.completed_tasks for p in self.phases)
    
    @property
    def progress_percent(self) -> int:
        """Overall progress percentage."""
        if self.total_tasks == 0:
            return 100
        return int((self.completed_tasks / self.total_tasks) * 100)
    
    @property
    def current_task(self) -> Optional[TaskStatus]:
        """Get the current task being worked on (first incomplete)."""
        for phase in self.phases:
            for task in phase.tasks:
                if not task.completed:
                    return task
        return None
    
    @property
    def blocking_tasks(self) -> List[Tuple[str, TaskStatus]]:
        """Get list of blocking tasks with their phase names."""
        blocking = []
        for phase in self.phases:
            for task in phase.tasks:
                if task.is_blocking:
                    blocking.append((phase.name, task))
        return blocking


class PlanParser:
    """Parse and analyze plan files."""
    
    def parse_plan(self, filepath: Path) -> PlanStatus:
        """Parse a plan file and return status.
        
        Args:
            filepath: Path to plan file (markdown format)
            
        Returns:
            PlanStatus with progress information
        """
        content = filepath.read_text(encoding='utf-8')
        
        # Extract title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else filepath.stem
        
        # Extract phases
        phases = self._parse_phases(content)
        
        return PlanStatus(
            title=title,
            filepath=filepath,
            phases=phases
        )
    
    def _parse_phases(self, content: str) -> List[PhaseStatus]:
        """Parse phases from markdown content.
        
        Recognizes two formats:
        1. Header-based tasks: ## N. Task Name
        2. Checkbox-based tasks: - [ ] Task or - [x] Task
        """
        phases = []
        
        # Try to find numbered header tasks first (## N. Task Name)
        header_pattern = r'##\s+(\d+)\.\s+(.+?)(?:\n|$)'
        header_matches = list(re.finditer(header_pattern, content))
        
        if header_matches:
            # Parse header-based format
            for i, match in enumerate(header_matches):
                task_num = match.group(1)
                task_name = match.group(2).strip()
                
                # Extract content between this header and next
                start_pos = match.end()
                end_pos = header_matches[i + 1].start() if i + 1 < len(header_matches) else len(content)
                task_content = content[start_pos:end_pos].strip()
                
                # Check if task is completed (look for [x] or ✓ in content)
                is_completed = bool(re.search(r'\[x\]|✓|✅', task_content, re.IGNORECASE))
                
                # Create a single task for this phase
                task = TaskStatus(
                    description=task_name,
                    completed=is_completed,
                    subtasks_total=0,
                    subtasks_completed=0
                )
                
                phases.append(PhaseStatus(
                    name=f"{task_num}. {task_name}",
                    tasks=[task]
                ))
        else:
            # Fall back to old checkbox-based parsing
            # Find all phase sections (## headers, not ###)
            phase_pattern = r'##\s+(.+?)\n(.*?)(?=\n##(?!#)|\Z)'
            phase_matches = re.finditer(phase_pattern, content, re.DOTALL)
            
            for match in phase_matches:
                phase_name = match.group(1).strip()
                phase_content = match.group(2).strip()
                
                # Parse tasks from this phase
                tasks = self._parse_tasks(phase_content)
                
                phases.append(PhaseStatus(name=phase_name, tasks=tasks))
        
        return phases
    
    def _parse_tasks(self, content: str) -> List[TaskStatus]:
        """Parse tasks from phase content."""
        tasks = []
        lines = content.split('\n')
        
        current_task = None
        for line in lines:
            stripped = line.strip()
            
            # Main task (starts with - [ ] or - [x] at beginning of line, not indented)
            if re.match(r'^-\s+\[([ x])\]\s+(.+)$', stripped) and not line.startswith(' '):
                # Save previous task if exists
                if current_task:
                    tasks.append(current_task)
                
                match = re.match(r'^-\s+\[([ x])\]\s+(.+)$', stripped)
                completed = match.group(1) == 'x'
                description = match.group(2).strip()
                current_task = TaskStatus(
                    description=description,
                    completed=completed,
                    subtasks_total=0,
                    subtasks_completed=0
                )
            
            # Subtask (indented - [ ] or - [x])
            elif current_task and line.startswith(' ') and re.match(r'^-\s+\[([ x])\]\s+(.+)$', stripped):
                match = re.match(r'^-\s+\[([ x])\]\s+(.+)$', stripped)
                current_task.subtasks_total += 1
                if match.group(1) == 'x':
                    current_task.subtasks_completed += 1
        
        # Add last task
        if current_task:
            tasks.append(current_task)
        
        return tasks
    
    def find_plans(self, directory: Path) -> List[Path]:
        """Find all plan files in a directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of plan file paths
        """
        plan_files = []
        
        # Look for common plan file patterns
        patterns = [
            'PLAN*.md',
            'PROJECT-ROADMAP.md',
            'ROADMAP.md',
            '*-PLAN.md'
        ]
        
        for pattern in patterns:
            plan_files.extend(directory.glob(pattern))
        
        return sorted(set(plan_files))
    
    def format_status_report(self, status: PlanStatus) -> str:
        """Format a status report for display.
        
        Args:
            status: PlanStatus to format
            
        Returns:
            Formatted status report as string
        """
        lines = [
            f"📋 Plan Progress: {status.filepath.name}",
            f"{'=' * 60}",
            f"",
            f"Overall: {status.completed_tasks}/{status.total_tasks} tasks completed ({status.progress_percent}%)",
            f""
        ]
        
        # Current task
        if status.current_task:
            lines.append(f"🔄 Current: {status.current_task.description}")
            if status.current_task.subtasks_total > 0:
                lines.append(
                    f"   Subtasks: {status.current_task.subtasks_completed}/{status.current_task.subtasks_total}"
                )
            lines.append("")
        
        # Blocking tasks
        if status.blocking_tasks:
            lines.append("⚠️  Blocking Tasks:")
            for phase_name, task in status.blocking_tasks:
                lines.append(f"   - [{phase_name}] {task.description}")
            lines.append("")
        
        # Phase breakdown
        lines.append("Phase Breakdown:")
        for phase in status.phases:
            progress_bar = self._create_progress_bar(phase.progress_percent)
            status_icon = "✅" if phase.progress_percent == 100 else "🔄"
            lines.append(
                f"  {status_icon} {phase.name}: {phase.completed_tasks}/{phase.total_tasks} {progress_bar}"
            )
        
        return "\n".join(lines)
    
    def _create_progress_bar(self, percent: int, width: int = 20) -> str:
        """Create a text progress bar.
        
        Args:
            percent: Progress percentage (0-100)
            width: Width of progress bar in characters
            
        Returns:
            Progress bar string
        """
        filled = int((percent / 100) * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}] {percent}%"
