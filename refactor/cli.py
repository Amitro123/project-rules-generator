"""CLI orchestrator for project rules and skills generator."""

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure project root is in sys.path
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import commands from modules
# note: imports are delayed to avoid circular dependency issues during setup if any
# but specific command imports are usually fine.


class DefaultGroup(click.Group):
    """Click group that delegates to a default command when none is given."""

    def __init__(self, *args, default_cmd="analyze", **kwargs):
        super().__init__(*args, **kwargs)
        self.default_cmd = default_cmd

    def parse_args(self, ctx, args):
        # Let group-level flags (--help, --version) pass through
        if (
            args
            and args[0] not in self.commands
            and args[0] not in ("--help", "--version", "-h")
        ):
            args = [self.default_cmd] + list(args)
        elif not args:
            args = [self.default_cmd]
        return super().parse_args(ctx, args)


@click.group(
    cls=DefaultGroup,
    default_cmd="analyze",
    help="Project Rules Generator - Generate rules.md and skills.md from README.md",
    epilog="Use 'analyze --help' to see options for the default analyze command.",
)
@click.version_option(version="0.1.0")
def cli():
    """Project Rules Generator - Generate rules.md and skills.md from README.md

    Common analyze options:
      --commit / --no-commit   Auto-commit to git
      --interactive            Interactive prompts
      --mode [manual|ai|constitution]
      --merge                  Preserve existing skill files
      --output PATH            Output directory (default: .clinerules)
      --incremental            Only regenerate changed sections
    """
    pass


from refactor.agent import agent_command, design, plan, review, setup, start

# Import and register commands at module level
from refactor.analyze_cmd import analyze
from refactor.autopilot_cmd import autopilot
from refactor.cascade_cmd import cascade
from refactor.create_skills_cmd import create_skills
from refactor.config_cmd import config_cmd
from refactor.create_rules_cmd import create_rules
from refactor.gaps_cmd import gaps, spec_cmd
from refactor.manager_cmd import manager
from refactor.tasks_cmd import tasks_cmd
from refactor.jobs import exec_task, leaderboard, next_task, query_tasks, status

cli.add_command(analyze)
cli.add_command(cascade)
cli.add_command(create_skills)
cli.add_command(create_rules)
cli.add_command(config_cmd)
cli.add_command(design)
cli.add_command(plan)
cli.add_command(review)
cli.add_command(start)
cli.add_command(setup)
cli.add_command(exec_task)
cli.add_command(status)
cli.add_command(next_task, name="next")
cli.add_command(query_tasks, name="query")
cli.add_command(autopilot)
cli.add_command(manager)
cli.add_command(gaps)
cli.add_command(tasks_cmd)
cli.add_command(spec_cmd, name="spec")
cli.add_command(agent_command)
cli.add_command(leaderboard)



from refactor.flows import SimpleFlow, GuidedFlow, AutoFlow

@click.command("simple")
@click.argument("project_path", default=".")
def simple_flow(project_path):
    """Run the Simple Flow (Quick Checklist)."""
    SimpleFlow(Path(project_path)).run()

@click.command("guided")
@click.argument("project_path", default=".")
def guided_flow(project_path):
    """Run the Guided Flow (Interactive Wizard)."""
    GuidedFlow(Path(project_path)).run()

@click.command("auto")
@click.argument("project_path", default=".")
@click.option("--discovery-only", is_flag=True, help="Run discovery only (dry run)")
def auto_flow(project_path, discovery_only):
    """Run the Auto Flow (Full Autopilot)."""
    AutoFlow(Path(project_path)).run(discovery_only=discovery_only)


# Register new flow commands
cli.add_command(simple_flow)
cli.add_command(guided_flow)
cli.add_command(auto_flow)

def main():
    cli()


if __name__ == "__main__":
    main()
