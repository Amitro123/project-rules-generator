"""Skill-specific extractors for README content.

Separated from readme_parser.py to keep core parsing concerns distinct from
skill-generation concerns.  All four functions operate only on raw string
input and stdlib — no dependency on readme_parser internals.
"""

import re
from pathlib import Path
from typing import List, Optional


def extract_purpose(readme: str) -> str:
    """Extract a single-line purpose from the first real paragraph after the title.

    Skips noise lines that typically appear between a title and the actual
    description: badge lines, blockquote taglines, full-bold marketing blurbs,
    horizontal rules, and lines that are too short to be meaningful.
    """
    lines = readme.split("\n")
    found_title = False
    for line in lines:
        stripped = line.strip()

        if not found_title:
            if stripped.startswith("# "):
                found_title = True
            continue

        # Skip blank lines and sub-headers
        if not stripped or stripped.startswith("#"):
            continue

        # Skip badge lines ([![ or plain ![ image links)
        if stripped.startswith("[![") or stripped.startswith("!["):
            continue

        # Skip blockquote taglines (> ...)
        if stripped.startswith(">"):
            continue

        # Skip full-bold marketing lines (**...**)
        if re.match(r"^\*\*[^*]+\*\*\.?$", stripped):
            continue

        # Skip horizontal rules
        if re.match(r"^[-*_]{3,}$", stripped):
            continue

        # Skip lines that are too short to be a real description
        if len(stripped) < 20:
            continue

        # Strip inline markdown (links, bold, italic) for a clean sentence
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", stripped)  # links
        clean = re.sub(r"\*\*|\*|__|_", "", clean)
        return clean.rstrip(".")

    return "Solve project-specific workflow challenges"


def extract_auto_triggers(readme: str, skill_name: str) -> List[str]:
    """Generate auto-trigger suggestions from README and skill name.

    Builds triggers that are specific to the skill being created:
      1. Skill-name keyword trigger (always included).
      2. Video-file trigger — only when the README explicitly references video
         glob patterns (*.mp4, *.avi, *.mov).
      3. Domain-specific file-extension triggers discovered from the README
         (non-generic extensions only, capped at 2).

    Removed previously hard-coded tech triggers ("FFmpeg operations needed",
    "Working in frontend code: *.tsx", "Working in backend code: *.py") because
    those fired based on tech keywords found anywhere in the README prose rather
    than being meaningful trigger conditions for the skill itself.
    """
    triggers: List[str] = []

    # 1. Skill-name keyword trigger
    name_words = skill_name.replace("-", " ").split()
    quoted_words = [f'"{w}"' for w in name_words]
    triggers.append(f"User mentions: {', '.join(quoted_words)}")

    # 2. Video-file trigger — only when the README explicitly lists video globs
    if re.search(r"\*\.(mp4|avi|mov)", readme):
        triggers.append("Working with video files: *.mp4, *.avi, *.mov")

    # 3. Domain-specific file-extension triggers (cap at 2 extra).
    # Sources:
    #   a. Explicit glob patterns in the README:  *.j2, *.jinja2
    #   b. File paths in backtick code spans:  `templates/model.py.j2`  → *.j2
    _generic = {
        "*.py",
        "*.js",
        "*.ts",
        "*.tsx",
        "*.jsx",
        "*.mp4",
        "*.avi",
        "*.mov",
        "*.md",
        "*.txt",
        "*.json",
        "*.yaml",
        "*.yml",
        "*.toml",
        "*.cfg",
        "*.ini",
        "*.sh",
    }
    seen_exts: set = set()
    candidates = list(re.findall(r"\*\.\w{1,8}", readme))  # explicit globs
    candidates += [f"*.{m}" for m in re.findall(r"`[^`]*\.([a-z][a-z0-9]{0,7})`", readme)]  # backtick paths
    for ext in candidates:
        if ext not in _generic and ext not in seen_exts:
            triggers.append(f"Working with {ext} files")
            seen_exts.add(ext)
            if len(seen_exts) >= 2:
                break

    return triggers


def extract_process_steps(readme: str) -> List[str]:
    """Extract process steps from README.

    Searches the following section headers (in priority order):
      - Quick Start / Installation / Setup  (original behaviour)
      - Workflow / Development Workflow / Development Process
      - How to Contribute / Contributing

    Captures both numbered list items (1. ...) and bullet items (- / * / +).
    Also captures fenced code blocks that appear within these sections.
    Returns up to 10 steps.
    """
    # Ordered priority: installation-style first, then broader workflow sections
    SECTION_PATTERNS = [
        r"quick start|installation|setup",
        r"development workflow|development process|workflow",
        r"how to contribute|contributing",
    ]

    lines = readme.split("\n")

    def _collect_steps_from_section(pattern: str) -> List[str]:
        """Return steps found in the first section matching *pattern*."""
        collected: List[str] = []
        in_section = False
        skip_subsection = False  # True while inside a Prerequisites/Requirements sub-section

        i = 0
        while i < len(lines):
            line = lines[i]

            if in_section:
                # ── Stop condition checked FIRST ────────────────────────────────
                # Any ## (but not ###) header that isn't the section entry exits
                # the loop.  This must come BEFORE the section-entry check below
                # so that a header matching BOTH the stop pattern and the entry
                # pattern (e.g. "## Installation" when already inside
                # "## Quick Start") terminates collection instead of re-entering.
                if re.match(r"^#{1,2}\s+\S", line) and not line.startswith("###"):
                    break

                stripped = line.strip()

                # ── Sub-section skipping ────────────────────────────────────────
                # ### Prerequisites / ### Requirements list dependencies, not
                # workflow steps.  Skip everything until the next sub-heading.
                if re.match(r"^###\s+(?:prerequisites?|requirements?)\s*$", stripped, re.IGNORECASE):
                    skip_subsection = True
                    i += 1
                    continue

                if skip_subsection:
                    # Any new ### (or ##) header ends the skip zone
                    if re.match(r"^#{2,3}\s+\S", stripped):
                        skip_subsection = False
                        # Don't skip this line — let it be processed normally below
                    else:
                        i += 1
                        continue

                # Numbered list item
                if re.match(r"^\d+[\.)]\s+", stripped):
                    collected.append(stripped)

                # Bullet list item (-, *, +) at top-level indentation
                elif re.match(r"^[-*+]\s+", stripped):
                    collected.append(stripped)

                # Fenced code block
                elif stripped.startswith("```"):
                    code_block: List[str] = [line]
                    i += 1
                    while i < len(lines):
                        code_block.append(lines[i])
                        if i > 0 and lines[i].strip().startswith("```") and len(code_block) > 1:
                            i += 1
                            break
                        i += 1
                    collected.append("\n".join(code_block))
                    continue

            else:
                # ── Section-entry check (only when NOT already in a section) ───
                if re.search(rf"##{{1,3}}\s+.*(?:{pattern})", line, re.IGNORECASE):
                    in_section = True

            i += 1

        return collected

    # Try each pattern in priority order; merge unique steps
    seen: set = set()
    steps: List[str] = []
    for pat in SECTION_PATTERNS:
        for step in _collect_steps_from_section(pat):
            key = step[:80]  # deduplicate by first 80 chars
            if key not in seen:
                seen.add(key)
                steps.append(step)
        if steps:
            break  # Stop at the first pattern that yields results

    return steps[:10]


def extract_anti_patterns(readme: str, tech: List[str], project_path: Optional[Path] = None) -> List[str]:
    """Extract anti-patterns from both README text and project structure.

    Priority 1: explicit ❌ markers the author wrote in the README.
    Priority 2: negative imperative statements in "Coding Standards" / "Best Practices" / "Rules" sections.
    Priority 3: structural checks against the actual project on disk.
    """
    anti_patterns: List[str] = []

    # --- Priority 1: parse ❌ markers the README author explicitly wrote ---
    for line in readme.split("\n"):
        stripped = line.strip()
        # Match lines starting with ❌ (U+274C) or the text "anti-pattern" style bullets
        if stripped.startswith("\u274c"):
            pattern = stripped[1:].strip()
            if len(pattern) > 10:
                anti_patterns.append(pattern)

    # --- Priority 2: negative imperatives in standards/best-practices sections ---
    _STANDARDS_SECTION_RE = re.compile(
        r"(?m)^#{1,3}\s+.*(?:coding standards?|best practices?|rules?|standards?|guidelines?)\s*$",
        re.IGNORECASE,
    )
    _NEGATIVE_KEYWORDS = re.compile(
        r"\b(?:never|do\s+not|don'?t|avoid|must\s+not|no\s+)\b",
        re.IGNORECASE,
    )

    existing_texts = {ap.lower() for ap in anti_patterns}

    lines = readme.split("\n")
    in_standards = False
    section_level = 0

    for line in lines:
        # Detect a standards/best-practices header
        if _STANDARDS_SECTION_RE.match(line.strip()):
            in_standards = True
            # Track the header level (##, ###, etc.) to detect when the section ends
            header_match = re.match(r"^(#+)", line.strip())
            if header_match:
                section_level = len(header_match.group(1))
            else:
                section_level = 0  # Fallback if header format is unexpected
            continue

        if in_standards:
            # Stop when we hit another header of same or higher level
            header_match = re.match(r"^(#+)\s+\S", line)
            if header_match:
                this_level = len(header_match.group(1))
                if this_level <= section_level:
                    in_standards = False
                    continue

            stripped = line.strip()
            # Only process list items (bullet or numbered)
            list_match = re.match(r"^(?:[-*+]|\d+[\.)]) (.+)", stripped)
            if list_match:
                item_text = list_match.group(1).strip()
                # Only keep items that contain a negative imperative
                if _NEGATIVE_KEYWORDS.search(item_text):
                    # Strip inline markdown formatting for cleaner display
                    clean = re.sub(r"`([^`]+)`", r"\1", item_text)
                    clean = re.sub(r"\*\*|__|_|\*", "", clean).strip()
                    if len(clean) > 10 and clean.lower() not in existing_texts:
                        anti_patterns.append(clean)
                        existing_texts.add(clean.lower())

    if not project_path:
        return anti_patterns

    project_path = Path(project_path)

    if "ffmpeg" in tech:
        for py_file in project_path.rglob("*.py"):
            if any(skip in py_file.parts for skip in (".venv", "venv", "__pycache__", ".git", "node_modules")):
                continue
            try:
                py_content = py_file.read_text(encoding="utf-8", errors="replace")
                if "ffmpeg" in py_content and "shutil.which" not in py_content:
                    anti_patterns.append(
                        f"Missing FFmpeg availability check in {py_file.name} \u2192 "
                        "Add: `if not shutil.which('ffmpeg'): raise RuntimeError('ffmpeg not found')`"
                    )
                    break
            except OSError:
                pass

    if "python" in tech or "pydantic" in tech:
        has_mypy_config = (
            (project_path / "mypy.ini").exists()
            or (project_path / ".mypy.ini").exists()
            or (project_path / "setup.cfg").exists()
            or (project_path / "pyproject.toml").exists()
        )
        if not has_mypy_config:
            anti_patterns.append("No type checking config found \u2192 Run: `mypy --install-types --strict .`")

    if "pytest" in tech:
        has_pytest_config = any(
            [
                (project_path / "pytest.ini").exists(),
                (project_path / "setup.cfg").exists(),
                (project_path / "pyproject.toml").exists(),
            ]
        )
        if not has_pytest_config:
            anti_patterns.append("No pytest config found \u2192 Run: `pytest --co -q` to verify test discovery")

    return anti_patterns
