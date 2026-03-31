"""Project Manager — Handles the full project lifecycle from setup to completion."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from generator.planning.autopilot import AutopilotOrchestrator
from generator.planning.preflight import PreflightChecker
from generator.planning.task_creator import TaskManifest
from generator.planning.workflow import AgentWorkflow

logger = logging.getLogger(__name__)


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
        logger.info("👨‍💼 PRODUCT MANAGER AGENT: Initializing...")

        self.phase1_setup()
        self.phase2_verify()
        self.phase3_copilot()
        self.phase4_summary()

    # -- Phase 1: Setup ---------------------------------------------------

    def phase1_setup(self):
        """PHASE 1: Setup Checklist & Doc Generation."""
        logger.info("\n📋 PHASE 1: SEMI-AUTO SETUP")

        # 1. Generate PROJECT-MANAGER.md
        self._update_manager_checklist()

        # 2. Check for missing docs and attempt generation
        missing = self._get_missing_docs()
        if missing:
            logger.info(f"   ⚠️  Missing {len(missing)} documents. Attempting generation...")
            self._generate_missing_docs(missing)
            # Re-check
            self._update_manager_checklist()
        else:
            logger.info("   ✅ All required documents present.")

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
            logger.info("   ⚙️  Running analysis (rules + skills)...")
            self._generate_rules_and_skills()

        # Group 2: Planning (PLAN.md, tasks/)
        if "PLAN.md" in missing or "tasks/TASKS.yaml" in missing:
            logger.info("   ⚙️  Running planning...")
            self.workflow.run_setup()  # Generates plan and tasks if missing

        # Group 3: Architecture
        if "ARCHITECTURE.md" in missing:
            logger.info("   ⚙️  Generating ARCHITECTURE.md...")
            from generator.design_generator import DesignGenerator

            gen = DesignGenerator(api_key=self.api_key, provider=self.provider)
            design = gen.generate_design(
                user_request="Complete full project implementation. Focus on high-level architecture.",
                project_context=self._get_context(),
            )
            (self.project_path / "ARCHITECTURE.md").write_text(design.to_markdown(), encoding="utf-8")

        # Group 4: Spec (Requirements)
        if "spec.md" in missing:
            logger.info("   ⚙️  Generating spec.md...")
            self._generate_spec_md()

        # Group 5: Tests (Scaffolding)
        if "tests/" in missing or "pytest.ini" in missing:
            logger.info("   ⚙️  Scaffolding tests...")
            (self.project_path / "tests").mkdir(exist_ok=True)
            if "pytest.ini" in missing:
                (self.project_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")

    def _generate_spec_md(self):
        """Generate a structured project specification using LLM (spec-kit-inspired)."""
        import subprocess

        from generator.ai.factory import create_ai_client
        from generator.prompts.spec_generation import SPEC_GENERATION_PROMPT, SPEC_SYSTEM_MESSAGE
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
        except (OSError, subprocess.SubprocessError):
            pass

        # --- Build prompt ---
        context_parts = [f"## README\n{readme_content[:2500]}"] if readme_content else []
        if plan_content:
            context_parts.append(f"## PLAN.md (excerpt)\n{plan_content}")
        if git_log:
            context_parts.append(f"## Recent Git Commits\n{git_log}")
        context_parts.append(f"## Project Tree\n{project_tree}")

        context_block = "\n\n".join(context_parts)

        prompt = SPEC_GENERATION_PROMPT.format(context_block=context_block)

        spec_content = client.generate(
            prompt,
            temperature=0.3,
            system_message=SPEC_SYSTEM_MESSAGE,
        )

        # Encoding safety
        spec_content = spec_content.encode("utf-8", errors="replace").decode("utf-8")

        (self.project_path / "spec.md").write_text(spec_content, encoding="utf-8")
        logger.info(f"   ✅ Generated spec.md ({len(spec_content.splitlines())} lines)")

    def _generate_rules_and_skills(self) -> None:
        """Generate rules.md and skills/index.md directly without going through the CLI layer."""
        from generator.rules_creator import CoworkRulesCreator
        from generator.skills_manager import SkillsManager
        from generator.utils.readme_bridge import find_readme

        output_dir = self.project_path / ".clinerules"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build enhanced context
        enhanced_context = None
        try:
            from generator.parsers.enhanced_parser import EnhancedProjectParser

            enhanced_context = EnhancedProjectParser(self.project_path).extract_full_context()
        except Exception as exc:
            logger.warning("Enhanced analysis unavailable: %s", exc)

        # README text for rules generation
        readme_path = find_readme(self.project_path)
        readme_text = (
            readme_path.read_text(encoding="utf-8", errors="replace") if readme_path else f"# {self.project_path.name}"
        )

        # Generate rules.md via CoworkRulesCreator
        creator = CoworkRulesCreator(self.project_path)
        content, metadata, _ = creator.create_rules(readme_text, enhanced_context=enhanced_context)
        creator.export_to_file(content, metadata, output_dir)
        logger.info("   Generated rules.md")

        # Generate skills index and auto-triggers
        skills_mgr = SkillsManager(project_path=self.project_path)
        skills_mgr.save_triggers_json(output_dir)
        skills_mgr.generate_perfect_index()
        logger.info("   Generated skills/index.md")

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
        logger.info(f"   📄 Updated PROJECT-MANAGER.md ({ready_count}/{len(self.REQUIRED_DOCS)} ready)")

    def _get_context(self) -> Optional[Dict]:
        # Helper to get some context for AI generation
        return self.workflow._get_project_context() if self.workflow else {}

    # -- Phase 2: Verify --------------------------------------------------

    def phase2_verify(self):
        """PHASE 2: Readiness Verification."""
        logger.info("\n🛡️  PHASE 2: READINESS VERIFICATION")
        checker = PreflightChecker(self.project_path, task_description="Project Manager Check")
        report = checker.run_checks()

        logger.info(report.format_report())

        if not report.all_passed:
            failed = [c.name for c in report.failed_checks]
            raise RuntimeError(f"Readiness verification failed: {', '.join(failed)}. Fix issues before proceeding.")

    # -- Phase 3: Copilot -------------------------------------------------

    def phase3_copilot(self):
        """PHASE 3: Copilot Execution."""
        logger.info("\n✈️  PHASE 3: COPILOT EXECUTION")

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
            logger.info("❌ No TASKS.yaml found. Skipping execution.")

    # -- Phase 4: Summary -------------------------------------------------

    def phase4_summary(self):
        """PHASE 4: Final Summary."""
        logger.info("\n🎉 PHASE 4: FINAL SUMMARY")

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
        logger.info(f"   📄 Generated PROJECT-COMPLETION.md\n   {stats}")
