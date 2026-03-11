# ruff: noqa: E402
"""CLI orchestrator for project rules and skills generator."""

import sys
from pathlib import Path

# Fix Windows console encoding so emoji/Unicode CLI output renders correctly
if sys.platform == "win32":
    import ctypes

    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)  # UTF-8 codepage
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

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
        if args and args[0] not in self.commands and args[0] not in ("--help", "--version", "-h"):
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


from cli.agent import agent_command, design, plan, review, setup, start

# Import and register commands at module level
from cli.analyze_cmd import analyze
from cli.autopilot_cmd import autopilot
from cli.create_rules_cmd import create_rules
from cli.gaps_cmd import gaps, spec_cmd
from cli.jobs import exec_task, leaderboard, next_task, query_tasks, status
from cli.manager_cmd import manager
from cli.providers_cmd import providers_group
from cli.tasks_cmd import tasks_cmd

cli.add_command(analyze)
cli.add_command(create_rules)
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
cli.add_command(providers_group, name="providers")


def main():
    cli()


if __name__ == "__main__":
    main()
