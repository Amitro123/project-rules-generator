"""Project Manager command — deprecated, redirects to prg ralph discover."""

import click


@click.command(name="manager")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--provider", type=click.Choice(["gemini", "groq", "anthropic", "openai"]), default=None, hidden=True)
@click.option("--api-key", default=None, hidden=True)
@click.option("--verbose/--quiet", default=True, hidden=True)
def manager(project_path, provider, api_key, verbose):
    """[DEPRECATED] Use 'prg ralph discover' instead.

    \b
    Old:  prg manager .
    New:  prg ralph discover
    """
    click.echo(
        "⚠️  'prg manager' is deprecated and will be removed in v0.4.0.\n"
        "\n"
        "Use Ralph discover instead:\n"
        "\n"
        "    prg ralph discover\n"
        "    prg ralph discover --run   # execute features automatically\n",
        err=True,
    )
    raise SystemExit(1)
