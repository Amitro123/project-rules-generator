"""Autopilot orchestrator — manages the end-to-end discovery and execution loop."""


import re
from pathlib import Path
from typing import Dict, List, Optional

import click

from generator.planning.workflow import AgentWorkflow
from generator.planning.task_creator import TaskManifest
from generator.planning.task_executor import TaskExecutor
from generator.planning.task_agent import TaskImplementationAgent
from generator.task_decomposer import SubTask
from prg_utils import git_ops

class AutopilotOrchestrator:
    """Manages the full end-to-end autopilot workflow."""

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
        self.workflow = None
        self.manifest_path = self.project_path / "tasks" / "TASKS.yaml"

    def discovery(self, task_description: str = "Complete project") -> TaskManifest:
        """PHASE 1: Discovery (rules + skills + plan + tasks)."""
        if self.verbose:
            click.echo(f"🔍 Discovery Phase: {task_description}")

        self.workflow = AgentWorkflow(
            project_path=self.project_path,
            task_description=task_description,
            provider=self.provider,
            api_key=self.api_key,
            verbose=self.verbose,
        )
        
        # run_setup handles analyze, design/plan, and task creation
        manifest = self.workflow.run_setup()
        return manifest

    def execution_loop(self, manifest: TaskManifest):
        """PHASE 2: Supervised Execution Loop."""
        if self.verbose:
            click.echo("🚀 Starting Supervised Execution Loop...")

        executor = TaskExecutor(manifest)
        agent = TaskImplementationAgent(provider=self.provider, api_key=self.api_key)
        
        main_branch = None
        try:
            main_branch = git_ops.get_current_branch(self.project_path)
        except Exception:
            if self.verbose:
                click.echo("⚠️  Not a git repository or git not found. Safety features disabled.")

        while True:
            nxt = executor.get_next_task()
            if not nxt:
                click.echo("\n🎉 PROJECT COMPLETE!")
                break

            click.echo(f"\n🎯 Next Task: #{nxt.id} {nxt.title}")
            
            # 1. Branching
            branch_name = f"autopilot/task-{nxt.id}"
            if main_branch:
                try:
                    git_ops.create_branch(branch_name, self.project_path)
                    click.echo(f"   🌿 Created branch: {branch_name}")
                except Exception as e:
                    click.echo(f"   ⚠️  Failed to create branch: {e}")

            # 2. Implementation
            try:
                executor.execute_single(nxt.id)
                # We need SubTask object, manifest has TaskEntry. 
                # TaskEntry references files, but not the full SubTask details needed for AI.
                # Re-parse subtask from its file
                subtask = self._load_subtask_details(nxt)
                
                click.echo("   🤖 Agent is implementing changes...")
                changes = agent.implement(subtask, project_context=self.workflow._get_project_context() if self.workflow else None)
                
                for fpath, content in changes.items():
                    full_path = self.project_path / fpath
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    click.echo(f"   ✅ Applied changes to {fpath}")

                # 3. Verification & Human in the loop
                click.echo("\n--- Verification Required ---")
                click.echo(f"Task: {nxt.title}")
                click.echo(f"Goal: {nxt.goal}")
                
                from rich.prompt import Confirm
                if Confirm.ask("Do you approve these changes?", default=True):
                    executor.complete_task(nxt.id)
                    executor.save(self.manifest_path)
                    
                    if main_branch:
                        git_ops.checkout(main_branch, self.project_path)
                        git_ops.merge_branch(branch_name, self.project_path)
                        git_ops.delete_branch(branch_name, force=True, repo_path=self.project_path)
                        click.echo(f"   ✅ Task #{nxt.id} merged and branch deleted.")
                else:
                    click.echo("   ❌ Changes rejected. Rolling back...")
                    if main_branch:
                        git_ops.checkout(main_branch, self.project_path)
                        git_ops.delete_branch(branch_name, force=True, repo_path=self.project_path)
                        git_ops.rollback_to_head(self.project_path)
                    break # Stop autopilot on rejection for safety

            except Exception as e:
                click.echo(f"   ❌ Task execution failed: {e}")
                if main_branch:
                    git_ops.checkout(main_branch, self.project_path)
                    git_ops.rollback_to_head(self.project_path)
                break

    def _load_subtask_details(self, entry) -> SubTask:
        """Load full SubTask details from the task file."""
        task_file = self.project_path / "tasks" / entry.file
        content = task_file.read_text(encoding="utf-8")
        
        # Extract fields using regex
        goal_match = re.search(r"\*\*Goal:\*\*\s*(.+)", content)
        goal = goal_match.group(1).strip() if goal_match else entry.title
        
        files = []
        files_section = re.search(r"## Files\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if files_section:
            files = re.findall(r"-\s+`(.+?)`", files_section.group(1))
            
        changes = []
        changes_section = re.search(r"## Changes\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if changes_section:
            changes = re.findall(r"-\s+(.+)", changes_section.group(1))
            
        tests = []
        tests_section = re.search(r"## Tests\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if tests_section:
            tests = re.findall(r"-\s+(.+)", tests_section.group(1))

        return SubTask(
            id=entry.id,
            title=entry.title,
            goal=goal,
            files=files,
            changes=changes,
            tests=tests,
            dependencies=entry.dependencies,
            estimated_minutes=entry.estimated_minutes,
            type=task_file.suffix.replace(".", "")
        )
