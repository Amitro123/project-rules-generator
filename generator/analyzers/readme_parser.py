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
    """Enrich README-detected tech with confirmation from actual dependency files.

    Strategy: UNION, not intersection.
    - README tech is always kept (it is the author's declared intent).
    - Additional tech found in dep files (requirements.txt, package.json, etc.)
      is added if not already present.

    The old intersect-only approach silently stripped the entire stack when a
    sparse pyproject.toml (e.g. containing only [tool.pytest.ini_options]) existed
    but listed none of the framework dependencies yet — common for projects that
    haven't written their deps file yet.

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
            except OSError:
                pass

    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            dep_content += pyproject.read_text(encoding="utf-8", errors="replace").lower() + "\n"
        except OSError:
            pass

    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        try:
            dep_content += pkg_json.read_text(encoding="utf-8", errors="replace").lower() + "\n"
        except OSError:
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

    # Union: always preserve all README-declared tech.
    # Dep-confirmed tech enriches the result; it never strips README entries.
    all_tech = list(readme_tech)  # start with README as ground truth
    seen = set(readme_tech)
    for tech in validated:
        if tech not in seen:
            all_tech.append(tech)
            seen.add(tech)

    return all_tech


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
        cut = len(content) // 2
        newline_pos = content.rfind("\n", 0, cut)
        if newline_pos != -1:
            cut = newline_pos + 1  # snap to line boundary
        early_content = content[:cut]
        features = _parse_list_items(early_content)
        features = [f for f in features if 5 < len(f) < 200]

        # For short READMEs the midpoint may precede all list items — retry on full content.
        if not features:
            features = _parse_list_items(content)
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


# Backward-compat re-exports — import from readme_skill_extractor directly for new code
from generator.analyzers.readme_skill_extractor import (  # noqa: F401, E402
    extract_anti_patterns,
    extract_auto_triggers,
    extract_process_steps,
    extract_purpose,
)
