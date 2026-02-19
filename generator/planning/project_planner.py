"""Project planning module for generating roadmaps and task plans.

Supports two modes:
1. README-based roadmap generation
2. Manual task-specific plan generation
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from generator.ai.factory import create_ai_client

logger = logging.getLogger(__name__)

ROADMAP_SYSTEM_PROMPT = (
    "You are a project planner. Generate a roadmap using ONLY the provided "
    "README content and extracted features. Do NOT reference external projects, "
    "tools, frameworks, or integrations not explicitly mentioned in the README. "
    "Do NOT invent project names, product names, or service names. "
    "Every task and phase must trace back to content in the README."
)


@dataclass
class Task:
    """Represents a single task in a plan."""

    description: str
    subtasks: List[str]
    completed: bool = False

    def to_markdown(self, level: int = 0) -> str:
        """Convert task to markdown checkbox format."""
        indent = "  " * level
        checkbox = "[x]" if self.completed else "[ ]"
        lines = [f"{indent}- {checkbox} {self.description}"]

        for subtask in self.subtasks:
            lines.append(f"{indent}  - [ ] {subtask}")

        return "\n".join(lines)


@dataclass
class Phase:
    """Represents a phase containing multiple tasks."""

    name: str
    description: str
    tasks: List[Task]

    def to_markdown(self) -> str:
        """Convert phase to markdown format."""
        lines = [f"## {self.name}", ""]
        if self.description:
            lines.append(self.description)
            lines.append("")

        for task in self.tasks:
            lines.append(task.to_markdown())
            lines.append("")

        return "\n".join(lines)


@dataclass
class Plan:
    """Represents a complete project plan."""

    title: str
    description: str
    phases: List[Phase]

    def to_markdown(self) -> str:
        """Convert plan to markdown format."""
        lines = [f"# {self.title}", "", self.description, "", "---", ""]

        for phase in self.phases:
            lines.append(phase.to_markdown())

        return "\n".join(lines)

    def to_mermaid(self) -> str:
        """Convert plan to Mermaid gantt/graph diagram embedded in markdown."""
        lines = [
            f"# {self.title}",
            "",
            self.description,
            "",
            "---",
            "",
            "## Roadmap Diagram",
            "",
            "```mermaid",
            "graph TD",
        ]

        # Build node IDs and connections
        prev_phase_id = None
        for phase_idx, phase in enumerate(self.phases):
            phase_id = f"P{phase_idx + 1}"
            phase_label = phase.name.replace('"', "'")
            lines.append(f'    {phase_id}["{phase_label}"]')

            for task_idx, task in enumerate(phase.tasks):
                task_id = f"T{phase_idx + 1}_{task_idx + 1}"
                task_label = task.description.replace('"', "'")[:60]
                status = "[x]" if task.completed else "[ ]"
                lines.append(f'    {task_id}["{status} {task_label}"]')
                lines.append(f"    {phase_id} --> {task_id}")

            if prev_phase_id:
                lines.append(f"    {prev_phase_id} --> {phase_id}")
            prev_phase_id = phase_id

        lines.append("```")
        lines.append("")

        # Also include the full markdown task list below the diagram
        lines.append("---")
        lines.append("")
        lines.append("## Task Details")
        lines.append("")
        for phase in self.phases:
            lines.append(phase.to_markdown())

        return "\n".join(lines)

    def save(self, filepath: Path, fmt: str = "markdown") -> None:
        """Save plan to file in the specified format."""
        if fmt == "mermaid":
            filepath.write_text(self.to_mermaid(), encoding="utf-8")
        else:
            filepath.write_text(self.to_markdown(), encoding="utf-8")


class ProjectPlanner:
    """Generate project plans from README or manual queries."""

    def __init__(
        self, provider: str = "gemini", api_key: Optional[str] = None, client=None
    ):
        """Initialize planner with AI client.

        Args:
            provider: AI provider ('gemini' or 'groq')
            api_key: Optional API key
            client: Optional pre-configured AI client (for testing)
        """
        self.client = client or create_ai_client(provider=provider, api_key=api_key)

    def generate_roadmap_from_readme(
        self, readme_path: Path, project_path: Optional[Path] = None
    ) -> Plan:
        """Generate project roadmap from README.md.

        Args:
            readme_path: Path to README.md
            project_path: Optional project root for context

        Returns:
            Plan with phases and tasks
        """
        # Read README
        readme_content = readme_path.read_text(encoding="utf-8")

        # Extract features and goals
        features = self._extract_features_from_readme(readme_content)

        # Build prompt for AI
        prompt = self._build_roadmap_prompt(readme_content, features, project_path)

        # Generate plan with AI
        try:
            response = self.client.generate(
                prompt,
                temperature=0.5,
                max_tokens=3000,
                system_message=ROADMAP_SYSTEM_PROMPT,
            )
            plan = self._parse_roadmap_response(response, readme_content)
        except Exception:
            # Fallback to template-based roadmap
            plan = self._generate_template_roadmap(features, readme_content)

        return plan

    def generate_task_plan(
        self, query: str, project_path: Optional[Path] = None
    ) -> Plan:
        """Generate task-specific plan from query.

        Args:
            query: Task description (e.g., "Fix config bug", "Add Redis cache")
            project_path: Optional project root for context

        Returns:
            Plan with implementation tasks
        """
        # Build context from project
        context = ""
        if project_path:
            context = self._extract_project_context(project_path)

        # Build prompt
        prompt = self._build_task_prompt(query, context)

        # Generate plan with AI
        try:
            response = self.client.generate(prompt, temperature=0.5, max_tokens=2500)
            plan = self._parse_task_response(response, query)
        except Exception:
            # Fallback to template-based plan
            plan = self._generate_template_task_plan(query)

        return plan

    def _extract_features_from_readme(self, readme_content: str) -> List[str]:
        """Extract features from README content."""
        features = []

        # Look for Features section
        features_match = re.search(
            r"##\s+Features.*?\n(.*?)(?=\n##|\Z)",
            readme_content,
            re.DOTALL | re.IGNORECASE,
        )

        if features_match:
            features_text = features_match.group(1)
            # Extract bullet points
            for line in features_text.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    feature = line.lstrip("-*").strip()
                    if feature and len(feature) > 5:
                        features.append(feature)

        # Also look for TODO or Roadmap sections
        todo_match = re.search(
            r"##\s+(TODO|Roadmap|Planned Features).*?\n(.*?)(?=\n##|\Z)",
            readme_content,
            re.DOTALL | re.IGNORECASE,
        )

        if todo_match:
            todo_text = todo_match.group(2)
            for line in todo_text.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    item = line.lstrip("-*").strip()
                    if item and len(item) > 5 and item not in features:
                        features.append(item)

        return features[:10]  # Limit to top 10 features

    def _extract_project_context(self, project_path: Path) -> str:
        """Extract project context for task planning."""
        context_parts = []

        # Check for key files
        if (project_path / "README.md").exists():
            readme = (project_path / "README.md").read_text(encoding="utf-8")[:1000]
            context_parts.append(f"**README excerpt:**\n{readme}")

        # Check for package.json or requirements.txt
        if (project_path / "package.json").exists():
            context_parts.append("**Stack:** Node.js project")
        elif (project_path / "requirements.txt").exists():
            context_parts.append("**Stack:** Python project")

        return "\n\n".join(context_parts) if context_parts else "No additional context"

    def _build_roadmap_prompt(
        self, readme_content: str, features: List[str], project_path: Optional[Path]
    ) -> str:
        """Build prompt for roadmap generation with strict context isolation."""
        features_list = (
            "\n".join(f"- {f}" for f in features) if features else "No features listed"
        )

        prompt = f"""Generate a project roadmap using ONLY the content below.

<readme>
{readme_content[:2000]}
</readme>

<extracted_features>
{features_list}
</extracted_features>

BANNED: Do not reference any project, tool, service, or framework not mentioned in the README above. Do not invent names.

Format the roadmap exactly as:

# Project Roadmap: [Project Name from README]

[Brief description]

---

## Phase 1: [Phase Name]
[Brief description of this phase]

- [ ] Task 1: [Description]
  - [ ] Subtask 1.1
  - [ ] Subtask 1.2
- [ ] Task 2: [Description]

## Phase 2: [Phase Name]
...

Requirements:
1. Organize features into 3-5 logical phases
2. Each phase should have 3-7 tasks
3. Add 2-4 subtasks for complex tasks
4. Use clear, actionable language
5. Order phases by dependency (foundation first)
6. Every task must trace back to the README content
"""
        return prompt

    def _build_task_prompt(self, query: str, context: str) -> str:
        """Build prompt for task plan generation."""
        prompt = f"""# Generate Task Implementation Plan

**Task:** {query}

**Project Context:**
{context}

## Your Task

Create a detailed implementation plan for this specific task.

**Format:**
```markdown
# Task: {query}

[Brief description of what needs to be done]

---

## Phase 1: Preparation
- [ ] Task 1: [Description]
  - [ ] Subtask 1.1
  - [ ] Subtask 1.2

## Phase 2: Implementation
- [ ] Task 1: [Description]

## Phase 3: Testing & Verification
- [ ] Task 1: [Description]
```

**Requirements:**
1. Break down into 3-4 phases (Preparation, Implementation, Testing, Documentation)
2. Each phase should have 2-5 tasks
3. Add subtasks for complex steps
4. Include specific file names, commands, or code references
5. Be actionable and concrete

Generate the plan now:
"""
        return prompt

    def _detect_hallucinations(
        self, roadmap_text: str, readme_content: str
    ) -> List[str]:
        """Find capitalized multi-word terms in roadmap that don't appear in README."""
        hallucinated = []
        readme_lower = readme_content.lower()

        # Find capitalized terms that look like proper nouns / project names
        # Match PascalCase, hyphenated names, or multi-word capitalized phrases
        candidates = set(
            re.findall(r"\b[A-Z][a-zA-Z]+-[A-Z][a-zA-Z]+\b", roadmap_text)
        )  # e.g. DevLens-AI
        candidates |= set(
            re.findall(r"\b[A-Z][a-z]+[A-Z][a-zA-Z]+\b", roadmap_text)
        )  # e.g. GithubAgent

        for term in candidates:
            if term.lower() not in readme_lower:
                hallucinated.append(term)

        return hallucinated

    def _parse_roadmap_response(self, response: str, readme_content: str) -> Plan:
        """Parse AI response into Plan object."""
        # Check for hallucinated terms before accepting the response
        hallucinations = self._detect_hallucinations(response, readme_content)
        if hallucinations:
            logger.warning(
                "Hallucinated terms detected in roadmap: %s. Falling back to template.",
                ", ".join(hallucinations),
            )
            features = self._extract_features_from_readme(readme_content)
            return self._generate_template_roadmap(features, readme_content)

        # Extract title
        title_match = re.search(r"^#\s+(.+)$", response, re.MULTILINE)
        title = title_match.group(1) if title_match else "Project Roadmap"

        # Extract description (text between title and first phase)
        desc_match = re.search(
            r"^#\s+.+\n+(.+?)(?=\n##)", response, re.DOTALL | re.MULTILINE
        )
        description = desc_match.group(1).strip() if desc_match else ""
        description = description.replace("---", "").strip()

        # Extract phases
        phases = self._extract_phases_from_markdown(response)

        return Plan(title=title, description=description, phases=phases)

    def _parse_task_response(self, response: str, query: str) -> Plan:
        """Parse AI response for task plan."""
        title = f"Plan: {query}"

        # Extract description
        desc_match = re.search(
            r"^#\s+.+\n+(.+?)(?=\n##)", response, re.DOTALL | re.MULTILINE
        )
        description = (
            desc_match.group(1).strip()
            if desc_match
            else f"Implementation plan for: {query}"
        )
        description = description.replace("---", "").strip()

        # Extract phases
        phases = self._extract_phases_from_markdown(response)

        return Plan(title=title, description=description, phases=phases)

    def _extract_phases_from_markdown(self, markdown: str) -> List[Phase]:
        """Extract phases from markdown content."""
        phases = []

        # Find all phase sections (## headers)
        phase_pattern = r"##\s+(.+?)\n(.*?)(?=\n##|\Z)"
        phase_matches = re.finditer(phase_pattern, markdown, re.DOTALL)

        for match in phase_matches:
            phase_name = match.group(1).strip()
            phase_content = match.group(2).strip()

            # Extract phase description (text before first task)
            desc_match = re.match(r"^(.+?)(?=\n-|\Z)", phase_content, re.DOTALL)
            phase_desc = desc_match.group(1).strip() if desc_match else ""

            # Extract tasks
            tasks = self._extract_tasks_from_content(phase_content)

            phases.append(Phase(name=phase_name, description=phase_desc, tasks=tasks))

        return phases

    def _extract_tasks_from_content(self, content: str) -> List[Task]:
        """Extract tasks from phase content."""
        tasks = []
        lines = content.split("\n")

        current_task = None
        for line in lines:
            line = line.strip()

            # Main task (starts with - [ ] or - [x])
            if re.match(r"^-\s+\[([ x])\]\s+(.+)$", line):
                if current_task:
                    tasks.append(current_task)

                match = re.match(r"^-\s+\[([ x])\]\s+(.+)$", line)
                completed = match.group(1) == "x"
                description = match.group(2).strip()
                current_task = Task(
                    description=description, subtasks=[], completed=completed
                )

            # Subtask (starts with  - [ ] - indented)
            elif current_task and re.match(r"^\s+-\s+\[([ x])\]\s+(.+)$", line):
                match = re.match(r"^\s+-\s+\[([ x])\]\s+(.+)$", line)
                subtask = match.group(2).strip()
                current_task.subtasks.append(subtask)

        if current_task:
            tasks.append(current_task)

        return tasks

    def _generate_template_roadmap(
        self, features: List[str], readme_content: str
    ) -> Plan:
        """Generate template-based roadmap when AI is unavailable."""
        # Extract project name from README
        name_match = re.search(r"^#\s+(.+)$", readme_content, re.MULTILINE)
        project_name = name_match.group(1).strip() if name_match else "Project"

        phases = [
            Phase(
                name="Phase 1: Foundation",
                description="Set up core infrastructure and architecture",
                tasks=[
                    Task(
                        "Set up project structure",
                        ["Create directory layout", "Initialize configuration"],
                    ),
                    Task(
                        "Configure development environment",
                        ["Set up linting", "Configure testing framework"],
                    ),
                    Task(
                        "Implement core modules",
                        ["Create base classes", "Set up utilities"],
                    ),
                ],
            ),
            Phase(
                name="Phase 2: Feature Implementation",
                description="Implement main features",
                tasks=[
                    (
                        Task(
                            f"Implement {features[0]}",
                            ["Design API", "Write implementation", "Add tests"],
                        )
                        if features
                        else Task(
                            "Implement core features",
                            ["Design API", "Write implementation", "Add tests"],
                        )
                    ),
                ],
            ),
            Phase(
                name="Phase 3: Testing & Documentation",
                description="Ensure quality and document the project",
                tasks=[
                    Task(
                        "Write comprehensive tests",
                        ["Unit tests", "Integration tests", "E2E tests"],
                    ),
                    Task(
                        "Update documentation", ["API docs", "User guide", "Examples"]
                    ),
                ],
            ),
        ]

        return Plan(
            title=f"Project Roadmap: {project_name}",
            description="High-level roadmap for project development",
            phases=phases,
        )

    def _generate_template_task_plan(self, query: str) -> Plan:
        """Generate template-based task plan when AI is unavailable."""
        phases = [
            Phase(
                name="Phase 1: Preparation",
                description="Understand requirements and prepare environment",
                tasks=[
                    Task(
                        "Research and understand requirements",
                        ["Review existing code", "Identify dependencies"],
                    ),
                    Task(
                        "Set up development environment",
                        ["Install dependencies", "Configure tools"],
                    ),
                ],
            ),
            Phase(
                name="Phase 2: Implementation",
                description="Implement the solution",
                tasks=[
                    Task(
                        "Implement core functionality",
                        ["Write main code", "Handle edge cases"],
                    ),
                    Task("Add error handling", ["Validate inputs", "Add logging"]),
                ],
            ),
            Phase(
                name="Phase 3: Testing",
                description="Test and verify the implementation",
                tasks=[
                    Task("Write tests", ["Unit tests", "Integration tests"]),
                    Task("Manual verification", ["Test manually", "Check edge cases"]),
                ],
            ),
        ]

        return Plan(
            title=f"Task: {query}",
            description=f"Implementation plan for: {query}",
            phases=phases,
        )
