"""SubTask — the atomic unit of a decomposed feature task."""

from typing import List

from pydantic import BaseModel, Field


class SubTask(BaseModel):
    """A single decomposed subtask."""

    id: int = Field(description="Sequential subtask ID")
    title: str = Field(description="Short imperative title")
    goal: str = Field(description="What this subtask achieves")
    skip_consequence: str = Field(
        default="",
        description="What is blocked or broken if this task is skipped",
    )
    files: List[str] = Field(default_factory=list, description="Files to create or modify")
    changes: List[str] = Field(default_factory=list, description="Specific changes to make")
    tests: List[str] = Field(default_factory=list, description="Tests to write or verify")
    dependencies: List[int] = Field(default_factory=list, description="IDs of prerequisite subtasks")
    estimated_minutes: int = Field(default=5, ge=1, le=10, description="Time estimate (2-5 min target)")
    type: str = Field(default="md", description="Task file extension (md or py)")
