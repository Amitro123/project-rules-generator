"""AI-powered task decomposition into actionable subtasks."""

import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from generator.base_generator import ArtifactGenerator


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
    type: str = Field(default="py", description="Task file extension (e.g. py, md)")


class TaskDecomposer(ArtifactGenerator):
    """Break a high-level task into subtasks using an AI model."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, provider: str = "gemini"):
        self.provider = provider
        self.api_key: Optional[str]
        # Resolve API key: explicit > env var for chosen provider > Gemini fallbacks
        if api_key:
            self.api_key = api_key
        elif provider == "gemini":
            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        else:
            self.api_key = os.getenv(f"{provider.upper()}_API_KEY")
        self.model_name = model_name

    def decompose(
        self,
        user_task: str,
        project_context: Optional[Dict] = None,
        project_path: Optional[Path] = None,
    ) -> List[SubTask]:
        """Use AI to break down *user_task* into a list of SubTasks.

        If no AI key is available, falls back to a simple single-task plan.
        """
        prompt = self._build_prompt(user_task, project_context, project_path)
        raw = self._call_llm(prompt)
        tasks = self._parse_response(raw, user_task)
        return self._ensure_minimum_tasks(tasks, user_task)

    def from_plan(
        self,
        plan_path: Path,
    ) -> List[SubTask]:
        """Parse an existing PLAN.md and convert it back to SubTasks."""
        from generator.planning.plan_parser import PlanParser

        parser = PlanParser()
        status = parser.parse_plan(plan_path)

        tasks: List[SubTask] = []
        task_id = 1
        for phase in status.phases:
            for task_status in phase.tasks:
                tasks.append(
                    SubTask(
                        id=task_id,
                        title=task_status.description,
                        goal=task_status.description,
                        estimated_minutes=5,
                        dependencies=[task_id - 1] if task_id > 1 else [],
                    )
                )
                task_id += 1
        return tasks

    def from_design(
        self,
        design_path: Path,
        project_context: Optional[Dict] = None,
    ) -> List[SubTask]:
        """Generate subtasks from an existing DESIGN.md file.

        Parses the design document sections and either uses AI to decompose
        each section or creates subtasks directly from the design structure.
        """
        from generator.design_generator import Design

        text = Path(design_path).read_text(encoding="utf-8")
        design = Design.from_markdown(text)

        prompt = self._build_design_prompt(design, project_context)
        raw = self._call_llm(prompt)
        tasks = self._parse_response(raw, design.title)

        # If AI returned only the fallback, build tasks from design structure
        if len(tasks) == 1 and tasks[0].title == design.title[:80]:
            tasks = self._tasks_from_design(design)

        return tasks

    @staticmethod
    def _tasks_from_design(design) -> "List[SubTask]":
        """Build subtasks directly from design structure (no AI needed)."""
        tasks: List[SubTask] = []
        task_id = 1

        # One task per architecture decision
        for dec in design.architecture_decisions:
            tasks.append(
                SubTask(
                    id=task_id,
                    title=f"Implement {dec.title}",
                    goal=f"Implement {dec.choice} for {dec.title}",
                    changes=[f"Apply: {dec.choice}"],
                    estimated_minutes=5,
                    dependencies=[t.id for t in tasks[-1:]] if tasks else [],
                )
            )
            task_id += 1

        # One task per data model
        for model_desc in design.data_models:
            tasks.append(
                SubTask(
                    id=task_id,
                    title=f"Create data model: {model_desc[:40]}",
                    goal=f"Define {model_desc}",
                    estimated_minutes=3,
                    dependencies=[1] if tasks else [],
                )
            )
            task_id += 1

        # One task per API contract
        for contract in design.api_contracts:
            tasks.append(
                SubTask(
                    id=task_id,
                    title=f"Implement endpoint: {contract[:40]}",
                    goal=contract,
                    estimated_minutes=4,
                    dependencies=[t.id for t in tasks[-1:]] if tasks else [],
                )
            )
            task_id += 1

        # A task for each success criterion (as verification)
        if design.success_criteria:
            deps = [t.id for t in tasks]
            tasks.append(
                SubTask(
                    id=task_id,
                    title="Verify success criteria",
                    goal="Ensure all success criteria are met",
                    tests=design.success_criteria,
                    estimated_minutes=5,
                    dependencies=deps,
                )
            )

        if not tasks:
            tasks.append(
                SubTask(
                    id=1,
                    title=design.title[:80],
                    goal=design.problem_statement or design.title,
                    estimated_minutes=5,
                )
            )

        return tasks

    def _build_design_prompt(self, design, project_context: Optional[Dict]) -> str:
        """Build a prompt that decomposes an existing design into tasks."""
        ctx_block = ""
        if project_context:
            meta = project_context.get("metadata", {})
            ctx_block = (
                f"\n## Project Context\n"
                f"- Type: {meta.get('project_type', 'unknown')}\n"
                f"- Tech: {', '.join(meta.get('tech_stack', []))}\n"
            )

        decisions_block = ""
        for dec in design.architecture_decisions:
            decisions_block += f"- {dec.title}: {dec.choice}\n"

        contracts_block = "\n".join(f"- {c}" for c in design.api_contracts) if design.api_contracts else "None"
        models_block = "\n".join(f"- {m}" for m in design.data_models) if design.data_models else "None"
        criteria_block = "\n".join(f"- {c}" for c in design.success_criteria) if design.success_criteria else "None"

        return f"""# Task Decomposition from Design

Break down the following technical design into small, actionable subtasks.
Each subtask should take 2-5 minutes to complete.

## Design: {design.title}

### Problem
{design.problem_statement}

### Architecture Decisions
{decisions_block}

### API Contracts
{contracts_block}

### Data Models
{models_block}

### Success Criteria
{criteria_block}
{ctx_block}
## Output Format

Return a numbered list of subtasks. For each subtask provide:
- Title (short, imperative)
- Goal (one sentence)
- Files to create/modify
- Specific changes
- Tests to write
- Dependencies (which subtask IDs must finish first)
- Estimated minutes (2-5)

Format each subtask as:

### <number>. <title>
Goal: <goal>
Files: <comma-separated file paths>
Changes: <bullet list>
Tests: <bullet list>
Dependencies: <comma-separated subtask numbers or "none">
Estimated: <minutes>

Generate the subtasks now:
"""

    # ------------------------------------------------------------------
    # Plan rendering
    # ------------------------------------------------------------------

    @staticmethod
    def generate_plan_md(tasks: List[SubTask], user_task: str = "") -> str:
        """Render a list of SubTasks as a PLAN.md markdown document."""
        lines = [
            "# PLAN",
            "",
        ]
        if user_task:
            lines += [f"> **Goal:** {user_task}", ""]

        lines += [
            f"**Subtasks:** {len(tasks)}",
            f"**Estimated time:** {sum(t.estimated_minutes for t in tasks)} minutes",
            "",
            "---",
            "",
        ]

        for task in tasks:
            dep_str = ", ".join(f"#{d}" for d in task.dependencies) if task.dependencies else "none"
            lines += [
                f"## {task.id}. {task.title}",
                "",
                f"**Goal:** {task.goal}",
            ]
            if task.skip_consequence:
                lines.append(f"**Skip consequence:** {task.skip_consequence}")
            lines += [
                f"**Depends on:** {dep_str}",
                f"**Estimated:** ~{task.estimated_minutes} min",
                "",
            ]
            if task.files:
                lines.append("**Files:**")
                for f in task.files:
                    lines.append(f"- `{f}`")
                lines.append("")
            if task.changes:
                lines.append("**Changes:**")
                for c in task.changes:
                    lines.append(f"- {c}")
                lines.append("")
            if task.tests:
                lines.append("**Tests:**")
                for t in task.tests:
                    lines.append(f"- {t}")
                lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        user_task: str,
        project_context: Optional[Dict] = None,
        project_path: Optional[Path] = None,
    ) -> str:
        """Build the task-decomposition prompt.

        Embeds _PAIN_FIRST_PREAMBLE and _SKIP_CONSEQUENCE_FORMAT so every
        generated subtask carries a SkipConsequence explaining what breaks
        if that task is omitted.
        """
        ctx_block = ""
        if project_context:
            meta = project_context.get("metadata", {})
            ctx_block = (
                f"\n## Project Context\n"
                f"- Type: {meta.get('project_type', 'unknown')}\n"
                f"- Tech: {', '.join(meta.get('tech_stack', []))}\n"
                f"- Has tests: {meta.get('has_tests', False)}\n"
            )
            structure = project_context.get("structure", {})
            if structure.get("entry_points"):
                ctx_block += f"- Entry points: {', '.join(structure['entry_points'])}\n"

        return (
            f"# Task Decomposition\n\n"
            f"{self._PAIN_FIRST_PREAMBLE}\n"
            f"{self._SKIP_CONSEQUENCE_FORMAT}\n"
            f"Break down the following task into small, actionable subtasks.\n\n"
            f"MANDATORY: Generate EXACTLY 5-8 subtasks, each 2-5 minutes.\n\n"
            f"## Task\n{user_task}\n"
            f"{ctx_block}\n"
            f"## Requirements\n\n"
            f'1. Each subtask MUST specify concrete file paths (e.g. `src/api.py`, not "the API file")\n'
            f"2. Each subtask MUST include code change descriptions with +/- line indicators\n"
            f"3. Each subtask MUST include test commands (e.g. `pytest tests/test_api.py -k test_create`)\n"
            f"4. Subtasks must be ordered by dependency (foundations first, features next, tests last)\n"
            f"5. NO subtask should take longer than 5 minutes\n"
            f"6. Every subtask MUST include a SkipConsequence line\n\n"
            f"## Output Format\n\n"
            f"Return a numbered list of 5-8 subtasks. For each subtask provide:\n"
            f"- Title (short, imperative)\n"
            f"- Goal (one sentence)\n"
            f"- SkipConsequence (what breaks or is blocked if this task is skipped)\n"
            f"- Files to create/modify (SPECIFIC paths)\n"
            f"- Changes (with code snippets showing what to add/modify)\n"
            f"- Tests (specific pytest/test commands to verify)\n"
            f"- Dependencies (which subtask IDs must finish first)\n"
            f"- Estimated minutes (2-5)\n\n"
            f"Format each subtask as:\n\n"
            f"### <number>. <title>\n"
            f"Goal: <goal>\n"
            f"SkipConsequence: <what breaks if skipped>\n"
            f"Files: <comma-separated file paths>\n"
            f"Changes: <bullet list with code snippets>\n"
            f"Tests: <bullet list with test commands>\n"
            f'Dependencies: <comma-separated subtask numbers or "none">\n'
            f"Estimated: <minutes>\n\n"
            f"Generate exactly 5-8 subtasks now:\n"
        )

    def _call_llm(self, prompt: str) -> str:
        """Call the AI model via the shared factory. Falls back to empty string if unavailable."""
        if not self.api_key:
            return ""
        try:
            from generator.ai.factory import create_ai_client

            client = create_ai_client(self.provider, api_key=self.api_key)
            return client.generate(prompt, max_tokens=3000) or ""
        except Exception:
            return ""

    def _parse_response(self, raw: str, user_task: str) -> List[SubTask]:
        """Parse the LLM response into SubTask objects.

        If parsing fails or raw is empty, returns a single fallback subtask.
        """
        if not raw.strip():
            return [
                SubTask(
                    id=1,
                    title=user_task[:80],
                    goal=user_task,
                    estimated_minutes=5,
                )
            ]

        tasks: List[SubTask] = []
        import re

        # Split on numbered headings like "### 1. Title" or "1. Title"
        blocks = re.split(r"###?\s*(\d+)\.\s*", raw)
        # blocks[0] is preamble, then alternating (number, content)
        i = 1
        while i < len(blocks) - 1:
            try:
                task_id = int(blocks[i])
                content = blocks[i + 1]

                title = content.split("\n", 1)[0].strip()
                goal = self._extract_field(content, "Goal")
                skip_consequence = self._extract_field(content, "SkipConsequence")
                files = [f.strip().strip("`") for f in self._extract_field(content, "Files").split(",") if f.strip()]
                changes = self._extract_list(content, "Changes")
                tests = self._extract_list(content, "Tests")
                deps_str = self._extract_field(content, "Dependencies")
                deps = [
                    int(d.strip().strip("#")) for d in deps_str.split(",") if d.strip() and d.strip().lower() != "none"
                ]
                est = self._extract_field(content, "Estimated")
                _est_m = re.search(r"\d+", est)
                est_min = int(_est_m.group()) if _est_m else 5
                est_min = max(1, min(est_min, 10))

                tasks.append(
                    SubTask(
                        id=task_id,
                        title=title,
                        goal=goal or title,
                        skip_consequence=skip_consequence,
                        files=files,
                        changes=changes,
                        tests=tests,
                        dependencies=deps,
                        estimated_minutes=est_min,
                    )
                )
            except (ValueError, AttributeError):
                pass
            i += 2

        if not tasks:
            return [SubTask(id=1, title=user_task[:80], goal=user_task, estimated_minutes=5)]

        return tasks

    @staticmethod
    def _extract_field(content: str, field: str) -> str:
        """Extract a single-line field value like 'Goal: ...'."""
        import re

        match = re.search(rf"{field}:\s*(.+)", content)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_list(content: str, field: str) -> List[str]:
        """Extract a bullet list after a field heading."""
        import re

        match = re.search(rf"{field}:(.*?)(?=\n\w|\n###|\Z)", content, re.DOTALL)
        if not match:
            return []
        items = re.findall(r"[-*]\s*(.+)", match.group(1))
        return [item.strip() for item in items if item.strip()]

    @staticmethod
    def _ensure_minimum_tasks(tasks: List["SubTask"], user_task: str, minimum: int = 3) -> List["SubTask"]:
        """Ensure at least *minimum* subtasks by splitting large ones.

        When the AI returns fewer tasks than desired, pad with planning,
        implementation, and verification subtasks derived from the original task.
        """
        if len(tasks) >= minimum:
            return tasks

        # If we have a single fallback task, expand it into a standard pattern
        if len(tasks) == 1 and tasks[0].title == user_task[:80]:
            next_id = 1
            expanded = [
                SubTask(
                    id=next_id,
                    title="Research and plan approach",
                    goal=f"Understand requirements for: {user_task[:60]}",
                    estimated_minutes=3,
                    dependencies=[],
                ),
                SubTask(
                    id=next_id + 1,
                    title="Implement core changes",
                    goal=f"Make primary code changes for: {user_task[:60]}",
                    estimated_minutes=5,
                    dependencies=[next_id],
                ),
                SubTask(
                    id=next_id + 2,
                    title="Write tests",
                    goal="Add tests covering the new behaviour",
                    estimated_minutes=4,
                    dependencies=[next_id + 1],
                ),
                SubTask(
                    id=next_id + 3,
                    title="Update documentation",
                    goal="Update relevant docs and comments",
                    estimated_minutes=2,
                    dependencies=[next_id + 1],
                ),
                SubTask(
                    id=next_id + 4,
                    title="Verify and clean up",
                    goal="Run full test suite, fix lint, confirm success",
                    estimated_minutes=3,
                    dependencies=[next_id + 2, next_id + 3],
                ),
            ]
            return expanded

        return tasks
