import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .requirements import Requirement
from .planning.task_creator import TaskManifest, TaskEntry

@dataclass
class TraceabilityMatrix:
    """Maps requirements to task coverage."""
    requirements: List[Requirement]
    tasks: List[TaskEntry]
    mapping: Dict[str, List[int]] = field(default_factory=dict) # req_id -> list of task_ids

    def build(self, api_client=None):
        """Build the mapping using AI or heuristics."""
        # Simple heuristic: check if requirement keywords appear in task titles/goals
        # In a full implementation, this should use AI for semantic matching
        for req in self.requirements:
            self.mapping[req.id] = []
            req_words = set(re.findall(r"\w+", req.description.lower()))
            for task in self.tasks:
                task_words = set(re.findall(r"\w+", task.title.lower()))
                # If significant overlap, count as covered
                if len(req_words.intersection(task_words)) >= 2:
                    self.mapping[req.id].append(task.id)

    def get_gaps(self) -> List[Requirement]:
        """Return requirements with 0 mapped tasks."""
        return [r for r in self.requirements if not self.mapping.get(r.id)]

    def format_table(self) -> str:
        """Return a formatted markdown table of the matrix."""
        lines = ["| Req ID | Source | Task ID(s) | Status | Coverage |", "| :--- | :--- | :--- | :--- | :--- |"]
        for req in self.requirements:
            task_ids = self.mapping.get(req.id, [])
            tid_str = ", ".join(f"#{tid}" for tid in task_ids) if task_ids else "-"
            
            coverage = "COV" if task_ids else "MISSING"
            # In progress or done based on tasks
            status = "pending"
            if task_ids:
                # simplify: if any task is done, mark as partial/complete
                # status = self._aggregate_task_status(task_ids)
                status = "mapped"

            lines.append(f"| {req.id} | {req.source} | {tid_str} | {status} | {coverage} |")
        
        return "\n".join(lines)
