"""README parsing and metadata extraction"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# ==========================
# Constants
# ==========================
TECH_KEYWORDS = [
    "python",
    "fastapi",
    "flask",
    "django",
    "react",
    "vue",
    "angular",
    "typescript",
    "javascript",
    "node",
    "express",
    "pytorch",
    "tensorflow",
    "sklearn",
    "transformers",
    "docker",
    "kubernetes",
    "redis",
    "postgres",
    "mongodb",
    "gemini",
    "openai",
    "anthropic",
    "claude",
    "gpt",
    "langchain",
    "perplexity",
    "groq",
    "mistral",
    "cohere",
    "ffmpeg",
    "opencv",
    "pillow",
    "moviepy",
    "whisper",
    "click",
    "argparse",
    "typer",
    "fire",
    "terraform",
    "helm",
    "aws",
    "gcp",
    "azure",
    # Web/realtime
    "websocket",
    "graphql",
    "grpc",
    # HTTP clients
    "httpx",
    "aiohttp",
    # Python ecosystem
    "pydantic",
    "uvicorn",
    "celery",
    "sqlalchemy",
    # Git/VCS
    "gitpython",
    # Chrome/browser
    "chrome",
    # Protocols/tools
    "mcp",
]

# ==========================
# Compiled regex patterns (performance + readability)
# ==========================
FENCED_LANG_RE = re.compile(r"```[a-zA-Z0-9_-]*\n[\s\S]*?```")
FENCED_GENERIC_RE = re.compile(r"```[\s\S]*?```")
INLINE_CODE_RE = re.compile(r"`[^`]+`")
MD_TABLE_RE = re.compile(r"(?m)^\|.*\|$")
HTML_TABLE_RE = re.compile(r"(?is)<table[\s\S]*?</table>")
BADGE_IMG_RE = re.compile(r"!\[.*?\]\(.*?\)")
BADGE_LINKED_RE = re.compile(r"\[!\[.*?\]\(.*?\)\]\(.*?\)")

IGNORE_SECTIONS_RE = re.compile(
    r"(?ms)^\s*#{2,}\s*[^\n]*(?:Examples?|Samples?|Supported|Comparison|vs\b|FAQ|"
    r"How It Works|What Makes|Wow Moment|Scenario|Real[\s\-_.]*World|Impact|Contributing|License|"
    r"Benchmarks?|Sponsors?|Badges?|Acknowledg(e)?ments?|Credits).*"
)

TITLE_RE = re.compile(r"^#\s+(.+?)\s*#*\s*$", re.MULTILINE)
DESC_AFTER_TITLE_RE = re.compile(r"^#.+?\n+\s*(.+?)(?=\n\n##|\n\n#|$)", re.DOTALL | re.MULTILINE)
FIRST_PARA_RE = re.compile(r"\n\n([\s\S]{20,500}?)(?=\n\n)")

# ==========================
# Public API
# ==========================


def parse_readme(readme_path: Union[str, Path]) -> Dict[str, Any]:
    """Extract structured metadata from README.md.

    Args:
        readme_path: Path to README.md file

    Returns:
        Dict with keys: name, tech_stack, features, description, installation,
        usage, troubleshooting, raw_readme, readme_path

    Raises:
        FileNotFoundError: If README.md doesn't exist
        ValueError: If README is empty or malformed
    """
    path = Path(readme_path)

    if not path.exists():
        raise FileNotFoundError(f"README not found: {readme_path}")

    content = path.read_text(encoding="utf-8", errors="replace")
    # Normalize line endings for consistent regex behavior across platforms
    if "\r\n" in content or "\r" in content:
        content = content.replace("\r\n", "\n").replace("\r", "\n")

    if not content.strip():
        raise ValueError(f"README is empty: {readme_path}")

    project_path = path.parent

    return {
        "name": _extract_project_name(content, path),
        "tech_stack": extract_tech_stack(content, project_path=project_path),
        "features": _extract_features(content),
        "description": _extract_description(content),
        "installation": _extract_section(content, ["installation", "setup", "getting started"]),
        "usage": _extract_section(content, ["usage", "how to run", "quick start"]),
        "troubleshooting": _extract_section(content, ["troubleshooting", "faq", "common issues", "gotchas"]),
        "raw_readme": content,
        "readme_path": str(path),
    }


def extract_tech_stack(content: str, project_path: Optional[Path] = None) -> List[str]:
    """Extract technologies from README content, validated against actual dependencies.

    Args:
        content: README text content
        project_path: Optional path to project root for dependency cross-referencing
    """
    # Remove full sections whose headers match common non-technical content
    content_cleaned = IGNORE_SECTIONS_RE.sub("", content)

    # Strip code blocks (```lang ... ```), including mermaid/other diagrams
    content_cleaned = FENCED_LANG_RE.sub("", content_cleaned)

    # Redundant with above but keep for safety (non-lang fenced blocks)
    content_cleaned = FENCED_GENERIC_RE.sub("", content_cleaned)

    # Strip inline code (`...`) to avoid matching tech names in code refs
    content_cleaned = INLINE_CODE_RE.sub("", content_cleaned)

    # Strip markdown tables and HTML tables
    content_cleaned = MD_TABLE_RE.sub("", content_cleaned)
    content_cleaned = HTML_TABLE_RE.sub("", content_cleaned)

    # Strip markdown image/badge syntax
    content_cleaned = BADGE_IMG_RE.sub("", content_cleaned)
    content_cleaned = BADGE_LINKED_RE.sub("", content_cleaned)

    content_lower = content_cleaned.lower()
    found = [tech for tech in TECH_KEYWORDS if re.search(rf"\b{re.escape(tech)}\b", content_lower)]

    # Cross-reference with actual dependencies if project_path is provided
    if project_path:
        found = _validate_tech_with_deps(found, Path(project_path))

    # Remove duplicates, preserve order
    return list(dict.fromkeys(found))


# ==========================
# Private helpers
# ==========================


def _extract_section(content: str, keywords: List[str]) -> str:
    """Extract content of a section matching keywords.

    Finds a header whose text roughly matches any of the provided keywords, then
    returns the content until the next header of same or higher level.
    """
    keyword_pattern = "|".join(keywords)
    header_pattern = re.compile(
        rf"(?m)^(#+)\s*(?:[^a-zA-Z0-9\n]*)\s*(?:{keyword_pattern})\s*(?:[^a-zA-Z0-9\n]*)$",
        re.IGNORECASE,
    )

    match = header_pattern.search(content)
    if not match:
        return ""

    start_pos = match.end()
    level = len(match.group(1))

    # Next header of same or higher level
    next_header_pattern = re.compile(rf"(?m)^#{{1,{level}}}\s+")
    next_match = next_header_pattern.search(content, start_pos)
    end_pos = next_match.start() if next_match else len(content)

    return content[start_pos:end_pos].strip()


def _extract_project_name(content: str, path: Path) -> str:
    """Extract project name from first H1 heading, normalized to slug."""
    match = TITLE_RE.search(content)
    if match:
        name = match.group(1).strip()
        # Clean badges, emojis, extra text
        name = re.sub(r"\[!\[.*?\]\(.*?\)\]", "", name)  # Remove badges
        name = re.sub(r"[\U0001F3AF\U0001F680\u2728\U0001F525\U0001F4A1]", "", name)  # Remove emojis
        name = re.sub(r"[^\w\s-]", "", name).lower().strip()
        name = re.sub(r"\s+", "-", name)
        return name

    # Fallback: use directory name
    return path.parent.name.lower().replace(" ", "-")


def _validate_tech_with_deps(readme_tech: List[str], project_path: Path) -> List[str]:
    """Cross-reference README-detected tech with actual project dependencies.

    Keeps tech that is:
    - Found in requirements.txt / pyproject.toml / package.json / setup.py
    - Found as actual imports in source files
    - A language marker ('python', 'javascript', 'typescript') confirmed by file existence
    - Infrastructure confirmed by file existence (docker, kubernetes)

    If no dependency files exist at all, returns readme_tech unchanged.
    """
    dep_files = [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-llm.txt",
        "pyproject.toml",
        "package.json",
        "setup.py",
        "setup.cfg",
    ]
    has_any_deps = any((project_path / f).exists() for f in dep_files)
    has_any_source = list(project_path.glob("*.py")) or (project_path / "package.json").exists()
    if not has_any_deps and not has_any_source:
        return readme_tech

    confirmed = set()

    # Language detection from files
    if (project_path / "requirements.txt").exists() or list(project_path.glob("*.py")):
        confirmed.add("python")
    if (project_path / "package.json").exists():
        confirmed.add("javascript")
        confirmed.add("node")

    # Infrastructure from files
    if (project_path / "Dockerfile").exists():
        confirmed.add("docker")
    if (project_path / "docker-compose.yml").exists() or (project_path / "docker-compose.yaml").exists():
        confirmed.add("docker")
    if any(project_path.glob("*.tf")):
        confirmed.add("terraform")

    # Read actual dependency files
    dep_content = ""
    for dep_file in [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-llm.txt",
    ]:
        dep_path = project_path / dep_file
        if dep_path.exists():
            try:
                dep_content += dep_path.read_text(encoding="utf-8", errors="replace").lower() + "\n"
            except Exception:
                pass

    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            dep_content += pyproject.read_text(encoding="utf-8", errors="replace").lower() + "\n"
        except Exception:
            pass

    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        try:
            dep_content += pkg_json.read_text(encoding="utf-8", errors="replace").lower() + "\n"
        except Exception:
            pass

    tech_to_dep_patterns = {
        "fastapi": ["fastapi"],
        "flask": ["flask"],
        "django": ["django"],
        "react": ["react", '"react"', "'react'"],
        "vue": ["vue", '"vue"', "'vue'"],
        "angular": ["@angular"],
        "express": ["express"],
        "pytorch": ["torch", "pytorch"],
        "tensorflow": ["tensorflow"],
        "sklearn": ["scikit-learn", "sklearn"],
        "transformers": ["transformers"],
        "redis": ["redis"],
        "postgres": ["psycopg", "postgresql", "postgres"],
        "mongodb": ["pymongo", "mongodb", "mongoose"],
        "gemini": ["google-generativeai", "google-genai", "gemini"],
        "openai": ["openai"],
        "anthropic": ["anthropic"],
        "claude": ["anthropic"],
        "langchain": ["langchain"],
        "perplexity": ["perplexity", "perplexity-ai", "pplx"],
        "groq": ["groq"],
        "mistral": ["mistral", "mistralai"],
        "cohere": ["cohere"],
        "ffmpeg": ["ffmpeg"],
        "opencv": ["opencv", "cv2"],
        "pillow": ["pillow", "pil"],
        "moviepy": ["moviepy"],
        "whisper": ["whisper", "openai-whisper"],
        "click": ["click"],
        "argparse": ["argparse"],
        "typer": ["typer"],
        "fire": ["python-fire", "fire"],
        "kubernetes": ["kubernetes"],
        "typescript": ["typescript"],
        "gpt": ["openai"],
        "helm": ["helm"],
        "aws": ["boto3", "aws-cdk", "aws"],
        "gcp": ["google-cloud", "gcp"],
        "azure": ["azure"],
        "websocket": ["websockets", "websocket", "socket.io"],
        "graphql": ["graphql", "ariadne", "strawberry"],
        "grpc": ["grpcio", "grpc"],
        "httpx": ["httpx"],
        "aiohttp": ["aiohttp"],
        "pydantic": ["pydantic"],
        "uvicorn": ["uvicorn"],
        "celery": ["celery"],
        "sqlalchemy": ["sqlalchemy"],
        "gitpython": ["gitpython"],
        "chrome": ["chrome", "manifest"],
        "mcp": ["mcp"],
    }

    validated: List[str] = []
    for tech in readme_tech:
        if tech in confirmed:
            validated.append(tech)
            continue
        patterns = tech_to_dep_patterns.get(tech, [tech])
        if any(pat in dep_content for pat in patterns):
            confirmed.add(tech)
            validated.append(tech)

    # Also add tech from actual dependencies not found in README
    dep_to_tech_reverse = {}
    for tech_name, patterns in tech_to_dep_patterns.items():
        for pat in patterns:
            dep_to_tech_reverse[pat] = tech_name
    for pat, tech_name in dep_to_tech_reverse.items():
        if tech_name not in confirmed and pat in dep_content:
            validated.append(tech_name)
            confirmed.add(tech_name)

    return validated


def _extract_features(content: str, max_features: int = 10) -> List[str]:
    """Extract feature list from README."""
    features: List[str] = []

    features_section = re.search(
        r"(?:^##?\s*(?:features|key|what|capabilities))(.+?)(?=^##?|\Z)",
        content,
        re.DOTALL | re.MULTILINE | re.IGNORECASE,
    )

    if features_section:
        section_text = features_section.group(1)
        features = _parse_list_items(section_text)

    if not features:
        early_content = content[: len(content) // 2]
        features = _parse_list_items(early_content)
        features = [f for f in features if 5 < len(f) < 200]

    return features[:max_features]


def _parse_list_items(text: str) -> List[str]:
    """Extract top-level list items from text, respecting indentation.

    Supports bullets (-, *, +, emoji) and numbered lists (1. / 1)
    Only returns items at the minimal indentation level found (top-level).
    """
    items: List[str] = []
    lines = text.split("\n")
    baseline_indent: Optional[int] = None

    bullet_pattern = re.compile(r"^(\s*)(?:[\-\+\*\u2705]|\d+[\.)])\s+(.+)")

    for line in lines:
        match = bullet_pattern.match(line)
        if match:
            indent = len(match.group(1))
            content = match.group(2).strip()
            if len(content) < 5:
                continue
            if baseline_indent is None:
                baseline_indent = len(match.group(1))
            if indent == baseline_indent:
                items.append(content)

    return items


def _extract_description(content: str, max_length: int = 200) -> str:
    """Extract project description from README."""
    match = DESC_AFTER_TITLE_RE.search(content)
    if match:
        desc = match.group(1).strip()
        desc = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", desc)  # Remove links
        desc = re.sub(r"\*\*|\*|__|_", "", desc)  # Remove bold/italic
        desc = desc.replace("\n", " ")
        return desc[:max_length].strip()

    first_para = FIRST_PARA_RE.search(content)
    if first_para:
        desc = first_para.group(1).strip().replace("\n", " ")
        return desc[:max_length].strip()

    return "No description available"


# Optional public utilities kept for compatibility (used elsewhere in codebase)


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
            if header_match: # Ensure there's a match before accessing group(1)
                section_level = len(header_match.group(1))
            else:
                section_level = 0 # Fallback if header format is unexpected
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
                        f"Missing FFmpeg availability check in {py_file.name} ג†’ "
                        "Add: `if not shutil.which('ffmpeg'): raise RuntimeError('ffmpeg not found')`"
                    )
                    break
            except Exception:
                pass

    if "python" in tech or "pydantic" in tech:
        has_mypy_config = (
            (project_path / "mypy.ini").exists()
            or (project_path / ".mypy.ini").exists()
            or (project_path / "setup.cfg").exists()
            or (project_path / "pyproject.toml").exists()
        )
        if not has_mypy_config:
            anti_patterns.append("No type checking config found ג†’ Run: `mypy --install-types --strict .`")

    if "pytest" in tech:
        has_pytest_config = any(
            [
                (project_path / "pytest.ini").exists(),
                (project_path / "setup.cfg").exists(),
                (project_path / "pyproject.toml").exists(),
            ]
        )
        if not has_pytest_config:
            anti_patterns.append("No pytest config found ג†’ Run: `pytest --co -q` to verify test discovery")

    return anti_patterns
