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
from refactor.jobs import exec_task, leaderboard, status

cli.add_command(analyze)
cli.add_command(design)
cli.add_command(plan)
cli.add_command(review)
cli.add_command(start)
cli.add_command(setup)
cli.add_command(exec_task)
cli.add_command(status)
cli.add_command(agent_command)
cli.add_command(leaderboard)


def main():
    cli()


if __name__ == "__main__":
    main()
