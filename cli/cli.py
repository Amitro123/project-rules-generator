"""CLI orchestrator for project rules and skills generator."""

from pathlib import Path

from prg_utils.logger import ensure_utf8_streams

# Fix Windows console encoding so emoji/Unicode CLI output renders correctly.
# Library consumers should import the same helper from prg_utils.logger rather
# than duplicating the ctypes/reconfigure dance here.
ensure_utf8_streams()

import click  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from cli._version import __version__  # noqa: E402

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
@click.version_option(version=__version__)
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
from cli.create_rules_cmd import create_rules
from cli.feature_cmd import feature
from cli.gaps_cmd import gaps, spec_cmd
from cli.init_cmd import init
from cli.jobs import exec_task, leaderboard, next_task, query_tasks, status
from cli.manager_cmd import manager
from cli.providers_cmd import providers_group
from cli.quality_cmd import quality_cmd
from cli.ralph_cmd import ralph_group
from cli.skills_cmd import skills_group
from cli.tasks_cmd import tasks_cmd
from cli.verify_cmd import verify
from cli.watch_cmd import watch

cli.add_command(analyze)
cli.add_command(init)
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
cli.add_command(manager)
cli.add_command(verify)
cli.add_command(gaps)
cli.add_command(tasks_cmd)
cli.add_command(spec_cmd, name="spec")
cli.add_command(agent_command)
cli.add_command(leaderboard)
cli.add_command(providers_group, name="providers")
cli.add_command(quality_cmd, name="quality")
cli.add_command(skills_group, name="skills")
cli.add_command(watch)
cli.add_command(feature)
cli.add_command(ralph_group, name="ralph")


def _sanitize_env_from_dotenv() -> None:
    """Re-parse .env to handle non-standard syntax that python-dotenv silently skips.

    python-dotenv requires KEY=value. Files with KEY:'value' or KEY: value
    (colon delimiter, optional quotes) are silently ignored, leaving API keys
    unset. This function handles those lines so the user gets a working key
    instead of a silent fallback to a lower-priority env var.

    Quote handling: only matching outer quotes are stripped (e.g. 'val' → val,
    "val" → val). Mismatched or embedded quotes are left in the value as-is
    rather than silently truncating.
    """
    import os
    import re

    env_path = Path(".env")
    if not env_path.exists():
        return

    # Capture KEY then the entire raw value — handle quoting explicitly below
    line_re = re.compile(r"""^\s*([\w]+)\s*[:=]\s*(.+?)\s*$""")
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("#") or not raw.strip():
            continue
        m = line_re.match(raw)
        if not m:
            continue
        key, raw_val = m.group(1), m.group(2)
        # Strip matching outer quotes only — never truncate on embedded quotes
        if len(raw_val) >= 2 and raw_val[0] == raw_val[-1] and raw_val[0] in ('"', "'"):
            value = raw_val[1:-1]
        else:
            value = raw_val
        if key not in os.environ and value:
            os.environ[key] = value


def main():
    load_dotenv()  # standard KEY=value lines
    _sanitize_env_from_dotenv()  # catch KEY:'value' / KEY: value syntax
    cli()


if __name__ == "__main__":
    main()
