"""Agent commands for project rules generator."""

import os
import sys
from pathlib import Path

import click

from cli._version import __version__
from cli.utils import detect_provider as _detect_provider
from cli.utils import set_api_key_env as _set_api_key


@click.command(name="design")
@click.argument("description")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="DESIGN.md",
    help="Output file (default: DESIGN.md)",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider (gemini, groq, anthropic, openai). Auto-detected if omitted.",
)
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def design(description, project_path, output, api_key, provider, verbose):
    """Generate a technical design document (Stage 1 of two-stage planning)."""
    project_path = Path(project_path).resolve()
    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    if verbose:
        click.echo(f"Project Rules Generator v{__version__} — Design Generator")
        click.echo(f"Request: {description}")
        click.echo(f"Project: {project_path}")

    # Gather project context
    enhanced_context = None
    try:
        from generator.parsers.enhanced_parser import EnhancedProjectParser

        parser = EnhancedProjectParser(project_path)
        enhanced_context = parser.extract_full_context()
        if verbose:
            meta = enhanced_context.get("metadata", {})
            click.echo(f"Context: {meta.get('project_type', 'unknown')} ({', '.join(meta.get('tech_stack', []))})")
    except Exception as exc:
        if verbose:
            click.echo(f"Context extraction skipped: {exc}")

    from generator.design_generator import DesignGenerator

    generator = DesignGenerator(provider=provider)

    if verbose:
        click.echo("Generating design...")

    design_obj = generator.generate_design(
        description,
        project_context=enhanced_context,
        project_path=project_path,
    )

    design_md = design_obj.to_markdown()

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_path / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(design_md, encoding="utf-8")

    click.echo(f"\\nDesign: {design_obj.title}")
    click.echo(f"  Decisions: {len(design_obj.architecture_decisions)}")
    click.echo(f"  API contracts: {len(design_obj.api_contracts)}")
    click.echo(f"  Data models: {len(design_obj.data_models)}")
    click.echo(f"  Success criteria: {len(design_obj.success_criteria)}")
    click.echo(f"Written to: {output_path}")


@click.command(name="plan")
@click.argument("task_description", required=False, default=None)
@click.option(
    "--from-design",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Generate plan from a DESIGN.md file",
)
@click.option(
    "--from-readme",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Generate roadmap from README.md",
)
@click.option("--status", is_flag=True, help="Show progress on existing plans")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file for the plan (default: auto-generated)",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider (gemini, groq, anthropic, openai). Auto-detected if omitted.",
)
@click.option("--interactive", is_flag=True, help="Open files in IDE as tasks are listed")
@click.option(
    "--auto-execute",
    is_flag=True,
    help="Agent executes tasks automatically (requires --interactive)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "mermaid"]),
    default="markdown",
    help="Output format: markdown (default) or mermaid (diagram)",
)
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def plan(
    task_description,
    from_design,
    from_readme,
    status,
    project_path,
    output,
    api_key,
    provider,
    interactive,
    auto_execute,
    output_format,
    verbose,
):
    """Break down a task into subtasks and generate PLAN.md."""
    project_path = Path(project_path).resolve()

    # Auto-detect: if task_description looks like a directory path, treat as project
    if task_description and not from_readme and not from_design and not status:
        candidate = Path(task_description)
        # Check relative to CWD and absolute
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        if candidate.is_dir():
            # Treat task_description as a project path, auto-find README
            project_path = candidate.resolve()
            readme_candidate = project_path / "README.md"
            if readme_candidate.exists():
                from_readme = str(readme_candidate)
                task_description = None
                if verbose:
                    click.echo(f"Auto-detected project directory: {project_path}")
                    click.echo(f"Using README: {readme_candidate}")

    # Handle --status mode
    if status:
        from generator.planning import PlanParser

        parser = PlanParser()

        # Find all plan files
        plan_files = parser.find_plans(project_path)

        if not plan_files:
            click.echo("No plan files found in project directory.")
            click.echo("Tip: Generate a plan with 'prg plan <task>' or 'prg plan --from-readme README.md'")
            sys.exit(0)

        # Show status for each plan
        for plan_file in plan_files:
            plan_status = parser.parse_plan(plan_file)
            report = parser.format_status_report(plan_status)
            click.echo(report)
            click.echo()  # Blank line between plans

        sys.exit(0)

    # Handle --from-readme mode
    if from_readme:
        from generator.planning import ProjectPlanner

        if verbose:
            click.echo(f"Project Rules Generator v{__version__} — Roadmap Generator")
            click.echo(f"From README: {from_readme}")
            click.echo(f"Project: {project_path}")

        provider = _detect_provider(provider, api_key)
        _set_api_key(provider, api_key)  # Fixed: using shared helper

        if verbose:
            click.echo(f"Generating roadmap with {provider}...")

        planner = ProjectPlanner(provider=provider, api_key=api_key)
        plan_obj = planner.generate_roadmap_from_readme(Path(from_readme), project_path=project_path)

        # Auto-generate output filename if not provided
        if not output:
            output = "PROJECT-ROADMAP.md"

        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = project_path / output_path

        plan_obj.save(output_path, fmt=output_format)
        if verbose and output_format == "mermaid":
            click.echo("   Format: Mermaid diagram")

        # Write structured task manifest for roadmaps too
        import json
        from datetime import datetime

        tasks_path = output_path.with_name("TASKS.json")
        task_id = 0
        roadmap_tasks = []
        for phase in plan_obj.phases:
            for task in phase.tasks:
                task_id += 1
                roadmap_tasks.append(
                    {
                        "id": task_id,
                        "phase": phase.name,
                        "title": task.description,
                        "subtasks": task.subtasks,
                        "completed": task.completed,
                        "status": "done" if task.completed else "pending",
                    }
                )
        tasks_data = {
            "plan_file": output_path.name,
            "created": datetime.now().isoformat(),
            "task": plan_obj.title,
            "tasks": roadmap_tasks,
        }
        tasks_path.write_text(json.dumps(tasks_data, indent=2), encoding="utf-8")

        click.echo("\\n✅ Generated roadmap:")
        click.echo(f"   Title: {plan_obj.title}")
        click.echo(f"   Phases: {len(plan_obj.phases)}")
        total_tasks = sum(len(p.tasks) for p in plan_obj.phases)
        click.echo(f"   Tasks: {total_tasks}")
        click.echo(f"   Saved to: {output_path}")
        click.echo(f"   Tasks manifest: {tasks_path}")

        sys.exit(0)

    # Original plan command logic (from task description or design)
    if not task_description and not from_design:
        click.echo(
            "Error: Provide a TASK_DESCRIPTION, --from-readme, --from-design, or --status.",
            err=True,
        )
        sys.exit(1)

    project_path = Path(project_path).resolve()

    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    if verbose:
        click.echo(f"Project Rules Generator v{__version__} — Task Planner")
        if from_design:
            click.echo(f"From design: {from_design}")
        else:
            click.echo(f"Task: {task_description}")
        click.echo(f"Project: {project_path}")

    # Gather project context if available
    enhanced_context = None
    try:
        from generator.parsers.enhanced_parser import EnhancedProjectParser

        parser = EnhancedProjectParser(project_path)
        enhanced_context = parser.extract_full_context()
        if verbose:
            meta = enhanced_context.get("metadata", {})
            click.echo(f"Context: {meta.get('project_type', 'unknown')} ({', '.join(meta.get('tech_stack', []))})")
    except Exception as exc:
        if verbose:
            click.echo(f"Context extraction skipped: {exc}")

    from generator.task_decomposer import TaskDecomposer

    decomposer = TaskDecomposer(provider=provider, api_key=api_key)
    if verbose:
        click.echo("Decomposing task...")

    if from_design:
        subtasks = decomposer.from_design(
            Path(from_design),
            project_context=enhanced_context,
        )
        # Use the design title as user_task for the plan header
        from generator.design_generator import Design

        design_obj = Design.from_markdown(Path(from_design).read_text(encoding="utf-8"))
        user_task_label = design_obj.title
    else:
        subtasks = decomposer.decompose(
            task_description,
            project_context=enhanced_context,
            project_path=project_path,
        )
        user_task_label = task_description

    plan_md = decomposer.generate_plan_md(subtasks, user_task=user_task_label)

    # Use default output if not provided
    if not output:
        output = "PLAN.md"

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_path / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(plan_md, encoding="utf-8")

    # Write structured task manifest alongside the plan
    import json
    from datetime import datetime

    tasks_path = output_path.with_name("TASKS.json")
    tasks_data = {
        "plan_file": output_path.name,
        "created": datetime.now().isoformat(),
        "task": user_task_label,
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "goal": t.goal,
                "files": t.files,
                "dependencies": t.dependencies,
                "estimated_minutes": t.estimated_minutes,
                "status": "pending",
            }
            for t in subtasks
        ],
    }
    tasks_path.write_text(json.dumps(tasks_data, indent=2), encoding="utf-8")

    click.echo(f"\\nGenerated {len(subtasks)} subtasks")
    click.echo(f"Plan written to: {output_path}")
    click.echo(f"Tasks manifest: {tasks_path}")
    click.echo(f"Estimated time: {sum(t.estimated_minutes for t in subtasks)} minutes")

    # Interactive mode: open files in IDE for each subtask
    if interactive:
        import shutil
        import subprocess

        # Detect available editor
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
        if not editor:
            for candidate in ["code", "cursor", "subl", "vim", "notepad"]:
                if shutil.which(candidate):
                    editor = candidate
                    break

        click.echo(f"\\n--- Interactive Mode (editor: {editor or 'none'}) ---")
        for task in subtasks:
            click.echo(f"\\nTask {task.id}: {task.title}")
            click.echo(f"  Goal: {task.goal}")
            if task.files and editor:
                for fpath in task.files:
                    full_path = project_path / fpath
                    action = "Open" if full_path.exists() else "Create"
                    click.echo(f"  [{action}] {fpath}")
                    if auto_execute and not full_path.exists():
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.write_text(f"# TODO: {task.title}\\n", encoding="utf-8")
                    try:
                        subprocess.Popen([editor, str(full_path)])
                    except Exception as e:
                        click.echo(f"  Could not open {fpath}: {e}")
            elif task.files:
                for fpath in task.files:
                    full_path = project_path / fpath
                    action = "Open" if full_path.exists() else "Create"
                    click.echo(f"  [{action}] {fpath} (no editor detected)")
            if not auto_execute:
                try:
                    input("  Press Enter for next task...")
                except (EOFError, KeyboardInterrupt):
                    click.echo("\\nAborted.")
                    break


@click.command(name="review")
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory for README context",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file (default: CRITIQUE.md next to input)",
)
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider (gemini, groq, anthropic, openai). Auto-detected if omitted.",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option("--tasks", is_flag=True, help="Generate executable tasks from review")
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def review(filepath, project_path, output, provider, api_key, tasks, verbose):
    """Review a generated artifact for quality and hallucinations."""
    filepath = Path(filepath).resolve()
    project_path = Path(project_path).resolve()

    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    if verbose:
        click.echo(f"Project Rules Generator v{__version__} — Self-Review")
        click.echo(f"Reviewing: {filepath}")
        click.echo(f"Provider: {provider}")

    from generator.planning import SelfReviewer

    reviewer = SelfReviewer(provider=provider, api_key=api_key)

    try:
        report = reviewer.review(filepath, project_path=project_path)
    except Exception as e:
        click.echo(f"Review failed: {e}", err=True)
        sys.exit(1)

    # Display summary
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Review Summary")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Verdict", report.verdict)
        table.add_row("Strengths", str(len(report.strengths)))
        table.add_row("Issues", str(len(report.issues)))
        table.add_row("Hallucinations", str(len(report.hallucinations)))
        console.print(table)

        if report.strengths and verbose:
            click.echo("\\nStrengths:")
            for s in report.strengths:
                click.echo(f"  + {s}")

        if report.issues:
            click.echo("\\nIssues:")
            for i in report.issues:
                click.echo(f"  - {i}")

        if report.hallucinations:
            click.echo("\\nHallucinations:")
            for h in report.hallucinations:
                click.echo(f"  ! {h}")

        if report.action_plan and verbose:
            click.echo("\\nAction Plan:")
            for a in report.action_plan:
                click.echo(f"  [ ] {a}")
    except ImportError:
        # Fallback without rich
        click.echo(f"\\nVerdict: {report.verdict}")
        click.echo(f"Strengths: {len(report.strengths)}")
        click.echo(f"Issues: {len(report.issues)}")
        click.echo(f"Hallucinations: {len(report.hallucinations)}")
        for i in report.issues:
            click.echo(f"  - {i}")
        for h in report.hallucinations:
            click.echo(f"  ! {h}")

    # Write output
    if not output:
        output = filepath.parent / "CRITIQUE.md"
    else:
        output = Path(output)
        if not output.is_absolute():
            output = Path.cwd() / output

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.to_markdown(), encoding="utf-8")
    click.echo(f"\\nCritique written to: {output}")

    # Handle --tasks flag
    if tasks:
        from generator.planning.task_creator import TaskCreator
        from generator.task_decomposer import TaskDecomposer

        if verbose:
            click.echo("Generating executable tasks from review...")

        try:
            decomposer = TaskDecomposer(api_key=api_key)
            subtasks = decomposer.from_plan(filepath)

            creator = TaskCreator()
            output_dir = project_path / ".clinerules" / "tasks"
            creator.create_from_subtasks(
                subtasks,
                plan_file=filepath.name,
                task_description=f"Generated from {filepath.name}",
                output_dir=output_dir,
            )
            click.echo(f"✅ Created {len(subtasks)} tasks in {output_dir}")
        except Exception as e:
            click.echo(f"❌ Failed to generate tasks: {e}", err=True)


@click.command(name="start")
@click.argument("task_description")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def start(task_description, project_path, provider, api_key, verbose):
    """Full agent workflow: plan -> tasks -> preflight -> auto-fix -> ready."""
    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    from generator.planning.workflow import AgentWorkflow

    workflow = AgentWorkflow(
        project_path=Path(project_path).resolve(),
        task_description=task_description,
        provider=provider,
        api_key=api_key,
        verbose=verbose,
    )

    try:
        workflow.run_full()
    except Exception as e:
        click.echo(f"Workflow failed: {e}", err=True)
        sys.exit(1)


@click.command(name="setup")
@click.argument("task_description")
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Project directory",
)
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option("--verbose/--quiet", default=True, help="Verbose output")
def setup(task_description, project_path, provider, api_key, verbose):
    """Setup workflow: plan -> tasks -> preflight -> auto-fix (no execution)."""
    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    from generator.planning.workflow import AgentWorkflow

    workflow = AgentWorkflow(
        project_path=Path(project_path).resolve(),
        task_description=task_description,
        provider=provider,
        api_key=api_key,
        verbose=verbose,
    )

    try:
        manifest = workflow.run_setup()
        click.echo(f"\\nSetup complete: {len(manifest.tasks)} tasks created.")
        click.echo("Run 'prg status' to see progress or 'prg exec tasks/<file>' to begin.")
    except Exception as e:
        click.echo(f"Setup failed: {e}", err=True)
        sys.exit(1)


@click.command(name="agent")
@click.argument("query")
def agent_command(query):
    """Simulate agent auto-trigger matching for a query."""
    from generator.planning.agent_executor import AgentExecutor

    # Assume current directory is project root
    project_path = Path(os.getcwd())
    executor = AgentExecutor(project_path)

    matched_skill = executor.match_skill(query)

    if matched_skill:
        click.echo(f"🎯 Auto-trigger: {matched_skill}")
    else:
        click.echo("No matching skill found.")
