"""Default tag-resolver implementation for ``filter_skills_by_tech_overlap``.

Bridge between PRG's skill storage (SKILL.md files with YAML frontmatter,
located via ``SkillPathManager``) and the generic filter primitive in
``generator.project_profile``. The filter primitive takes any
``(skill_ref) -> frozenset[str]`` callable — this module supplies the one
the production pipeline uses by default.

Why a separate module
---------------------
``project_profile.py`` is the pure contract layer — no disk I/O, no
YAML parsing, no project-specific knowledge. The tag-resolver IS those
things. Keeping it here lets the contract stay pure and lets tests
substitute their own resolver via dependency injection without monkey-
patching anything.

Caching
-------
File reads are cached per-process via ``functools.lru_cache`` on the
inner reader. Repeated resolves of the same ref during one ``prg
analyze`` run hit the cache, so the filter adds negligible overhead
even when iterating over 50+ skill refs.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Callable, FrozenSet, Iterable, Optional

import yaml

logger = logging.getLogger(__name__)

# Matches a YAML frontmatter block at the start of a markdown file:
# ---
# key: value
# ...
# ---
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)


# --- File-level tag extraction (cached) ------------------------------------


@lru_cache(maxsize=512)
def _tags_from_file(path_str: str) -> FrozenSet[str]:
    """Read tags from a SKILL.md (or .yaml) file. Cached per-process.

    Returns ``frozenset()`` for any failure: missing file, malformed
    frontmatter, no `tags` key, tags value that isn't a list. The caller
    treats empty-set as "tags unknown" (conservative keep by default).
    """
    path = Path(path_str)
    if not path.exists() or not path.is_file():
        return frozenset()

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.debug("skill_tag_resolver: cannot read %s: %s", path, exc)
        return frozenset()

    # Try YAML frontmatter first (markdown files)
    fm_match = _FRONTMATTER_RE.match(content)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError as exc:
            logger.debug("skill_tag_resolver: bad frontmatter in %s: %s", path, exc)
            fm = {}
    else:
        # Maybe a pure YAML file? Try the whole content.
        try:
            fm = yaml.safe_load(content) or {}
            if not isinstance(fm, dict):
                fm = {}
        except yaml.YAMLError:
            fm = {}

    tags_raw = fm.get("tags", [])
    if not isinstance(tags_raw, Iterable) or isinstance(tags_raw, (str, bytes)):
        return frozenset()

    out = set()
    for t in tags_raw:
        if isinstance(t, str) and t.strip():
            out.add(t.strip().lower())
    return frozenset(out)


def clear_tag_cache() -> None:
    """Reset the file-read cache. Tests use this between cases so a
    fixture rewrite during one test doesn't leak into the next."""
    _tags_from_file.cache_clear()


# --- Default resolver factory ---------------------------------------------


def default_tag_resolver(
    path_resolver: Optional[Callable[[str], Optional[Path]]] = None,
) -> Callable[[str], FrozenSet[str]]:
    """Build a tag-resolver callable suitable for
    ``filter_skills_by_tech_overlap``.

    Parameters
    ----------
    path_resolver : callable mapping a skill ref to a Path on disk, or
        ``None`` when the ref can't be resolved. Defaults to
        ``SkillPathManager.get_skill_path``. Tests can inject a custom
        resolver pointing at a tmp directory.

    Returns
    -------
    Callable[[str], FrozenSet[str]]
        Pass this directly as ``tag_resolver`` to
        ``filter_skills_by_tech_overlap``.
    """
    if path_resolver is None:
        from generator.storage.skill_paths import SkillPathManager

        path_resolver = SkillPathManager.get_skill_path

    def _resolve(skill_ref: str) -> FrozenSet[str]:
        try:
            path = path_resolver(skill_ref)
        except Exception:  # noqa: BLE001 — resolver is best-effort
            return frozenset()
        if not path:
            return frozenset()
        return _tags_from_file(str(path))

    return _resolve
