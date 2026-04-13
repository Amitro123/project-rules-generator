"""prg providers — list, test, and benchmark AI providers.

Commands::

    prg providers list                     # Rich table of all providers
    prg providers test [--provider X]      # Live connectivity test
    prg providers benchmark [--prompts N]  # Benchmark & rank
"""

from __future__ import annotations

import os
import sys
import time

import click

from generator.ai.ai_strategy_router import (
    PROVIDER_DEFAULT_MODELS,
    PROVIDER_ENV_KEYS,
    QUALITY_SCORES,
    SPEED_SCORES,
    AIStrategyRouter,
)


@click.group(name="providers")
def providers_group() -> None:
    """Manage and benchmark AI providers."""


# ---------------------------------------------------------------------------
# prg providers list
# ---------------------------------------------------------------------------


@providers_group.command(name="list")
def providers_list() -> None:
    """List all AI providers with status, quality, and speed scores."""
    router = AIStrategyRouter()
    statuses = router.provider_status()

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="[bold]AI Providers[/bold]", show_header=True, header_style="bold cyan")
        table.add_column("Provider", style="bold white")
        table.add_column("Status", justify="center")
        table.add_column("Quality", justify="right")
        table.add_column("Speed", justify="right")
        table.add_column("Default Model", style="dim")
        table.add_column("Env Variable", style="dim")
        table.add_column("Preferred", justify="center")

        for s in statuses:
            table.add_row(
                s["provider"],
                s["status"],
                f"{s['quality']}/100",
                f"{s['speed']}/100",
                s["default_model"],
                s["env_key"],
                "⭐" if s["preferred"] else "",
            )

        console.print()
        console.print(table)
        console.print()

        ready = [s["provider"] for s in statuses if s["has_key"]]
        if ready:
            console.print(f"[green]Ready providers:[/green] {', '.join(ready)}")
        else:
            console.print("[yellow]No providers ready. Set at least one API key.[/yellow]")
        console.print()

    except ImportError:
        # Plain fallback if rich not available
        click.echo(f"{'Provider':<14} {'Status':<14} {'Quality':>8} {'Speed':>7}  Env Variable")
        click.echo("-" * 70)
        for s in statuses:
            click.echo(
                f"{s['provider']:<14} {s['status']:<14} " f"{s['quality']:>6}/100 {s['speed']:>5}/100  {s['env_key']}"
            )


# ---------------------------------------------------------------------------
# prg providers test
# ---------------------------------------------------------------------------


@providers_group.command(name="test")
@click.option("--provider", default=None, help="Test a specific provider (default: all with keys)")
def providers_test(provider: str | None) -> None:
    """Send a test prompt to verify provider connectivity and measure latency."""
    test_prompt = "Reply with exactly three words: PROVIDER_TEST_OK"
    to_test = [provider] if provider else list(PROVIDER_ENV_KEYS.keys())

    any_tested = False
    for p in to_test:
        env_key = PROVIDER_ENV_KEYS.get(p, f"{p.upper()}_API_KEY")
        has_key = bool(os.getenv(env_key)) or (p == "gemini" and bool(os.getenv("GOOGLE_API_KEY")))
        if not has_key:
            click.echo(f"⚠️  {p:<12} — no API key ({env_key} not set)")
            continue

        any_tested = True
        try:
            from generator.ai.factory import create_ai_client

            t0 = time.perf_counter()
            client = create_ai_client(p)
            result = client.generate(test_prompt, max_tokens=20)
            latency = time.perf_counter() - t0
            click.echo(f"✅ {p:<12} — {latency:.2f}s → {result.strip()[:60]}")
        except Exception as exc:  # noqa: BLE001 — CLI boundary: AI provider test can fail in many ways
            click.echo(f"❌ {p:<12} — {exc}")

    if not any_tested:
        click.echo("No providers with API keys found. Set at least one of:")
        for p, key in PROVIDER_ENV_KEYS.items():
            click.echo(f"  {key}")


# ---------------------------------------------------------------------------
# prg providers benchmark
# ---------------------------------------------------------------------------


@providers_group.command(name="benchmark")
@click.option("--prompts", default=3, show_default=True, help="Number of test prompts to run")
def providers_benchmark(prompts: int) -> None:
    """Benchmark available providers — ranks by composite quality/speed score."""
    test_prompts = [
        "Write one Python function that adds two numbers. Return only the code.",
        "What is dependency injection? Answer in one sentence.",
        "Write a pytest test for a function called add(a, b) -> int. Return only the code.",
    ][:prompts]

    results: dict = {}

    for provider in PROVIDER_ENV_KEYS:
        env_key = PROVIDER_ENV_KEYS[provider]
        if not os.getenv(env_key):
            continue

        click.echo(f"⏳ Benchmarking {provider}...")
        try:
            from generator.ai.factory import create_ai_client

            client = create_ai_client(provider)
            latencies: list[float] = []  # list[float] requires Python 3.10+
            for prompt in test_prompts:
                t0 = time.perf_counter()
                client.generate(prompt, max_tokens=200)
                latencies.append(time.perf_counter() - t0)

            avg_latency = sum(latencies) / len(latencies)
            results[provider] = {
                "avg_latency": avg_latency,
                "quality": QUALITY_SCORES.get(provider, 50),
                "speed": SPEED_SCORES.get(provider, 50),
            }
            click.echo(f"   ✅ done — avg {avg_latency:.2f}s")
        except Exception as exc:  # noqa: BLE001 — CLI boundary: AI provider benchmark can fail in many ways
            click.echo(f"   ❌ {provider}: {exc}")

    if not results:
        click.echo("\nNo providers available for benchmarking. Set at least one API key.")
        sys.exit(1)

    # Composite score: quality score / latency (quality per second)
    def _composite(data: dict) -> float:
        return data["quality"] / max(data["avg_latency"], 0.01)

    ranked = sorted(results.items(), key=lambda x: -_composite(x[1]))

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="[bold]Provider Benchmark Results[/bold]", header_style="bold green")
        table.add_column("Rank", justify="center", style="bold")
        table.add_column("Provider", style="bold white")
        table.add_column("Avg Latency", justify="right")
        table.add_column("Quality/100", justify="right")
        table.add_column("Speed/100", justify="right")
        table.add_column("Composite ↑", justify="right", style="cyan")

        for i, (p, data) in enumerate(ranked, 1):
            composite = _composite(data)
            table.add_row(
                str(i),
                p,
                f"{data['avg_latency']:.2f}s",
                str(data["quality"]),
                str(data["speed"]),
                f"{composite:.1f}",
            )

        console.print()
        console.print(table)
        console.print()
        console.print(f"[bold green]🏆 Recommended:[/bold green] {ranked[0][0]}")
        console.print()

    except ImportError:
        click.echo("\nBenchmark Results (quality / latency):")
        for i, (p, data) in enumerate(ranked, 1):
            click.echo(f"  {i}. {p:<12} avg={data['avg_latency']:.2f}s  quality={data['quality']}")
