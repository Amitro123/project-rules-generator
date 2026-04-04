"""Autopilot command — deprecated, redirects to prg ralph."""

import click


@click.command(name="autopilot")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--discovery-only", is_flag=True, hidden=True)
@click.option("--execute-only", is_flag=True, hidden=True)
@click.option("--provider", type=click.Choice(["gemini", "groq", "anthropic", "openai"]), default=None, hidden=True)
@click.option("--api-key", default=None, hidden=True)
@click.option("--verbose/--quiet", default=True, hidden=True)
def autopilot(project_path, discovery_only, execute_only, provider, api_key, verbose):
    """[DEPRECATED] Use 'prg ralph' instead.

    \b
    Old:  prg autopilot .
    New:  prg ralph "describe what you want to build"
    """
    click.echo(
        "⚠️  'prg autopilot' is deprecated and will be removed in v0.4.0.\n"
        "\n"
        "Use the Ralph Feature Loop instead:\n"
        "\n"
        "    prg ralph \"describe what you want to build\"\n"
        "\n"
        "Or for multi-feature discovery:\n"
        "\n"
        "    prg ralph discover\n",
        err=True,
    )
    raise SystemExit(1)
