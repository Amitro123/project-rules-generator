"""prg skills — skill inspection and validation sub-commands."""

import logging
from pathlib import Path
from typing import Optional

import click

logger = logging.getLogger(__name__)


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
    except Exception as exc:
        logger.debug("Could not resolve skill %r via SkillsManager: %s", name_or_path, exc)

    return None, None


def _parse_frontmatter(content: str):
    """Return (meta_dict, body_str)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    yaml_block = content[3:end].strip()
    body = content[end + 4 :]
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

    # Load usage stats once
    try:
        from generator.skill_tracker import SkillTracker

        tracker = SkillTracker()
        all_stats = tracker.all_stats()
    except Exception:
        all_stats = {}

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
        except Exception as exc:
            logger.debug("Could not read skill file %s: %s", skill_path, exc)

        stats = all_stats.get(name, {})
        score_str = f"{stats['score']:.0%}" if "score" in stats else "-"
        matches = stats.get("match_count", 0) or "-"

        fm_status = "✓" if has_frontmatter else "✗"
        rows.append((name, layer, trigger_count, tools_str or "(none)", fm_status, score_str, matches))

    # Print table
    col_name = max(len(r[0]) for r in rows)
    col_layer = max(len(r[1]) for r in rows)

    header = (
        f"{'Name':<{col_name}}  {'Layer':<{col_layer}}  {'Trig':>4}  "
        f"{'Tools':<28}  FM  {'Score':>5}  {'Hits':>4}"
    )
    click.echo(header)
    click.echo("-" * len(header))
    for name, layer, triggers, tools, fm, score, hits in rows:
        tools_display = tools[:26] + ".." if len(tools) > 28 else tools
        click.echo(
            f"{name:<{col_name}}  {layer:<{col_layer}}  {triggers:>4}  "
            f"{tools_display:<28}  {fm:<2}  {score:>5}  {str(hits):>4}"
        )

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
# prg skills feedback
# ---------------------------------------------------------------------------


@skills_group.command(name="feedback")
@click.argument("skill_name")
@click.option("--useful", "vote", flag_value="useful", help="Mark skill as useful.")
@click.option("--not-useful", "vote", flag_value="not_useful", help="Mark skill as not useful.")
def skills_feedback(skill_name, vote):
    """Record useful / not-useful feedback for a skill.

    Scores accumulate across sessions and are used by 'prg skills stale'
    to flag candidates for regeneration.

    Example:
      prg skills feedback pytest-testing-workflow --useful
      prg skills feedback pytest-testing-workflow --not-useful
    """
    if not vote:
        click.echo("Specify --useful or --not-useful.", err=True)
        raise SystemExit(1)

    # Warn if the skill name doesn't match any known skill (prevents zombie entries)
    try:
        from generator.skills_manager import SkillsManager

        sm = SkillsManager(project_path=Path.cwd())
        known = sm.list_skills()
        if skill_name not in known:
            click.echo(
                f"Warning: '{skill_name}' not found in known skills. "
                "Check spelling with: prg skills list --all",
                err=True,
            )
            if not click.confirm("Record feedback anyway?", default=False):
                raise SystemExit(0)
    except SystemExit:
        raise
    except Exception:
        pass  # Don't block feedback if SkillsManager lookup fails

    from generator.skill_tracker import SkillTracker

    tracker = SkillTracker()
    is_useful = vote == "useful"
    score = tracker.record_feedback(skill_name, useful=is_useful)
    stats = tracker.get_stats(skill_name)

    label = "useful" if is_useful else "not useful"
    click.echo(f"Recorded: '{skill_name}' marked as {label}.")
    click.echo(
        f"Score: {score:.0%}  "
        f"({stats.get('useful_count', 0)} useful / "
        f"{stats.get('not_useful_count', 0)} not useful / "
        f"{stats.get('match_count', 0)} matches)"
    )


# ---------------------------------------------------------------------------
# prg skills stale
# ---------------------------------------------------------------------------


@skills_group.command(name="stale")
@click.option("--threshold", default=0.3, type=float, show_default=True, help="Score below this is flagged.")
def skills_stale(threshold):
    """List skills with low feedback scores that may need regeneration.

    Only skills with at least 3 feedback votes are considered. Regenerate with:

      prg analyze . --create-skill <name>
    """
    from generator.skill_tracker import MIN_FEEDBACK_FOR_FLAG, SkillTracker

    tracker = SkillTracker()
    low = tracker.get_low_scoring(threshold=threshold)

    if not low:
        click.echo(f"No skills below {threshold:.0%} score threshold (min {MIN_FEEDBACK_FOR_FLAG} votes required).")
        return

    click.echo(f"Skills below {threshold:.0%} score ({len(low)} found):\n")
    for name in low:
        stats = tracker.get_stats(name)
        score = stats.get("score", 0.0)
        useful = stats.get("useful_count", 0)
        not_useful = stats.get("not_useful_count", 0)
        matches = stats.get("match_count", 0)
        click.echo(f"  {name}")
        click.echo(f"    score={score:.0%}  useful={useful}  not-useful={not_useful}  matches={matches}")
        click.echo(f"    → prg analyze . --create-skill {name}")
        click.echo()


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
