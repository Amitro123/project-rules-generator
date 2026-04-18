"""LLM-output hardening utilities.

Problems this module solves:

1. **Silent truncation** — LLM hits max_tokens, response ends mid-sentence,
   downstream regex parsers return ``""`` without signalling failure.
   ``looks_truncated()`` detects the common cases.

2. **Parse-failure blindness** — a single LLM call either produces parseable
   output or doesn't.  There is no retry with a repair hint.
   ``generate_with_validator()`` retries with a repair-oriented prompt when a
   validator callable rejects the output.

3. **File-path hallucination** — LLMs emit ``src/api.py`` regardless of the
   actual project layout because ``src/`` is overwhelmingly common in their
   training data.  ``discover_source_dirs()`` reports the project's real
   top-level source directories; ``ground_paths()`` rewrites paths that
   reference non-existent top-level dirs.

Nothing in this module knows about Design or SubTask specifically — it is a
thin utility layer usable from any generator.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Callable, List, Optional, Protocol, Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Truncation detection
# ---------------------------------------------------------------------------

# A response that ends with one of these is almost certainly cut off mid-thought.
# We deliberately err on the side of false negatives — a properly-terminated
# response that happens to end with `:` is rare, and a false-positive retry is
# cheap compared with silently handing back a broken document.
_TRUNCATION_TAIL_PATTERNS = (
    re.compile(r"[,:;]\s*$"),  # ends with a listing punctuator
    re.compile(r"\b(and|or|but|the|a|an|to|for|with|of|in|on)\s*$", re.IGNORECASE),
    re.compile(r"```[a-z]*\s*$", re.IGNORECASE),  # open code fence never closed
    re.compile(r"\[\s*$"),  # open bracket list
)


def looks_truncated(text: str, *, min_length: int = 100) -> bool:
    """Return True when the LLM output appears cut off mid-sentence.

    Heuristics combined with an OR:

    * Ends with a listing-style punctuator (``,`` ``:`` ``;``)
    * Ends with a stop-word / conjunction the LLM was clearly continuing from
    * Contains an odd number of triple-backtick fences (unclosed code block)
    * Exact length under ``min_length`` characters (too short to be complete)

    Not a guarantee of truncation, but good enough to trigger a retry.
    """
    if not text:
        return True
    stripped = text.rstrip()
    if len(stripped) < min_length:
        return True

    # Unclosed ``` fence
    if stripped.count("```") % 2 == 1:
        return True

    tail = stripped[-60:]  # enough to cover "...response could not be found because"
    for pattern in _TRUNCATION_TAIL_PATTERNS:
        if pattern.search(tail):
            return True

    return False


# ---------------------------------------------------------------------------
# Retry loop with validator-aware repair
# ---------------------------------------------------------------------------


class _SupportsGenerate(Protocol):
    def generate(
        self,
        prompt: str,
        max_tokens: int = ...,
        model: Optional[str] = ...,
        temperature: float = ...,
        system_message: Optional[str] = ...,
    ) -> str: ...


Validator = Callable[[str], bool]
"""A validator returns True when the LLM output is acceptable."""


def generate_with_validator(
    client: _SupportsGenerate,
    prompt: str,
    *,
    validator: Optional[Validator] = None,
    max_tokens: int = 4000,
    model: Optional[str] = None,
    temperature: float = 0.7,
    system_message: Optional[str] = None,
    max_retries: int = 1,
    detect_truncation: bool = True,
) -> str:
    """Call ``client.generate`` with retry on validation/truncation failure.

    The first retry repeats the call at lower temperature to encourage the LLM
    to stay on-format.  Additional retries append an explicit repair hint so
    the LLM knows its previous answer was rejected.

    ``validator`` is optional; when ``None`` only the truncation heuristic (if
    enabled) drives retries.  Errors from the client are caught and treated as
    an invalid empty response, exhausting retries before returning ``""``.
    """
    last_result = ""
    for attempt in range(max_retries + 1):
        current_temp = temperature if attempt == 0 else max(0.1, temperature - 0.3)
        attempt_prompt = prompt
        if attempt > 0:
            attempt_prompt = (
                prompt + "\n\n---\n" + "NOTE: Your previous response was rejected (empty, truncated, or "
                "failed validation). Respond with the COMPLETE answer in the exact "
                "format requested. Do not apologise; do not repeat instructions."
            )
        try:
            result = client.generate(
                attempt_prompt,
                max_tokens=max_tokens,
                model=model,
                temperature=current_temp,
                system_message=system_message,
            )
        except Exception as exc:  # noqa: BLE001 — treat any SDK error as retryable
            logger.warning("LLM call failed on attempt %d: %s", attempt + 1, exc)
            result = ""

        last_result = result or ""

        if detect_truncation and looks_truncated(last_result):
            logger.warning(
                "LLM response looks truncated on attempt %d (len=%d)",
                attempt + 1,
                len(last_result),
            )
            continue

        if validator is None or validator(last_result):
            return last_result

        logger.debug("Validator rejected LLM output on attempt %d", attempt + 1)

    return last_result


# ---------------------------------------------------------------------------
# Repo-tree grounding
# ---------------------------------------------------------------------------

# Directories we never treat as candidate source dirs, even when they contain code.
_SOURCE_DIR_BLOCKLIST = frozenset(
    {
        ".git",
        ".github",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
        "htmlcov",
        ".tox",
        ".idea",
        ".vscode",
        "tests",
        "test",
        "docs",
        "doc",
        "examples",
        "example",
    }
)

# Common source-layout conventions; presence of any of these (in the order given)
# wins over heuristic discovery.
_CONVENTIONAL_SOURCE_DIRS = ("src", "lib", "app")


def discover_source_dirs(project_path: Path) -> List[str]:
    """Return real top-level source directories for ``project_path``.

    Rules:

    * ``src/``, ``lib/``, ``app/`` win when they exist.
    * Otherwise any non-blocklisted directory that contains at least one
      ``*.py`` / ``*.ts`` / ``*.js`` / ``*.go`` / ``*.rs`` file is included.
    * Hidden directories (``.foo``) are always skipped.

    The returned list is sorted alphabetically for deterministic prompts.
    Returns an empty list when ``project_path`` is not a directory.
    """
    if not project_path or not project_path.is_dir():
        return []

    conventional = [d for d in _CONVENTIONAL_SOURCE_DIRS if (project_path / d).is_dir()]
    if conventional:
        return conventional

    found: List[str] = []
    for child in sorted(project_path.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(".") or name in _SOURCE_DIR_BLOCKLIST:
            continue
        try:
            if any(child.rglob("*.py")) or any(child.rglob("*.ts")) or any(child.rglob("*.go")):
                found.append(name)
        except (OSError, PermissionError):
            continue
    return found


def _path_top_segment(path: str) -> str:
    """Return the first path segment (handles both `/` and `\\`)."""
    cleaned = path.strip().strip("`").lstrip("./").replace("\\", "/")
    if not cleaned:
        return ""
    return cleaned.split("/", 1)[0]


def ground_paths(
    paths: Sequence[str],
    project_path: Optional[Path],
    *,
    allowed_top_dirs: Optional[Sequence[str]] = None,
) -> List[str]:
    """Rewrite or drop paths whose top-level directory does not exist.

    If an LLM emits ``src/api.py`` but the project has no ``src/`` directory
    and does have (say) ``generator/``, we rewrite the path to
    ``generator/api.py``.  If no reasonable replacement exists, the path is
    kept verbatim (we never silently drop a path — that would hide the bug
    from the reviewer).

    ``allowed_top_dirs`` overrides auto-discovery.  When ``project_path`` is
    ``None`` and no override is given, the input is returned unchanged.
    """
    if not paths:
        return list(paths)

    if allowed_top_dirs is None:
        if project_path is None:
            return list(paths)
        allowed_top_dirs = discover_source_dirs(project_path)

    if not allowed_top_dirs:
        return list(paths)

    allowed_set = {d.strip("/") for d in allowed_top_dirs if d.strip("/")}
    if not allowed_set:
        return list(paths)

    # Pick a single canonical replacement (first in the list) to keep output
    # coherent — mixing `generator/` and `cli/` in one rewrite is confusing.
    replacement = next(iter(allowed_top_dirs))

    result: List[str] = []
    for p in paths:
        top = _path_top_segment(p)
        if not top:
            result.append(p)
            continue
        # Path points somewhere that really exists → leave it alone.
        if top in allowed_set:
            result.append(p)
            continue
        # File with no directory component (e.g. "README.md") — always keep.
        if "/" not in p.strip().strip("`").replace("\\", "/"):
            result.append(p)
            continue
        # Rewrite: swap the hallucinated top segment with a real one.
        cleaned = p.strip().strip("`").replace("\\", "/")
        _, rest = cleaned.split("/", 1)
        rewritten = f"{replacement}/{rest}"
        logger.info("Grounding hallucinated path %r → %r", p, rewritten)
        result.append(rewritten)

    return result


# ---------------------------------------------------------------------------
# Convenience validators for the common cases
# ---------------------------------------------------------------------------


def require_sections(*headings: str) -> Validator:
    """Build a validator that checks each heading appears in the text.

    Matches loosely: ``## Foo`` / ``### Foo`` / ``Foo:`` all count.  Case-insensitive.
    """
    normalised = [h.lower() for h in headings]

    def _check(text: str) -> bool:
        body = text.lower()
        return all(h in body for h in normalised)

    return _check


def require_min_count(pattern: str, minimum: int) -> Validator:
    """Build a validator that requires ``pattern`` to match ``minimum`` times."""
    compiled = re.compile(pattern, re.MULTILINE | re.IGNORECASE)

    def _check(text: str) -> bool:
        return len(compiled.findall(text)) >= minimum

    return _check


# ---------------------------------------------------------------------------
# Placeholder detection — LLMs sometimes echo the template's [bracket hints]
# back verbatim instead of filling them in.  Detecting this lets us retry.
# ---------------------------------------------------------------------------

# Exact placeholders that appear in the skill-generation prompt template.
# Matching on the *whole* placeholder is safer than matching any `[...]`,
# because legitimate markdown links and image alt-text also contain brackets.
_PLACEHOLDER_PATTERNS = (
    re.compile(r"\[One sentence:[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[First step[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[Second step[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[Third step[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[trigger phrase \d+\]", re.IGNORECASE),
    re.compile(r"\[Non-negotiable rule \d+\]", re.IGNORECASE),
    re.compile(r"\[WHY this step matters[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[What to do\]", re.IGNORECASE),
    re.compile(r"\[runnable command\]", re.IGNORECASE),
    re.compile(r"\[runnable check/test command\]", re.IGNORECASE),
    re.compile(r"\[What this skill produces\]", re.IGNORECASE),
    re.compile(r"\[Files created or modified\]", re.IGNORECASE),
    re.compile(r"\[bad pattern[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[good pattern\]", re.IGNORECASE),
    re.compile(r"\[describes the pain[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[another trigger scenario[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[comma-separated negative triggers\]", re.IGNORECASE),
    re.compile(r"\{\{Skill Name Title Case\}\}", re.IGNORECASE),
    re.compile(r"\[relevant, tags, here\]", re.IGNORECASE),
)


def contains_unfilled_placeholders(text: str) -> bool:
    """Return True when ``text`` contains a literal prompt-template placeholder.

    LLMs occasionally echo guidance like ``[One sentence: what problem does
    this solve]`` verbatim instead of filling it in. This happens most often
    with smaller models or when context is thin. The validator lets us retry
    with a repair hint before returning broken output to the user.
    """
    if not text:
        return False
    for pattern in _PLACEHOLDER_PATTERNS:
        if pattern.search(text):
            return True
    return False


def reject_unfilled_placeholders(text: str) -> bool:
    """Validator form of :func:`contains_unfilled_placeholders` — returns True
    when the text is *clean* (no unfilled placeholders), matching the
    :data:`Validator` protocol used by :func:`generate_with_validator`.
    """
    return not contains_unfilled_placeholders(text)
