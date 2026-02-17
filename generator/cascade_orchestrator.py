"""
CASCADE ORCHESTRATOR: PLAN → DESIGN → TASKS
============================================

Cowork-powered cascade system that generates:
1. PLAN.md (MASTER) - Detailed plan with specific files, times, AC
2. DESIGN.md - Feeds from PLAN (API contracts, architecture)
3. task.yaml - Feeds from PLAN (precise task breakdown)

Key Innovation: PLAN drives everything with specificity!
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


@dataclass
class Task:
    """Single task with Cowork-level specificity."""

    title: str
    estimate_minutes: int
    files: List[str] = field(default_factory=list)  # Specific files!
    depends_on: List[int] = field(default_factory=list)  # Task dependencies
    steps: List[str] = field(default_factory=list)
    verification: str = ""  # How to verify (pytest --cov=80%)
    acceptance_criteria: str = ""  # Measurable AC (Cache hit >80%)
    risks: List[str] = field(default_factory=list)


@dataclass
class PlanMetadata:
    """MASTER PLAN metadata."""

    project_name: str
    goal: str
    total_estimate_minutes: int
    tech_stack: List[str] = field(default_factory=list)
    overall_risks: List[str] = field(default_factory=list)


@dataclass
class DesignComponent:
    """Design component extracted from PLAN."""

    name: str
    type: str  # API, Component, Module, etc.
    description: str
    interfaces: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class CascadeOrchestrator:
    """
    Orchestrates the CASCADE: PLAN → DESIGN → TASKS

    This is the brain that ensures:
    - PLAN has specific files (not generic "core")
    - Tasks have measurable AC
    - Design feeds from PLAN
    - Tasks feed from PLAN
    """

    def __init__(self, project_path: Path):
        """Initialize with project path."""
        self.project_path = project_path
        self._project_files: Optional[List[Path]] = None

    def create_cascade(
        self,
        goal: str,
        readme_content: str,
        context: Optional[Dict] = None,
    ) -> Tuple[str, str, str]:
        """
        Create complete CASCADE with Cowork specificity.

        Args:
            goal: What to accomplish (e.g., "Add Redis caching layer")
            readme_content: Project README
            context: Additional context from analysis

        Returns:
            Tuple of (plan_content, design_content, tasks_yaml)
        """

        # 1. Analyze project to get SPECIFIC files
        project_files = self._scan_project_files()

        # 2. Generate MASTER PLAN with specificity
        plan_metadata, tasks = self._generate_plan(
            goal, readme_content, project_files, context
        )

        # 3. Generate PLAN.md content
        plan_content = self._generate_plan_content(plan_metadata, tasks)

        # 4. Generate DESIGN.md FROM plan
        design_content = self._generate_design_from_plan(plan_metadata, tasks)

        # 5. Generate task.yaml FROM plan
        tasks_yaml = self._generate_tasks_yaml_from_plan(plan_metadata, tasks)

        return plan_content, design_content, tasks_yaml

    def _scan_project_files(self) -> List[Path]:
        """Scan project for actual files (for specificity!)."""
        if self._project_files:
            return self._project_files

        files = []

        # Common source directories
        source_dirs = ["src", "app", "api", "lib", "components", "services"]

        for dir_name in source_dirs:
            dir_path = self.project_path / dir_name
            if dir_path.exists():
                for ext in [".py", ".ts", ".tsx", ".js", ".jsx"]:
                    files.extend(dir_path.rglob(f"*{ext}"))

        # Also check root-level files
        for ext in [".py", ".ts", ".tsx", ".js", ".jsx"]:
            files.extend(self.project_path.glob(f"*{ext}"))

        self._project_files = files
        return files

    def _generate_plan(
        self,
        goal: str,
        readme_content: str,
        project_files: List[Path],
        context: Optional[Dict],
    ) -> Tuple[PlanMetadata, List[Task]]:
        """Generate MASTER PLAN with Cowork specificity."""

        # Extract project info
        project_name = self.project_path.name
        tech_stack = self._detect_tech_stack(readme_content, context)

        # Parse goal into tasks
        tasks = self._decompose_goal_into_tasks(
            goal, tech_stack, project_files, context
        )

        # Calculate total estimate
        total_estimate = sum(task.estimate_minutes for task in tasks)

        # Identify overall risks
        overall_risks = self._identify_overall_risks(goal, tasks, tech_stack)

        metadata = PlanMetadata(
            project_name=project_name,
            goal=goal,
            total_estimate_minutes=total_estimate,
            tech_stack=tech_stack,
            overall_risks=overall_risks,
        )

        return metadata, tasks

    def _decompose_goal_into_tasks(
        self,
        goal: str,
        tech_stack: List[str],
        project_files: List[Path],
        context: Optional[Dict],
    ) -> List[Task]:
        """
        Decompose goal into specific tasks with REAL files.

        This is where Cowork intelligence shines - NO generic "core" references!
        """

        tasks = []

        # Example decomposition based on goal keywords
        goal_lower = goal.lower()

        if "redis" in goal_lower or "cache" in goal_lower:
            # Redis caching example
            # Find relevant files
            client_files = [
                f for f in project_files
                if "client" in f.name or "service" in f.name
            ]

            tasks.append(Task(
                title="Add Redis async wrapper",
                estimate_minutes=45,
                files=[
                    str(f.relative_to(self.project_path))
                    for f in client_files[:2]
                ] if client_files else ["lib/cache_client.py"],
                steps=[
                    "Install redis[async] dependency",
                    "Create RedisClient class with async methods",
                    "Implement get/set/delete operations",
                    "Add connection pooling",
                ],
                verification="pytest tests/test_cache.py --cov=80%",
                acceptance_criteria="Cache hit rate > 80% in load test",
                risks=["Redis connection timeout", "Memory overflow"],
            ))

            tasks.append(Task(
                title="Integrate cache with API endpoints",
                estimate_minutes=60,
                files=[f"api/routes/{name}.py" for name in ["users", "posts"]],
                depends_on=[1],  # Depends on task 1
                steps=[
                    "Add @cache_result decorator to endpoints",
                    "Set appropriate TTL per endpoint",
                    "Handle cache misses gracefully",
                ],
                verification="pytest tests/test_api_cache.py -v",
                acceptance_criteria="Response time < 100ms for cached requests",
                risks=["Stale cache data"],
            ))

            tasks.append(Task(
                title="Add cache invalidation strategy",
                estimate_minutes=30,
                files=["lib/cache_client.py", "api/middleware.py"],
                depends_on=[1, 2],
                steps=[
                    "Implement invalidate_on_update decorator",
                    "Add cache key pattern matching",
                    "Create manual invalidation endpoint",
                ],
                verification="pytest tests/test_cache_invalidation.py",
                acceptance_criteria="Cache updates within 1s of data change",
                risks=["Over-invalidation causing performance hit"],
            ))

        elif "api" in goal_lower or "endpoint" in goal_lower:
            # API endpoint creation
            api_files = [f for f in project_files if "api" in str(f) or "routes" in str(f)]

            tasks.append(Task(
                title="Define API schema with Pydantic",
                estimate_minutes=30,
                files=["api/schemas/new_endpoint.py"],
                steps=[
                    "Create request/response models",
                    "Add validation rules",
                    "Document with examples",
                ],
                verification="pytest tests/test_schemas.py",
                acceptance_criteria="Schema validation passes for all edge cases",
            ))

            tasks.append(Task(
                title="Implement endpoint handler",
                estimate_minutes=45,
                files=["api/routes/new_endpoint.py"],
                depends_on=[1],
                steps=[
                    "Create async route handler",
                    "Add business logic",
                    "Implement error handling",
                ],
                verification="pytest tests/test_new_endpoint.py --cov=90%",
                acceptance_criteria="All happy path & error cases covered",
            ))

        else:
            # Generic task decomposition
            tasks.append(Task(
                title=f"Implement {goal}",
                estimate_minutes=60,
                files=[
                    str(f.relative_to(self.project_path))
                    for f in project_files[:3]
                ] if project_files else ["main.py"],
                steps=[
                    "Analyze requirements",
                    "Implement core functionality",
                    "Add tests",
                ],
                verification="pytest --cov=70%",
                acceptance_criteria="Feature works as specified",
            ))

        return tasks

    def _identify_overall_risks(
        self,
        goal: str,
        tasks: List[Task],
        tech_stack: List[str],
    ) -> List[str]:
        """Identify project-level risks."""
        risks = []

        # Collect from tasks
        for task in tasks:
            risks.extend(task.risks)

        # Add tech-specific risks
        if "redis" in " ".join(tech_stack).lower():
            risks.append("Redis service availability")

        if "async" in goal.lower() or "asyncio" in tech_stack:
            risks.append("Async/sync boundary issues")

        if len(tasks) > 5:
            risks.append("Task dependencies may cause delays")

        return list(set(risks))

    def _detect_tech_stack(
        self, readme_content: str, context: Optional[Dict]
    ) -> List[str]:
        """Detect tech stack from README and context."""
        tech_keywords = {
            "fastapi", "flask", "django",
            "react", "vue", "angular",
            "redis", "postgresql", "mongodb",
            "pytest", "jest",
            "docker", "kubernetes",
            "asyncio", "celery",
        }

        detected = set()

        readme_lower = readme_content.lower()
        for tech in tech_keywords:
            if tech in readme_lower:
                detected.add(tech)

        if context:
            context_tech = context.get("tech_stack", [])
            detected.update(t.lower() for t in context_tech)

        return list(sorted(detected))

    def _generate_plan_content(
        self,
        metadata: PlanMetadata,
        tasks: List[Task],
    ) -> str:
        """Generate PLAN.md content (MASTER document)."""

        content = f"""# PLAN: {metadata.project_name} - {metadata.goal}

**Est:** {metadata.total_estimate_minutes}min | **Risks:** {', '.join(metadata.overall_risks[:2])}

---

## Tasks

"""

        for idx, task in enumerate(tasks, 1):
            deps = ", ".join(f"#{d}" for d in task.depends_on) if task.depends_on else "None"
            files_str = "\n".join(f"   - {f}" for f in task.files)

            content += f"""
### {idx}. {task.title} ({task.estimate_minutes}min)

**Files:**
{files_str}

**Depends:** {deps}

**Steps:**
{chr(10).join(f'   {i+1}. {step}' for i, step in enumerate(task.steps))}

**Verify:** `{task.verification}`

**AC:** {task.acceptance_criteria}

**Risks:** {', '.join(task.risks) if task.risks else 'None'}

---
"""

        content += f"""
## Tech Stack
{chr(10).join(f'- {tech}' for tech in metadata.tech_stack)}

## Overall Risks
{chr(10).join(f'- {risk}' for risk in metadata.overall_risks)}

---
*Generated by CASCADE Orchestrator (Cowork-Powered)*
"""

        return content

    def _generate_design_from_plan(
        self,
        metadata: PlanMetadata,
        tasks: List[Task],
    ) -> str:
        """Generate DESIGN.md FROM the master plan."""

        # Extract components from tasks
        components = self._extract_design_components(tasks)

        content = f"""# DESIGN: {metadata.project_name} - {metadata.goal}

**Architecture:** Component-based with clear separation of concerns

---

## Components

"""

        for comp in components:
            content += f"""
### {comp.name}

**Type:** {comp.type}

**Description:** {comp.description}

**Interfaces:**
{chr(10).join(f'- {iface}' for iface in comp.interfaces)}

**Dependencies:**
{chr(10).join(f'- {dep}' for dep in comp.dependencies)}

---
"""

        content += """
## Data Flow

```
[Client] → [API Layer] → [Business Logic] → [Data Layer]
```

## Error Handling Strategy

- Use specific exceptions for each error type
- Return appropriate HTTP status codes
- Log errors with context

---
*Generated FROM PLAN.md by CASCADE Orchestrator*
"""

        return content

    def _extract_design_components(self, tasks: List[Task]) -> List[DesignComponent]:
        """Extract design components from tasks."""
        components = []

        # Group by file patterns
        file_groups = {}
        for task in tasks:
            for file in task.files:
                if "/" in file:
                    component_name = file.split("/")[0]
                else:
                    component_name = "Core"

                if component_name not in file_groups:
                    file_groups[component_name] = []
                file_groups[component_name].append(file)

        # Create components
        for comp_name, files in file_groups.items():
            comp_type = "API Layer" if "api" in comp_name.lower() else "Module"

            components.append(DesignComponent(
                name=comp_name.title(),
                type=comp_type,
                description=f"Handles {comp_name} functionality",
                interfaces=[f"{comp_name}Interface"],
                dependencies=[],
            ))

        return components

    def _generate_tasks_yaml_from_plan(
        self,
        metadata: PlanMetadata,
        tasks: List[Task],
    ) -> str:
        """Generate task.yaml FROM the master plan."""

        yaml_data = {
            "project": metadata.project_name,
            "goal": metadata.goal,
            "total_estimate_minutes": metadata.total_estimate_minutes,
            "tasks": []
        }

        for idx, task in enumerate(tasks, 1):
            yaml_data["tasks"].append({
                "id": idx,
                "title": task.title,
                "estimate_minutes": task.estimate_minutes,
                "files": task.files,
                "depends_on": task.depends_on,
                "steps": task.steps,
                "verification": task.verification,
                "acceptance_criteria": task.acceptance_criteria,
                "risks": task.risks,
                "status": "pending",
            })

        return yaml.dump(yaml_data, sort_keys=False, allow_unicode=True)

    def export_cascade(
        self,
        plan_content: str,
        design_content: str,
        tasks_yaml: str,
        output_dir: Path,
    ) -> Tuple[Path, Path, Path]:
        """Export CASCADE files."""

        output_dir.mkdir(parents=True, exist_ok=True)

        plan_file = output_dir / "PLAN.md"
        design_file = output_dir / "DESIGN.md"
        tasks_file = output_dir / "tasks.yaml"

        plan_file.write_text(plan_content, encoding="utf-8")
        design_file.write_text(design_content, encoding="utf-8")
        tasks_file.write_text(tasks_yaml, encoding="utf-8")

        return plan_file, design_file, tasks_file
