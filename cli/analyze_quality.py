"""Quality-check and Opik evaluation logic for the analyze command."""

from pathlib import Path
from typing import Optional

import click


def run_quality_check(
    output_dir: Path,
    project_path: Path,
    provider: str,
    api_key: Optional[str],
    eval_opik: bool,
    auto_fix: bool,
    verbose: bool,
) -> None:
    """Analyze quality of generated .clinerules files and (optionally) log to Opik."""
    from rich.console import Console
    from rich.table import Table

    from generator.config import AnalyzerConfig
    from generator.content_analyzer import ContentAnalyzer

    analyzer_config = AnalyzerConfig(enable_opik=eval_opik)
    analyzer = ContentAnalyzer(provider=provider, api_key=api_key, config=analyzer_config)
    if eval_opik and analyzer.opik:
        analyzer.opik.enabled = True

    if verbose:
        click.echo("\n📊 Quality Analysis & Evaluation...")

    files_to_check = []
    for name in ("rules.md", "constitution.md"):
        p = output_dir / name
        if p.exists():
            files_to_check.append(p)
    index_p = output_dir / "skills" / "index.md"
    if index_p.exists():
        files_to_check.append(index_p)

    if not files_to_check:
        click.echo("⚠️  No files found to analyze")
        return

    reports = []
    for filepath in files_to_check:
        content = filepath.read_text(encoding="utf-8")
        report = analyzer.analyze(
            str(filepath.relative_to(output_dir)),
            content,
            project_path=project_path,
        )
        reports.append((filepath, report))

    console = Console()
    table = Table(title="\n📊 Quality Analysis Results")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Top Issue", style="yellow")

    for filepath, report in reports:
        top_issue = report.suggestions[0] if report.suggestions else "None"
        if len(top_issue) > 40:
            top_issue = top_issue[:37] + "..."
        table.add_row(filepath.name, f"{report.score}/100", report.status, top_issue)

    console.print(table)

    if verbose:
        for filepath, report in reports:
            click.echo(f"   {filepath.name}: {report.status}")
            if hasattr(report, "breakdown") and report.breakdown:
                b = report.breakdown
                fields = [
                    ("Structure", b.structure),
                    ("Clarity", b.clarity),
                    ("Project Grounding", b.project_grounding),
                    ("Actionability", b.actionability),
                    ("Consistency", b.consistency),
                ]
                for name, score in fields:
                    icon = "✅" if score >= 15 else "⚠️"
                    click.echo(f"     {icon} {name}: {score}/20")
            elif hasattr(report, "quick_check") and report.quick_check:
                for check, passed in report.quick_check.items():
                    icon = "✅" if passed else "⚠️"
                    click.echo(f"     {icon} {check.replace('_', ' ').title()}")
            if report.suggestions:
                click.echo("     Suggestions:")
                for s in report.suggestions:
                    click.echo(f"       - {s}")
            if eval_opik and analyzer.opik and analyzer.opik.enabled:
                click.echo(f"     🚀 Logged to Opik (Trace ID: {report.status})")
            if auto_fix and "Needs Review" in report.status:
                click.echo(f"     🔧 Auto-fixing {filepath.name}...")
                click.echo("     (Auto-fix temporarily disabled in v1.2.0 Opik update)")
