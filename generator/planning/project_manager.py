"""Project Manager — Handles the full project lifecycle from setup to completion."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from generator.planning.autopilot import AutopilotOrchestrator
from generator.planning.preflight import PreflightChecker
from generator.planning.task_creator import TaskManifest
from generator.planning.workflow import AgentWorkflow


class ProjectManager:
    """Orchestrates the 4 phases of the project lifecycle."""

    REQUIRED_DOCS = [
        ".clinerules/rules.md",
        ".clinerules/skills/index.md",
        "PLAN.md",
        "tasks/TASKS.yaml",
        "spec.md",
        "tests/",
        "pytest.ini",
        "README.md",
        "ARCHITECTURE.md",
    ]

    def __init__(
        self,
        project_path: Path,
        provider: str = "groq",
        api_key: Optional[str] = None,
        verbose: bool = True,
    ):
        self.project_path = Path(project_path).resolve()
        self.provider = provider
        self.api_key = api_key
        self.verbose = verbose
        self.workflow = AgentWorkflow(
            project_path=self.project_path,
            task_description="Complete project",  # Default generic task
            provider=provider,
            api_key=api_key,
            verbose=verbose,
        )

    def run_lifecycle(self):
        """Execute the full 4-phase lifecycle."""
        click.echo("👨‍💼 PRODUCT MANAGER AGENT: Initializing...")

        self.phase1_setup()
        self.phase2_verify()
        self.phase3_copilot()
        self.phase4_summary()

    # -- Phase 1: Setup ---------------------------------------------------

    def phase1_setup(self):
        """PHASE 1: Setup Checklist & Doc Generation."""
        click.echo("\n📋 PHASE 1: SEMI-AUTO SETUP")

        # 1. Generate PROJECT-MANAGER.md
        self._update_manager_checklist()

        # 2. Check for missing docs and attempt generation
        missing = self._get_missing_docs()
        if missing:
            click.echo(f"   ⚠️  Missing {len(missing)} documents. Attempting generation...")
            self._generate_missing_docs(missing)
            # Re-check
            self._update_manager_checklist()
        else:
            click.echo("   ✅ All required documents present.")

    def _get_missing_docs(self) -> List[str]:
        return [doc for doc in self.REQUIRED_DOCS if not self._doc_exists(doc)]

    def _doc_exists(self, doc_path: str) -> bool:
        path = self.project_path / doc_path
        if doc_path.endswith("/"):  # Directory check
            return path.is_dir()
        # Special case for TASKS.yaml which might be TASKS.json in some versions
        if "TASKS.yaml" in doc_path and not path.exists():
            return (self.project_path / "tasks/TASKS.json").exists()
        return path.exists()

    def _generate_missing_docs(self, missing: List[str]):
        """Trigger specific generators for missing artifacts."""

        # Group 1: Analysis (rules, skills)
        if any(x in missing for x in [".clinerules/rules.md", ".clinerules/skills/index.md"]):
            click.echo("   ⚙️  Running analysis (rules + skills)...")
            # We can use AgentWorkflow's internal or call specific commands.
            # Using AgentWorkflow.run_setup() covers a lot, but might be too broad.
            # Let's use the CLI logic roughly:
            from refactor.analyze_cmd import AnalyzeCommand

            cmd = AnalyzeCommand(
                project_path=self.project_path, mode="ai" if self.api_key else "manual", api_key=self.api_key
            )
            cmd.execute()

        # Group 2: Planning (PLAN.md, tasks/)
        if "PLAN.md" in missing or "tasks/TASKS.yaml" in missing:
            click.echo("   ⚙️  Running planning...")
            self.workflow.run_setup()  # Generates plan and tasks if missing

        # Group 3: Architecture
        if "ARCHITECTURE.md" in missing:
            click.echo("   ⚙️  Generating ARCHITECTURE.md...")
            from generator.design_generator import DesignGenerator

            gen = DesignGenerator(api_key=self.api_key, provider=self.provider)
            design = gen.generate_design(
                user_request="Complete full project implementation. Focus on high-level architecture.",
                project_context=self._get_context(),
            )
            (self.project_path / "ARCHITECTURE.md").write_text(design.to_markdown(), encoding="utf-8")

        # Group 4: Spec (Requirements)
        if "spec.md" in missing:
            click.echo("   ⚙️  Generating spec.md...")
            self._generate_spec_md()

        # Group 5: Tests (Scaffolding)
        if "tests/" in missing or "pytest.ini" in missing:
            click.echo("   ⚙️  Scaffolding tests...")
            (self.project_path / "tests").mkdir(exist_ok=True)
            if "pytest.ini" in missing:
                (self.project_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")

    def _generate_spec_md(self):
        """Generate a structured project specification using LLM (spec-kit-inspired)."""
        import subprocess

        from generator.ai.factory import create_ai_client
        from generator.utils.readme_bridge import build_project_tree, is_readme_sufficient

        client = create_ai_client(provider=self.provider, api_key=self.api_key)

        # --- Gather context ---
        readme_path = self.project_path / "README.md"
        readme_content = ""
        if readme_path.exists():
            readme_content = readme_path.read_text(encoding="utf-8", errors="replace")

        plan_path = self.project_path / "PLAN.md"
        plan_content = ""
        if plan_path.exists():
            plan_content = plan_path.read_text(encoding="utf-8", errors="replace")[:1500]

        project_tree = build_project_tree(self.project_path)

        git_log = ""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.project_path), "log", "--oneline", "-20"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            git_log = result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            pass

        # --- Build prompt ---
        context_parts = [f"## README\n{readme_content[:2500]}"] if readme_content else []
        if plan_content:
            context_parts.append(f"## PLAN.md (excerpt)\n{plan_content}")
        if git_log:
            context_parts.append(f"## Recent Git Commits\n{git_log}")
        context_parts.append(f"## Project Tree\n{project_tree}")

        context_block = "\n\n".join(context_parts)

        prompt = f"""You are a senior product manager. Based on the project context below, write a complete **spec.md** document.

---
{context_block}
---

Generate a spec.md with EXACTLY these sections (use the headings verbatim):

# Project Specification

## Overview
One paragraph: what this project does, who it's for, and the core problem it solves.

## Goals
3-5 bullet points. Each goal is a concrete, measurable outcome.

## User Personas
2-3 short personas. Format: **Name** (Role) — one sentence describing their need.

## User Stories
5-8 stories in "As a [persona], I want [action] so that [benefit]." format.

## Constraints
Technical and non-functional constraints (performance, security, compatibility, budget, timeline).
Use bullets.

## Acceptance Criteria
Numbered list. Each criterion is testable and unambiguous.
Format: [ID] Given [context], when [action], then [expected result].

## Out of Scope
What this project explicitly does NOT cover. 2-4 bullets.

Rules:
- Be specific to THIS project — no generic filler.
- Do not include section titles not listed above.
- Use clean Markdown only.
"""

        spec_content = client.generate(
            prompt,
            temperature=0.3,
            system_message="You are a senior product manager. Write precise, actionable project specifications.",
        )

        # Encoding safety
        spec_content = spec_content.encode("utf-8", errors="replace").decode("utf-8")

        (self.project_path / "spec.md").write_text(spec_content, encoding="utf-8")
        click.echo(f"   ✅ Generated spec.md ({len(spec_content.splitlines())} lines)")

    def _update_manager_checklist(self):
        """Create or update PROJECT-MANAGER.md."""
        lines = [
            "# 👨‍💼 Project Manager Checklist",
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Phase 1: Setup Artifacts",
        ]

        ready_count = 0
        for doc in self.REQUIRED_DOCS:
            exists = self._doc_exists(doc)
            icon = "✅" if exists else "❌"
            if exists:
                ready_count += 1
            lines.append(f"- [{'x' if exists else ' '}] {icon} `{doc}`")

        lines.append("")
        lines.append(f"**Status:** {ready_count}/{len(self.REQUIRED_DOCS)} documents ready.")

        (self.project_path / "PROJECT-MANAGER.md").write_text("\n".join(lines), encoding="utf-8")
        click.echo(f"   📄 Updated PROJECT-MANAGER.md ({ready_count}/{len(self.REQUIRED_DOCS)} ready)")

    def _get_context(self) -> Optional[Dict]:
        # Helper to get some context for AI generation
        return self.workflow._get_project_context() if self.workflow else {}

    # -- Phase 2: Verify --------------------------------------------------

    def phase2_verify(self):
        """PHASE 2: Readiness Verification."""
        click.echo("\n🛡️  PHASE 2: READINESS VERIFICATION")
        checker = PreflightChecker(self.project_path, task_description="Project Manager Check")
        report = checker.run_checks()

        click.echo(report.format_report())

        if not report.all_passed:
            click.echo("❌ Verification failed. Please fix issues before proceeding.")
            # In interactive mode we might pause here, but for now we stop.
            # Or asking user via input?
            pass

    # -- Phase 3: Copilot -------------------------------------------------

    def phase3_copilot(self):
        """PHASE 3: Copilot Execution."""
        click.echo("\n✈️  PHASE 3: COPILOT EXECUTION")

        # Delegate to AutopilotOrchestrator, but maybe wrapper it to enforce reports?
        # For now, let's just run the execute loop.
        orchestrator = AutopilotOrchestrator(
            project_path=self.project_path, provider=self.provider, api_key=self.api_key, verbose=self.verbose
        )

        # Load manifest
        manifest_path = self.project_path / "tasks" / "TASKS.yaml"
        if manifest_path.exists():
            manifest = TaskManifest.from_yaml(manifest_path)
            orchestrator.execution_loop(manifest)
        else:
            click.echo("❌ No TASKS.yaml found. Skipping execution.")

    # -- Phase 4: Summary -------------------------------------------------

    def phase4_summary(self):
        """PHASE 4: Final Summary."""
        click.echo("\n🎉 PHASE 4: FINAL SUMMARY")

        # Basic stats
        manifest_path = self.project_path / "tasks" / "TASKS.yaml"
        stats = "No tasks found."
        if manifest_path.exists():
            manifest = TaskManifest.from_yaml(manifest_path)
            total = len(manifest.tasks)
            done = sum(1 for t in manifest.tasks if t.status == "done")
            stats = f"Tasks: {done}/{total} complete."

        report = [
            "# Project Completion Report",
            f"Date: {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "## 📊 Metrics",
            stats,
            # Placeholder for test coverage
            "",
            "## 📁 Generated Artifacts",
            "- [x] PROJECT-MANAGER.md",
            "- [x] rules.md",
            "- [x] skills/",
            "",
            "## 🎯 Achievements",
            "See `TASKS.yaml` for detailed task logs.",
        ]

        (self.project_path / "PROJECT-COMPLETION.md").write_text("\n".join(report), encoding="utf-8")
        click.echo(f"   📄 Generated PROJECT-COMPLETION.md\n   {stats}")
