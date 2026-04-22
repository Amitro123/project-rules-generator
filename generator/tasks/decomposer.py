"""TaskDecomposer — breaks a high-level task into SubTasks using AI."""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from generator.base_generator import ArtifactGenerator
from generator.tasks.subtask_model import SubTask

logger = logging.getLogger(__name__)


class TaskDecomposer(ArtifactGenerator):
    """Break a high-level task into subtasks using an AI model."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, provider: str = "gemini"):
        # Normalise None → "gemini" so provider.upper() never crashes
        self.provider = provider or "gemini"
        self.api_key: Optional[str]
        # Resolve API key: explicit > env var for chosen provider > Gemini fallbacks
        if api_key:
            self.api_key = api_key
        elif self.provider == "gemini":
            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        else:
            self.api_key = os.getenv(f"{self.provider.upper()}_API_KEY")
        self.model_name = model_name

    def decompose(
        self,
        user_task: str,
        project_context: Optional[Dict] = None,
        project_path: Optional[Path] = None,
    ) -> List[SubTask]:
        """Use AI to break down *user_task* into a list of SubTasks."""
        prompt = self._build_prompt(user_task, project_context, project_path)
        raw = self._call_llm(prompt, expect_multiple=True)
        tasks = self._parse_response(raw, user_task)
        tasks = self._ground_task_paths(tasks, project_path)
        return self._ensure_minimum_tasks(tasks, user_task)

    def from_plan(self, plan_path: Path) -> List[SubTask]:
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

    def from_design(self, design_path: Path, project_context: Optional[Dict] = None) -> List[SubTask]:
        """Generate subtasks from an existing DESIGN.md file.

        Falls back to the deterministic ``_tasks_from_design`` builder when the
        LLM under-decomposes.  "Under-decomposed" is defined as fewer than 3
        tasks — previously this check was title-string equality, which missed
        the common failure where the LLM returns one task with a paraphrased
        title and never gets replaced by the structural builder.
        """
        from generator.design_generator import Design

        text = Path(design_path).read_text(encoding="utf-8")
        design = Design.from_markdown(text)

        project_path = Path(design_path).parent
        prompt = self._build_design_prompt(design, project_context, project_path)
        raw = self._call_llm(prompt, expect_multiple=True)
        tasks = self._parse_response(raw, design.title)

        # LLM under-decomposition: a single task (or none) is almost always the
        # fallback stub, regardless of its title.  Prefer the structural build
        # so the user gets one task per architecture decision / contract / model.
        if len(tasks) < 3:
            structural = self._tasks_from_design(design)
            if len(structural) >= len(tasks):
                logger.info("LLM returned %d tasks; using structural fallback (%d)", len(tasks), len(structural))
                tasks = structural

        return self._ground_task_paths(tasks, project_path)

    @staticmethod
    def _tasks_from_design(design) -> List[SubTask]:
        """Build subtasks directly from design structure (no AI needed)."""
        tasks: List[SubTask] = []
        task_id = 1

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
                    id=1, title=design.title[:80], goal=design.problem_statement or design.title, estimated_minutes=5
                )
            )

        return tasks

    def _build_design_prompt(self, design, project_context: Optional[Dict], project_path: Optional[Path] = None) -> str:
        """Build a prompt that decomposes an existing design into tasks."""
        from generator.utils.readme_bridge import build_project_tree

        ctx_block = ""
        if project_path and project_path.is_dir():
            tree = build_project_tree(project_path, max_depth=3, max_items=60)
            ctx_block = f"\n## Project Structure\n```\n{tree[:1200]}\n```\n"

        if project_context:
            meta = project_context.get("metadata", {})
            ctx_block += (
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
    def generate_plan_md(tasks: List[SubTask], user_task: str = "", is_template: bool = False) -> str:
        """Render a list of SubTasks as a PLAN.md markdown document."""
        lines = ["# PLAN", ""]
        if user_task:
            lines += [f"> **Goal:** {user_task}", ""]
        if is_template:
            lines += [
                "> **Note:** This is a generic template plan — configure an AI provider API key",
                "> (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) for task-specific breakdown.",
                "",
            ]

        lines += [
            f"**Subtasks:** {len(tasks)}",
            f"**Estimated time:** {sum(t.estimated_minutes for t in tasks)} minutes",
            "",
            "---",
            "",
        ]

        for task in tasks:
            dep_str = ", ".join(f"#{d}" for d in task.dependencies) if task.dependencies else "none"
            lines += [f"## {task.id}. {task.title}", "", f"**Goal:** {task.goal}"]
            if task.skip_consequence:
                lines.append(f"**Skip consequence:** {task.skip_consequence}")
            lines += [f"**Depends on:** {dep_str}", f"**Estimated:** ~{task.estimated_minutes} min", ""]
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

        The example file path in the rules section is chosen from the actual
        project's top-level source directories when available; this prevents
        the LLM from anchoring on ``src/`` (a common training-data artefact)
        in projects that organise code under ``generator/``, ``lib/``, etc.
        """
        from generator.ai.hardening import discover_source_dirs

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

        # Inject the real project tree so the LLM grounds its file paths in
        # what actually exists — previously only from_design() did this.
        if project_path and project_path.is_dir():
            try:
                from generator.utils.readme_bridge import build_project_tree

                tree = build_project_tree(project_path, max_depth=3, max_items=60)
                ctx_block += (
                    f"\n## Project Structure (use THESE directories in Files fields)\n```\n{tree[:1200]}\n```\n"
                )
            except Exception as exc:  # noqa: BLE001 — tree build is best-effort
                logger.debug("Could not build project tree for prompt: %s", exc)

        # Pick a real top-level dir for the example; fall back to a
        # generic placeholder when discovery fails.
        source_dirs = discover_source_dirs(project_path) if project_path else []
        example_path = f"{source_dirs[0]}/api.py" if source_dirs else "<package>/api.py"

        return (
            f"# Task Decomposition\n\n"
            f"{self._PAIN_FIRST_PREAMBLE}\n"
            f"{self._SKIP_CONSEQUENCE_FORMAT}\n"
            f"Break down the following task into small, actionable subtasks.\n\n"
            f"MANDATORY: Generate EXACTLY 5-8 subtasks, each 2-5 minutes.\n\n"
            f"## Task\n{user_task}\n"
            f"{ctx_block}\n"
            f"## Requirements\n\n"
            f'1. Each subtask MUST specify concrete file paths (e.g. `{example_path}`, not "the API file")\n'
            f"2. File paths MUST use directories that exist in the Project Structure above. "
            f"Do NOT invent `src/` or other paths if they are not listed.\n"
            f"3. Each subtask MUST include code change descriptions with +/- line indicators\n"
            f"4. Each subtask MUST include test commands (e.g. `pytest tests/test_api.py -k test_create`)\n"
            f"5. Subtasks must be ordered by dependency (foundations first, features next, tests last)\n"
            f"6. NO subtask should take longer than 5 minutes\n"
            f"7. Every subtask MUST include a SkipConsequence line\n\n"
            f"## Output Format\n\n"
            f"Return a numbered list of 5-8 subtasks. For each subtask provide:\n"
            f"- Title (short, imperative)\n"
            f"- Goal (one sentence)\n"
            f"- SkipConsequence (what breaks or is blocked if this task is skipped)\n"
            f"- Files to create/modify (SPECIFIC paths from the Project Structure)\n"
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

    def _call_llm(self, prompt: str, *, expect_multiple: bool = False) -> str:
        """Call the AI model with validator-driven retry.

        ``expect_multiple`` switches the validator to require at least three
        ``### N.`` task headings — the most common failure mode for
        ``decompose()`` is returning one task and quitting.  max_tokens is
        increased to 8000 to reduce the chance of mid-task truncation.
        """
        if not self.api_key:
            return ""
        try:
            from generator.ai.factory import create_ai_client
            from generator.ai.hardening import generate_with_validator, require_min_count

            client = create_ai_client(self.provider, api_key=self.api_key)
            validator = require_min_count(r"^###?\s*\d+\.", 3) if expect_multiple else None
            return (
                generate_with_validator(
                    client,
                    prompt,
                    validator=validator,
                    max_tokens=8000,
                    max_retries=1,
                )
                or ""
            )
        except Exception as exc:  # noqa: BLE001 — LLM failures fall back to empty string
            logger.debug("LLM call failed in TaskDecomposer: %s", exc)
            return ""

    @staticmethod
    def _ground_task_paths(tasks: List[SubTask], project_path: Optional[Path]) -> List[SubTask]:
        """Rewrite hallucinated top-level directories in task file paths.

        When an LLM emits ``src/api.py`` but the project has no ``src/``,
        the path is rewritten to use a real source directory (e.g.
        ``generator/api.py``).  Never drops paths — bad paths that cannot be
        repaired stay so the user sees the problem.
        """
        if not project_path or not tasks:
            return tasks
        from generator.ai.hardening import ground_paths

        for task in tasks:
            if task.files:
                task.files = ground_paths(task.files, project_path)
        return tasks

    @classmethod
    def parse_response(cls, raw: str, user_task: str) -> List[SubTask]:
        """Parse an LLM response string into SubTask objects (no AI call needed)."""
        return cls._parse_response_impl(raw, user_task)

    def _parse_response(self, raw: str, user_task: str) -> List[SubTask]:
        """Instance wrapper — delegates to the classmethod implementation."""
        return self.parse_response(raw, user_task)

    @classmethod
    def _parse_response_impl(cls, raw: str, user_task: str) -> List[SubTask]:
        """Parse the LLM response into SubTask objects."""
        if not raw.strip():
            return [SubTask(id=1, title=user_task[:80], goal=user_task, estimated_minutes=5)]

        tasks: List[SubTask] = []

        # Normalise various LLM heading styles to "### N. " before splitting
        normalised = re.sub(r"(?m)^#+\s*(\d+)\.\s*", r"### \1. ", raw)
        normalised = re.sub(r"(?m)^\*+(\d+)\.\*+\s*", r"### \1. ", normalised)
        normalised = re.sub(r"(?m)^(\d+)\)\s+", r"### \1. ", normalised)

        blocks = re.split(r"###?\s*(\d+)\.\s*", normalised)
        i = 1
        while i < len(blocks) - 1:
            try:
                task_id = int(blocks[i])
                content = blocks[i + 1]

                title = content.split("\n", 1)[0].strip()
                goal = cls._extract_field(content, "Goal")
                skip_consequence = cls._extract_field(content, "SkipConsequence")
                files = [f.strip().strip("`") for f in cls._extract_field(content, "Files").split(",") if f.strip()]
                changes = cls._extract_list(content, "Changes")
                tests = cls._extract_list(content, "Tests")
                deps_str = cls._extract_field(content, "Dependencies")
                deps = [
                    int(d.strip().strip("#")) for d in deps_str.split(",") if d.strip() and d.strip().lower() != "none"
                ]
                est = cls._extract_field(content, "Estimated")
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
        """Extract a field value, joining continuation lines.

        Previously used a single-line regex which silently dropped anything
        after the first line, turning a truncated continuation into an empty
        string.  Now captures the full value up to the next ``Field:``-style
        label or a blank line, which is what a human reader would do.
        """
        # Labels we treat as terminators when scanning for continuation lines.
        # Matched case-insensitively so "files:" and "Files:" both stop us.
        terminators = (
            "goal",
            "skipconsequence",
            "skip consequence",
            "files",
            "changes",
            "tests",
            "dependencies",
            "estimated",
        )

        lines = content.split("\n")
        pattern = re.compile(rf"^\s*{re.escape(field)}\s*:\s*(.*)$", re.IGNORECASE)
        collected: List[str] = []
        in_field = False
        for line in lines:
            if in_field:
                stripped = line.strip()
                if not stripped:
                    break  # blank line ends the field
                # Another labelled field starts — stop here
                first_token = stripped.split(":", 1)[0].strip().lower() if ":" in stripped else ""
                if first_token in terminators or stripped.startswith("###"):
                    break
                collected.append(stripped)
                continue
            m = pattern.match(line)
            if m:
                in_field = True
                first = m.group(1).strip()
                if first:
                    collected.append(first)
        return " ".join(collected).strip()

    @staticmethod
    def _extract_list(content: str, field: str) -> List[str]:
        """Extract a bullet list after a field heading."""
        match = re.search(rf"{field}:(.*?)(?=\n\w|\n###|\Z)", content, re.DOTALL)
        if not match:
            return []
        items = re.findall(r"[-*]\s*(.+)", match.group(1))
        return [item.strip() for item in items if item.strip()]

    @staticmethod
    def _ensure_minimum_tasks(tasks: List[SubTask], user_task: str, minimum: int = 3) -> List[SubTask]:
        """Ensure at least *minimum* subtasks by splitting large ones."""
        if len(tasks) >= minimum:
            return tasks

        if len(tasks) == 1 and tasks[0].title == user_task[:80]:
            next_id = 1
            return [
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

        return tasks
