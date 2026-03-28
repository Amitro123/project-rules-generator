"""prg skills — skill inspection and validation sub-commands."""

from pathlib import Path
from typing import Optional

import click


def _resolve_skill(name_or_path: str, project_path: Path):
    """Return (skill_path, layer) for a skill name or file path.

    Tries, in order:
    1. Literal file path (absolute or relative to cwd)
    2. SkillsManager resolution by name
    """
    # 1. Explicit path
    candidate = Path(name_or_path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / name_or_path
    if candidate.exists() and candidate.is_file():
        return candidate, "file"

    # 2. Name resolution via SkillsManager
    try:
        from generator.skills_manager import SkillsManager

        sm = SkillsManager(project_path=project_path)
        skills = sm.list_skills()

        # Exact name match first
        if name_or_path in skills:
            info = skills[name_or_path]
            return Path(info["path"]), info["type"]

        # Partial / basename match
        for skill_name, info in skills.items():
            if skill_name.lower() == name_or_path.lower():
                return Path(info["path"]), info["type"]
            skill_file = Path(info["path"])
            if skill_file.stem.lower() == name_or_path.lower():
                return skill_file, info["type"]
            if skill_file.parent.name.lower() == name_or_path.lower():
                return skill_file, info["type"]
    except Exception:
        pass

    return None, None


def _parse_frontmatter(content: str):
    """Return (meta_dict, body_str)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    yaml_block = content[3:end].strip()
    body = content[end + 4:]
    try:
        import yaml

        meta = yaml.safe_load(yaml_block) or {}
    except Exception:
        meta = {}
    return meta if isinstance(meta, dict) else {}, body


@click.group(name="skills")
def skills_group():
    """Inspect, validate, and display skills."""
    pass


# ---------------------------------------------------------------------------
# prg skills list
# ---------------------------------------------------------------------------


@skills_group.command(name="list")
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--all", "show_all", is_flag=True, default=False, help="Include global builtin skills")
def skills_list(path, show_all):
    """List all skills with layer, trigger count, and tool info."""
    project_path = Path(path).resolve()

    try:
        from generator.skills_manager import SkillsManager

        sm = SkillsManager(project_path=project_path)
        skills = sm.list_skills()
    except Exception as exc:
        click.echo(f"Error loading skills: {exc}", err=True)
        raise SystemExit(1)

    if not skills:
        click.echo("No skills found.")
        return

    # Filter out builtin unless --all
    if not show_all:
        skills = {k: v for k, v in skills.items() if v["type"] != "builtin"}

    if not skills:
        click.echo("No project or learned skills found. Use --all to include builtins.")
        return

    # Compute column widths
    rows = []
    for name, info in sorted(skills.items()):
        skill_path = Path(info["path"])
        layer = info["type"]

        # Parse frontmatter
        has_frontmatter = False
        trigger_count = 0
        tools_str = ""
        try:
            content = skill_path.read_text(encoding="utf-8", errors="replace")
            meta, _ = _parse_frontmatter(content)
            has_frontmatter = bool(meta)

            triggers = meta.get("triggers") or meta.get("auto_triggers") or []
            if isinstance(triggers, list):
                trigger_count = len(triggers)

            tools = meta.get("allowed-tools") or meta.get("tools") or ""
            if isinstance(tools, list):
                tools_str = " ".join(tools)
            elif isinstance(tools, str):
                tools_str = tools
        except Exception:
            pass

        fm_status = "✓" if has_frontmatter else "✗ no frontmatter"
        rows.append((name, layer, trigger_count, tools_str or "(none)", fm_status))

    # Print table
    col_name = max(len(r[0]) for r in rows)
    col_layer = max(len(r[1]) for r in rows)

    header = (
        f"{'Name':<{col_name}}  {'Layer':<{col_layer}}  {'Triggers':>8}  {'Tools':<30}  FM"
    )
    click.echo(header)
    click.echo("-" * len(header))
    for name, layer, triggers, tools, fm in rows:
        tools_display = tools[:28] + ".." if len(tools) > 30 else tools
        click.echo(f"{name:<{col_name}}  {layer:<{col_layer}}  {triggers:>8}  {tools_display:<30}  {fm}")

    click.echo()
    click.echo(f"{len(rows)} skill(s) shown. Use --all to include builtins.")


# ---------------------------------------------------------------------------
# prg skills validate
# ---------------------------------------------------------------------------


@skills_group.command(name="validate")
@click.argument("name_or_path")
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
def skills_validate(name_or_path, path):
    """Validate a skill against quality checks. Exits 1 if any checks fail."""
    project_path = Path(path).resolve()
    skill_path, layer = _resolve_skill(name_or_path, project_path)

    if skill_path is None:
        click.echo(f"Skill not found: {name_or_path}", err=True)
        raise SystemExit(1)

    try:
        content = skill_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        click.echo(f"Cannot read {skill_path}: {exc}", err=True)
        raise SystemExit(1)

    from generator.utils.quality_checker import validate_quality

    report = validate_quality(content)

    click.echo(f"Skill : {skill_path.parent.name}/{skill_path.name}")
    click.echo(f"Layer : {layer}")
    click.echo(f"Score : {report.score:.0f}/100  ({'PASS' if report.passed else 'FAIL'})")
    click.echo()

    if report.issues:
        click.echo("Issues (must fix):")
        for issue in report.issues:
            click.echo(f"  ✗ {issue}")
        click.echo()

    if report.warnings:
        click.echo("Warnings:")
        for warning in report.warnings:
            click.echo(f"  ⚠ {warning}")
        click.echo()

    if report.suggestions:
        click.echo("Suggestions:")
        for suggestion in report.suggestions:
            click.echo(f"  → {suggestion}")
        click.echo()

    if not report.passed:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# prg skills show
# ---------------------------------------------------------------------------


@skills_group.command(name="show")
@click.argument("name_or_path")
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
def skills_show(name_or_path, path):
    """Pretty-print a skill's frontmatter and body."""
    project_path = Path(path).resolve()
    skill_path, layer = _resolve_skill(name_or_path, project_path)

    if skill_path is None:
        click.echo(f"Skill not found: {name_or_path}", err=True)
        raise SystemExit(1)

    try:
        content = skill_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        click.echo(f"Cannot read {skill_path}: {exc}", err=True)
        raise SystemExit(1)

    meta, body = _parse_frontmatter(content)

    # Header
    name = meta.get("name") or skill_path.parent.name
    click.echo("=" * 60)
    click.echo(f"  {name}  [{layer}]")
    click.echo("=" * 60)
    click.echo()

    # Frontmatter table
    if meta:
        click.echo("Frontmatter")
        click.echo("-" * 40)
        for key, value in meta.items():
            if isinstance(value, list):
                click.echo(f"  {key}:")
                for item in value:
                    click.echo(f"    - {item}")
            elif isinstance(value, str) and "\n" in value:
                click.echo(f"  {key}:")
                for line in value.strip().splitlines():
                    click.echo(f"    {line}")
            else:
                click.echo(f"  {key}: {value}")
        click.echo()
    else:
        click.echo("(no YAML frontmatter found)")
        click.echo()

    # Body
    if body.strip():
        click.echo("Body")
        click.echo("-" * 40)
        click.echo(body.strip())
    else:
        click.echo("(empty body)")
