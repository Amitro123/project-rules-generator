"""AI-powered task decomposition into actionable subtasks."""

import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SubTask(BaseModel):
    """A single decomposed subtask."""

    id: int = Field(description="Sequential subtask ID")
    title: str = Field(description="Short imperative title")
    goal: str = Field(description="What this subtask achieves")
    files: List[str] = Field(default_factory=list, description="Files to create or modify")
    changes: List[str] = Field(default_factory=list, description="Specific changes to make")
    tests: List[str] = Field(default_factory=list, description="Tests to write or verify")
    dependencies: List[int] = Field(default_factory=list, description="IDs of prerequisite subtasks")
    estimated_minutes: int = Field(default=5, ge=1, le=10, description="Time estimate (2-5 min target)")


class TaskDecomposer:
    """Break a high-level task into subtasks using an AI model."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

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
        return self._parse_response(raw, user_task)

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

        text = Path(design_path).read_text(encoding='utf-8')
        design = Design.from_markdown(text)

        prompt = self._build_design_prompt(design, project_context)
        raw = self._call_llm(prompt)
        tasks = self._parse_response(raw, design.title)

        # If AI returned only the fallback, build tasks from design structure
        if len(tasks) == 1 and tasks[0].title == design.title[:80]:
            tasks = self._tasks_from_design(design)

        return tasks

    @staticmethod
    def _tasks_from_design(design) -> 'List[SubTask]':
        """Build subtasks directly from design structure (no AI needed)."""
        tasks: List[SubTask] = []
        task_id = 1

        # One task per architecture decision
        for dec in design.architecture_decisions:
            tasks.append(SubTask(
                id=task_id,
                title=f"Implement {dec.title}",
                goal=f"Implement {dec.choice} for {dec.title}",
                changes=[f"Apply: {dec.choice}"],
                estimated_minutes=5,
                dependencies=[t.id for t in tasks[-1:]] if tasks else [],
            ))
            task_id += 1

        # One task per data model
        for model_desc in design.data_models:
            tasks.append(SubTask(
                id=task_id,
                title=f"Create data model: {model_desc[:40]}",
                goal=f"Define {model_desc}",
                estimated_minutes=3,
                dependencies=[1] if tasks else [],
            ))
            task_id += 1

        # One task per API contract
        for contract in design.api_contracts:
            tasks.append(SubTask(
                id=task_id,
                title=f"Implement endpoint: {contract[:40]}",
                goal=contract,
                estimated_minutes=4,
                dependencies=[t.id for t in tasks[-1:]] if tasks else [],
            ))
            task_id += 1

        # A task for each success criterion (as verification)
        if design.success_criteria:
            deps = [t.id for t in tasks]
            tasks.append(SubTask(
                id=task_id,
                title="Verify success criteria",
                goal="Ensure all success criteria are met",
                tests=design.success_criteria,
                estimated_minutes=5,
                dependencies=deps,
            ))

        if not tasks:
            tasks.append(SubTask(
                id=1,
                title=design.title[:80],
                goal=design.problem_statement or design.title,
                estimated_minutes=5,
            ))

        return tasks

    def _build_design_prompt(self, design, project_context: Optional[Dict]) -> str:
        """Build a prompt that decomposes an existing design into tasks."""
        ctx_block = ''
        if project_context:
            meta = project_context.get('metadata', {})
            ctx_block = (
                f"\n## Project Context\n"
                f"- Type: {meta.get('project_type', 'unknown')}\n"
                f"- Tech: {', '.join(meta.get('tech_stack', []))}\n"
            )

        decisions_block = ''
        for dec in design.architecture_decisions:
            decisions_block += f"- {dec.title}: {dec.choice}\n"

        contracts_block = '\n'.join(f"- {c}" for c in design.api_contracts) if design.api_contracts else 'None'
        models_block = '\n'.join(f"- {m}" for m in design.data_models) if design.data_models else 'None'
        criteria_block = '\n'.join(f"- {c}" for c in design.success_criteria) if design.success_criteria else 'None'

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
    def generate_plan_md(tasks: List[SubTask], user_task: str = '') -> str:
        """Render a list of SubTasks as a PLAN.md markdown document."""
        lines = [
            '# PLAN',
            '',
        ]
        if user_task:
            lines += [f'> **Goal:** {user_task}', '']

        lines += [
            f'**Subtasks:** {len(tasks)}',
            f'**Estimated time:** {sum(t.estimated_minutes for t in tasks)} minutes',
            '',
            '---',
            '',
        ]

        for task in tasks:
            dep_str = ', '.join(f'#{d}' for d in task.dependencies) if task.dependencies else 'none'
            lines += [
                f'## {task.id}. {task.title}',
                '',
                f'**Goal:** {task.goal}',
                f'**Depends on:** {dep_str}',
                f'**Estimated:** ~{task.estimated_minutes} min',
                '',
            ]
            if task.files:
                lines.append('**Files:**')
                for f in task.files:
                    lines.append(f'- `{f}`')
                lines.append('')
            if task.changes:
                lines.append('**Changes:**')
                for c in task.changes:
                    lines.append(f'- {c}')
                lines.append('')
            if task.tests:
                lines.append('**Tests:**')
                for t in task.tests:
                    lines.append(f'- {t}')
                lines.append('')
            lines.append('---')
            lines.append('')

        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        user_task: str,
        project_context: Optional[Dict],
        project_path: Optional[Path],
    ) -> str:
        ctx_block = ''
        if project_context:
            meta = project_context.get('metadata', {})
            ctx_block = (
                f"\n## Project Context\n"
                f"- Type: {meta.get('project_type', 'unknown')}\n"
                f"- Tech: {', '.join(meta.get('tech_stack', []))}\n"
                f"- Has tests: {meta.get('has_tests', False)}\n"
            )
            structure = project_context.get('structure', {})
            if structure.get('entry_points'):
                ctx_block += f"- Entry points: {', '.join(structure['entry_points'])}\n"

        return f"""# Task Decomposition

Break down the following task into small, actionable subtasks.
Each subtask should take 2-5 minutes to complete.

## Task
{user_task}
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

    def _call_llm(self, prompt: str) -> str:
        """Call the AI model. Falls back to empty string if unavailable."""
        if not self.api_key:
            return ''
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=3000,
                ),
            )
            return response.text
        except Exception:
            return ''

    def _parse_response(self, raw: str, user_task: str) -> List[SubTask]:
        """Parse the LLM response into SubTask objects.

        If parsing fails or raw is empty, returns a single fallback subtask.
        """
        if not raw.strip():
            return [SubTask(
                id=1,
                title=user_task[:80],
                goal=user_task,
                estimated_minutes=5,
            )]

        tasks: List[SubTask] = []
        import re

        # Split on numbered headings like "### 1. Title" or "1. Title"
        blocks = re.split(r'###?\s*(\d+)\.\s*', raw)
        # blocks[0] is preamble, then alternating (number, content)
        i = 1
        while i < len(blocks) - 1:
            try:
                task_id = int(blocks[i])
                content = blocks[i + 1]

                title = content.split('\n', 1)[0].strip()
                goal = self._extract_field(content, 'Goal')
                files = [f.strip().strip('`') for f in self._extract_field(content, 'Files').split(',') if f.strip()]
                changes = self._extract_list(content, 'Changes')
                tests = self._extract_list(content, 'Tests')
                deps_str = self._extract_field(content, 'Dependencies')
                deps = [int(d.strip().strip('#')) for d in deps_str.split(',') if d.strip() and d.strip().lower() != 'none']
                est = self._extract_field(content, 'Estimated')
                est_min = int(re.search(r'\d+', est).group()) if re.search(r'\d+', est) else 5
                est_min = max(1, min(est_min, 10))

                tasks.append(SubTask(
                    id=task_id,
                    title=title,
                    goal=goal or title,
                    files=files,
                    changes=changes,
                    tests=tests,
                    dependencies=deps,
                    estimated_minutes=est_min,
                ))
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
        match = re.search(rf'{field}:\s*(.+)', content)
        return match.group(1).strip() if match else ''

    @staticmethod
    def _extract_list(content: str, field: str) -> List[str]:
        """Extract a bullet list after a field heading."""
        import re
        match = re.search(rf'{field}:(.*?)(?=\n\w|\n###|\Z)', content, re.DOTALL)
        if not match:
            return []
        items = re.findall(r'[-*]\s*(.+)', match.group(1))
        return [item.strip() for item in items if item.strip()]
