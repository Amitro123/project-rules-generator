"""prg quality — analyze and score generated .clinerules files.

Usage:

    prg quality .
    prg quality . --output .clinerules --verbose
    prg quality . --eval-opik --auto-fix
"""

from pathlib import Path
from typing import Optional

import click


@click.command(name="quality")
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option(
    "--output",
    type=click.Path(file_okay=False),
    default=".clinerules",
    show_default=True,
    help="Directory containing generated .clinerules files",
)
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI provider for analysis (auto-detected from env if omitted)",
)
@click.option("--api-key", help="API key (overrides env var)")
@click.option("--eval-opik", is_flag=True, help="Log results to Comet Opik (requires OPIK_API_KEY)")
@click.option("--auto-fix", is_flag=True, help="Attempt to fix low-quality files automatically")
@click.option(
    "--max-iterations",
    type=int,
    default=3,
    show_default=True,
    help="Max improvement iterations for --auto-fix",
)
@click.option("--verbose", "-v", is_flag=True, help="Show per-file breakdowns and suggestions")
def quality_cmd(
    path: str,
    output: str,
    provider: Optional[str],
    api_key: Optional[str],
    eval_opik: bool,
    auto_fix: bool,
    max_iterations: int,
    verbose: bool,
) -> None:
    """Analyze quality of generated .clinerules files.

    Scores rules.md, constitution.md, and skills/index.md against structure,
    clarity, project-grounding, actionability, and consistency criteria.

    Examples:

      \b
      # Score the default output directory
      prg quality .

      \b
      # Verbose breakdown with Opik logging
      prg quality . --verbose --eval-opik
    """
    from cli.analyze_quality import run_quality_check
    from cli.utils import detect_provider, set_api_key_env

    project_path = Path(path).resolve()
    output_dir = project_path / output

    if not output_dir.exists():
        click.echo(f"❌ Output directory not found: {output_dir}", err=True)
        click.echo("💡 Run 'prg analyze .' first to generate .clinerules files.")
        raise SystemExit(1)

    resolved_provider: str = detect_provider(provider, api_key) or ""
    set_api_key_env(resolved_provider, api_key)

    run_quality_check(
        output_dir=output_dir,
        project_path=project_path,
        provider=resolved_provider,
        api_key=api_key,
        eval_opik=eval_opik,
        auto_fix=auto_fix,
        verbose=verbose,
    )
