"""prg manager — Bootstrap PRG memory artifacts (no LLM required)."""

from __future__ import annotations

import logging
from pathlib import Path

import click


@click.command(name="manager")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--verbose/--quiet", default=True)
def manager(project_path, verbose):
    """Bootstrap PRG memory artifacts for this project.

    \b
    Generates any missing:
      .clinerules/rules.md      (coding rules)
      .clinerules/skills/       (skill library)
      tests/                    (test scaffold)
      pytest.ini                (test config)

    No LLM or API key required. For spec.md generation use: prg spec --generate --provider <name>

    \b
    Recommended flow:
      prg manager                        # bootstrap memory (this command)
      prg verify                         # validate project is Ralph-ready
      prg ralph "Add loading states"     # run the feature loop
    """
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")

    from generator.planning.project_manager import ProjectManager

    pm = ProjectManager(project_path=Path(project_path).resolve(), verbose=verbose)
    pm.phase1_setup()
