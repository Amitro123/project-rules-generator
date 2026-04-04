"""prg manager — Bootstrap and verify the PRG memory layer before running Ralph."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from cli.utils import detect_provider as _detect_provider
from cli.utils import set_api_key_env as _set_api_key


@click.command(name="manager")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI provider for generating spec.md and rules (optional).",
)
@click.option("--api-key", default=None, help="Override API key from environment.")
@click.option("--setup-only", is_flag=True, default=False, help="Run Phase 1 (setup) only, skip verification.")
@click.option("--verify-only", is_flag=True, default=False, help="Run Phase 2 (verify) only, skip setup.")
@click.option("--verbose/--quiet", default=True)
def manager(project_path, provider, api_key, setup_only, verify_only, verbose):
    """Bootstrap and verify PRG memory artifacts before running Ralph.

    \b
    Phase 1 (Setup)  — generates missing rules, skills, spec.md, tests/
    Phase 2 (Verify) — runs PreflightChecker; fails loudly if project isn't ready

    \b
    Typical workflow:
      prg manager                        # bootstrap + verify
      prg ralph "Add loading states"     # consume memory, iterate autonomously

    \b
    With AI-generated spec.md:
      prg manager --provider gemini
    """
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")

    provider = _detect_provider(provider, api_key)
    _set_api_key(provider, api_key)

    from generator.planning.project_manager import ProjectManager

    pm = ProjectManager(
        project_path=Path(project_path).resolve(),
        provider=provider,
        api_key=api_key,
        verbose=verbose,
    )

    if setup_only:
        pm.phase1_setup()
    elif verify_only:
        pm.phase2_verify()
    else:
        pm.run()
