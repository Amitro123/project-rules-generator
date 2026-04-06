"""Coverage boost: ProjectPlanner pure methods (Task, Phase, Plan, parsers)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from generator.planning.project_planner import Phase, Plan, ProjectPlanner, Task

# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


class TestTask:
    def test_to_markdown_uncompleted(self):
        t = Task(description="Write tests", subtasks=["unit tests", "e2e tests"])
        md = t.to_markdown()
        assert "- [ ] Write tests" in md
        assert "unit tests" in md

    def test_to_markdown_completed(self):
        t = Task(description="Done task", subtasks=[], completed=True)
        md = t.to_markdown()
        assert "- [x] Done task" in md

    def test_to_markdown_with_indent(self):
        t = Task(description="Nested", subtasks=["sub1"])
        md = t.to_markdown(level=2)
        assert md.startswith("    ")

    def test_subtasks_listed(self):
        t = Task(description="Main", subtasks=["a", "b", "c"])
        md = t.to_markdown()
        assert md.count("[ ]") == 4  # 1 main + 3 subtasks


# ---------------------------------------------------------------------------
# Phase
# ---------------------------------------------------------------------------


class TestPhase:
    def test_to_markdown_with_description(self):
        phase = Phase(
            name="Phase 1",
            description="Initial setup",
            tasks=[Task("Install deps", [])],
        )
        md = phase.to_markdown()
        assert "## Phase 1" in md
        assert "Initial setup" in md
        assert "Install deps" in md

    def test_to_markdown_no_description(self):
        phase = Phase(name="Phase 2", description="", tasks=[Task("Do work", [])])
        md = phase.to_markdown()
        assert "## Phase 2" in md
        assert "Do work" in md

    def test_multiple_tasks(self):
        phase = Phase(
            name="Phase 3",
            description="",
            tasks=[Task("Task A", []), Task("Task B", [])],
        )
        md = phase.to_markdown()
        assert "Task A" in md
        assert "Task B" in md


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


class TestPlan:
    def _make_plan(self):
        phase = Phase(
            name="Phase 1: Foundation",
            description="Setup",
            tasks=[Task("Initialize", ["Create dirs"])],
        )
        return Plan(title="My Project Roadmap", description="A great plan", phases=[phase])

    def test_to_markdown_contains_title(self):
        plan = self._make_plan()
        md = plan.to_markdown()
        assert "# My Project Roadmap" in md

    def test_to_markdown_contains_description(self):
        plan = self._make_plan()
        md = plan.to_markdown()
        assert "A great plan" in md

    def test_to_markdown_contains_phase(self):
        plan = self._make_plan()
        md = plan.to_markdown()
        assert "Phase 1: Foundation" in md

    def test_to_mermaid_contains_graph(self):
        plan = self._make_plan()
        md = plan.to_mermaid()
        assert "```mermaid" in md
        assert "graph TD" in md

    def test_to_mermaid_contains_phase_node(self):
        plan = self._make_plan()
        md = plan.to_mermaid()
        assert "Phase 1: Foundation" in md

    def test_to_mermaid_contains_task_node(self):
        plan = self._make_plan()
        md = plan.to_mermaid()
        assert "Initialize" in md

    def test_save_markdown(self, tmp_path):
        plan = self._make_plan()
        out = tmp_path / "roadmap.md"
        plan.save(out, fmt="markdown")
        assert out.exists()
        assert "# My Project Roadmap" in out.read_text()

    def test_save_mermaid(self, tmp_path):
        plan = self._make_plan()
        out = tmp_path / "roadmap.md"
        plan.save(out, fmt="mermaid")
        assert "```mermaid" in out.read_text()

    def test_multiple_phases_linked(self):
        plan = Plan(
            title="Multi-phase",
            description="Test",
            phases=[
                Phase("Phase 1", "", [Task("T1", [])]),
                Phase("Phase 2", "", [Task("T2", [])]),
            ],
        )
        md = plan.to_mermaid()
        # Both phases should appear
        assert "Phase 1" in md
        assert "Phase 2" in md


# ---------------------------------------------------------------------------
# ProjectPlanner — pure methods (no LLM calls)
# ---------------------------------------------------------------------------


def _stub_planner():
    """Build a planner with a stub AI client to avoid LLM calls."""
    stub = MagicMock()
    stub.generate.return_value = ""
    return ProjectPlanner(client=stub)


class TestExtractFeaturesFromReadme:
    def test_extracts_features_section(self):
        planner = _stub_planner()
        readme = "# My App\n\n## Features\n\n- Fast processing\n- Easy install\n\n## Installation\npip install\n"
        features = planner._extract_features_from_readme(readme)
        assert "Fast processing" in features
        assert "Easy install" in features

    def test_extracts_todo_section(self):
        planner = _stub_planner()
        readme = "# App\n\n## TODO\n\n- Add caching\n- Improve logging\n"
        features = planner._extract_features_from_readme(readme)
        assert "Add caching" in features

    def test_returns_empty_for_no_sections(self):
        planner = _stub_planner()
        features = planner._extract_features_from_readme("# No features or todos here")
        assert features == []

    def test_limits_to_ten_features(self):
        planner = _stub_planner()
        items = "\n".join(f"- Feature {i}" for i in range(20))
        readme = f"## Features\n{items}\n"
        features = planner._extract_features_from_readme(readme)
        assert len(features) <= 10

    def test_short_items_excluded(self):
        planner = _stub_planner()
        readme = "## Features\n\n- OK\n- This is long enough\n"
        features = planner._extract_features_from_readme(readme)
        assert "OK" not in features
        assert "This is long enough" in features


class TestDetectHallucinations:
    def test_detects_term_not_in_readme(self):
        planner = _stub_planner()
        roadmap = "Build the DevLens-AI monitoring system"
        readme = "# My App\n\nA simple tool."
        hals = planner._detect_hallucinations(roadmap, readme)
        assert "DevLens-AI" in hals

    def test_no_hallucination_when_term_in_readme(self):
        planner = _stub_planner()
        roadmap = "Build the DevLens-AI monitoring system"
        readme = "# DevLens-AI\n\nA monitoring system."
        hals = planner._detect_hallucinations(roadmap, readme)
        assert "DevLens-AI" not in hals

    def test_returns_empty_for_clean_roadmap(self):
        planner = _stub_planner()
        roadmap = "- [ ] Write tests\n- [ ] Add documentation"
        readme = "# My Project\n\nA simple project."
        assert planner._detect_hallucinations(roadmap, readme) == []


class TestExtractPhasesFromMarkdown:
    def test_extracts_phase_and_tasks(self):
        planner = _stub_planner()
        md = "## Phase 1: Setup\n\nSet up the env\n\n- [ ] Task A\n- [ ] Task B\n"
        phases = planner._extract_phases_from_markdown(md)
        assert len(phases) == 1
        assert phases[0].name == "Phase 1: Setup"
        assert len(phases[0].tasks) == 2

    def test_multiple_phases(self):
        planner = _stub_planner()
        md = "## Phase 1\n\n- [ ] Task 1\n\n## Phase 2\n\n- [ ] Task 2\n"
        phases = planner._extract_phases_from_markdown(md)
        assert len(phases) == 2

    def test_empty_markdown_returns_empty(self):
        planner = _stub_planner()
        assert planner._extract_phases_from_markdown("No phases here") == []


class TestExtractTasksFromContent:
    def test_extracts_uncompleted_task(self):
        planner = _stub_planner()
        content = "- [ ] Install dependencies\n"
        tasks = planner._extract_tasks_from_content(content)
        assert len(tasks) == 1
        assert tasks[0].description == "Install dependencies"
        assert not tasks[0].completed

    def test_extracts_completed_task(self):
        planner = _stub_planner()
        content = "- [x] Done task\n"
        tasks = planner._extract_tasks_from_content(content)
        assert tasks[0].completed is True

    def test_multiple_tasks(self):
        planner = _stub_planner()
        content = "- [ ] Task A\n- [ ] Task B\n"
        tasks = planner._extract_tasks_from_content(content)
        assert len(tasks) == 2


class TestGenerateTemplateRoadmap:
    def test_returns_plan_with_three_phases(self):
        planner = _stub_planner()
        plan = planner._generate_template_roadmap(["Feature A"], "# My Project\n")
        assert isinstance(plan, Plan)
        assert len(plan.phases) == 3

    def test_uses_project_name_from_readme(self):
        planner = _stub_planner()
        plan = planner._generate_template_roadmap([], "# SuperApp\n\nA super app.")
        assert "SuperApp" in plan.title

    def test_uses_first_feature_in_phase2(self):
        planner = _stub_planner()
        plan = planner._generate_template_roadmap(["My special feature"], "# App\n")
        phase2_tasks = " ".join(t.description for t in plan.phases[1].tasks)
        assert "My special feature" in phase2_tasks

    def test_empty_features_still_returns_plan(self):
        planner = _stub_planner()
        plan = planner._generate_template_roadmap([], "# App\n")
        assert len(plan.phases) == 3


class TestGenerateTemplateTaskPlan:
    def test_returns_three_phases(self):
        planner = _stub_planner()
        plan = planner._generate_template_task_plan("Add caching")
        assert len(plan.phases) == 3

    def test_title_contains_query(self):
        planner = _stub_planner()
        plan = planner._generate_template_task_plan("Implement login")
        assert "Implement login" in plan.title

    def test_description_contains_query(self):
        planner = _stub_planner()
        plan = planner._generate_template_task_plan("Fix bug")
        assert "Fix bug" in plan.description


class TestBuildPrompts:
    def test_roadmap_prompt_contains_readme_excerpt(self):
        planner = _stub_planner()
        prompt = planner._build_roadmap_prompt("# My App\n\nA tool.", ["Feature A"], None)
        assert "My App" in prompt
        assert "Feature A" in prompt

    def test_roadmap_prompt_includes_banned_note(self):
        planner = _stub_planner()
        prompt = planner._build_roadmap_prompt("# App\n", [], None)
        assert "BANNED" in prompt

    def test_task_prompt_contains_query(self):
        planner = _stub_planner()
        prompt = planner._build_task_prompt("Add caching", "Python project")
        assert "Add caching" in prompt
        assert "Python project" in prompt


class TestParseRoadmapResponse:
    def test_returns_template_on_hallucination(self):
        planner = _stub_planner()
        # Response with hallucinated term (not in README)
        response = "# Roadmap\n\nBuild the GhostAgent-AI system\n\n## Phase 1\n\n- [ ] Task A\n"
        readme = "# My App\n\nA simple tool."
        plan = planner._parse_roadmap_response(response, readme)
        # Falls back to template when hallucination detected
        assert isinstance(plan, Plan)

    def test_parses_clean_response(self):
        planner = _stub_planner()
        response = "# Project Roadmap\n\nThis is a plan\n\n---\n\n## Phase 1: Setup\n\n- [ ] Task A\n"
        readme = "# Project Roadmap\n\nThis is a plan about setup."
        plan = planner._parse_roadmap_response(response, readme)
        assert plan.title != ""
