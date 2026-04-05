"""prg verify — Validate the project is Ralph-ready."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click


@click.command(name="verify")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--verbose/--quiet", default=True)
def verify(project_path, verbose):
    """Run preflight checks and confirm the project is Ralph-ready.

    \b
    Checks:
      - .clinerules/rules.md exists and is non-empty
      - .clinerules/skills/ exists
      - README.md present
      - tests/ directory exists
      - No obvious dependency issues

    Exits with code 1 if any critical check fails.

    \b
    Recommended flow:
      prg manager                        # bootstrap memory
      prg verify                         # validate (this command)
      prg ralph "Add loading states"     # run the feature loop
    """
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")

    from generator.planning.preflight import PreflightChecker

    checker = PreflightChecker(
        project_path=Path(project_path).resolve(),
        task_description="prg verify readiness check",
    )
    report = checker.run_checks()

    click.echo(report.format_report())

    if not report.all_passed:
        failed = [c.name for c in report.failed_checks]
        click.echo(f"\n❌ Failed checks: {', '.join(failed)}", err=True)
        click.echo("Fix the issues above, then re-run `prg verify` before `prg ralph`.", err=True)
        sys.exit(1)

    click.echo('\n✅ Project is Ralph-ready. Run: prg ralph "<feature description>"')
