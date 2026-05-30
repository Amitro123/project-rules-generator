"""
Tech Stack Detection Utilities
==============================
Consolidated tech detection logic from:
- generator/skill_creator.py (_detect_tech_stack, _detect_from_dependencies)
- generator/skill_parser.py (extract_tech_context)
"""

import json
from pathlib import Path
from typing import List, Set

from generator.tech import NPM_PKG_ALIASES, PKG_MAP, TECH_README_KEYWORDS

# Communication / notification channels. These are never promoted into a
# project's build ``tech_stack`` from README prose alone — a dashboard that
# *sends alerts via* Telegram is not "built with" Telegram. They are surfaced
# only when their actual package is a real dependency, or when the README is the
# project's sole manifest (a deps-free ops repo — see ``detect_tech_stack``).
CHANNEL_TECHS = frozenset({"telegram", "whatsapp", "slack", "discord", "messenger"})

# Alias map for tech name variations
TECH_ALIASES = {
    "fastapi": {"fastapi", "fast api"},
    "websocket": {"websocket", "websockets", "web socket"},
    "perplexity": {"perplexity", "sonar"},
    "openai": {"openai", "gpt-4", "gpt-3", "chatgpt"},
    "pytorch": {"pytorch", "torch"},
    "chrome": {"chrome", "chrome extension", "manifest.json", "background.js", "content script"},
    "gitpython": {"gitpython", "git diff", "git operations", "repo.git"},
    "mcp": {"mcp", "model context protocol", "mcp server", "mcp tool"},
}


def extract_context(tech: str, readme_content: str) -> List[str]:
    """
    Extract lines from README that mention a specific technology.

    Consolidated from SkillParser.extract_tech_context().
    """
    lines = readme_content.split("\n")
    context = []
    tech_lower = tech.lower()

    aliases = TECH_ALIASES.get(tech_lower, {tech_lower})

    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(alias in line_lower for alias in aliases):
            stripped = line.strip()
            if not stripped or stripped.startswith("```") or stripped.startswith("|--"):
                continue
            if stripped not in context:
                context.append(stripped)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if (
                        next_line
                        and not next_line.startswith("#")
                        and not next_line.startswith("```")
                        and next_line not in context
                    ):
                        context.append(next_line)

    return context[:10]


def detect_from_readme(readme_content: str) -> Set[str]:
    """
    Detect tech stack from README content (keyword-based).
    Less reliable than detect_from_dependencies - use as confirmation only.

    Each keyword match is checked via the shared negation helper
    (``generator.utils.negation.keyword_has_non_negated_mention``) so
    prose like *"This is not a Python application"* does not cause
    ``python`` to leak into the detected set. A tech is included only
    when at least one of its keywords matches in a non-negated context.
    """
    from generator.utils.negation import keyword_has_non_negated_mention

    detected = set()
    content_lower = readme_content.lower()

    for tech, keywords in TECH_README_KEYWORDS.items():
        # Multi-word keywords like "fast api" need permissive (substring)
        # matching; single-word keywords like "python" should be
        # word-bounded to avoid 'jython' -> python false positives.
        if any(
            keyword_has_non_negated_mention(
                kw,
                content_lower,
                word_boundary=(" " not in kw),
            )
            for kw in keywords
        ):
            detected.add(tech)

    return detected


def detect_from_dependencies(project_path: Path) -> Set[str]:
    """
    Detect tech stack from actual dependency files.
    Most reliable method - checks requirements.txt, package.json, Dockerfile.

    Consolidated from CoworkSkillCreator._detect_from_dependencies().
    """
    detected = set()

    # Python: requirements.txt
    requirements_file = project_path / "requirements.txt"
    if requirements_file.exists():
        try:
            content = requirements_file.read_text(encoding="utf-8", errors="ignore").lower()
            for pkg, tech in PKG_MAP.items():
                if pkg in content:
                    detected.add(tech)
            detected.add("python")  # Has requirements.txt = Python project
        except OSError:
            pass

    # Python: pyproject.toml (covers PEP 621 [project] and poetry [tool.poetry] deps)
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
            for pkg, tech in PKG_MAP.items():
                if pkg in content:
                    detected.add(tech)
            detected.add("python")
        except OSError:
            pass

    # Node: package.json — match against *exact* dependency keys.
    #
    # Exact-key matching (not substring) is essential: '@testing-library/jest-dom'
    # contains the substring 'jest' but is a DOM-matcher used *with* Vitest, so a
    # substring scan would falsely tag the Jest test runner on a Vitest project.
    # Detection is data-driven via PKG_MAP (built from TechProfile.packages) plus
    # NPM_PKG_ALIASES for npm names whose canonical profile carries a different
    # primary package — so adding a new tech needs only a profile entry, not edits
    # here.
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            pkg_data = json.loads(package_json.read_text(encoding="utf-8"))
            dep_keys = set(pkg_data.get("dependencies", {})) | set(pkg_data.get("devDependencies", {}))
            for dep_name in dep_keys:
                tech = PKG_MAP.get(dep_name) or NPM_PKG_ALIASES.get(dep_name)
                if tech:
                    detected.add(tech)
            # Language grounding: TypeScript when it (or its @types/*) is a real
            # dependency; otherwise plain JavaScript. README prose never decides this.
            if "typescript" in dep_keys or any(k.startswith("@types/") for k in dep_keys):
                detected.add("typescript")
            else:
                detected.add("javascript")
        except (OSError, ValueError):
            pass

    # Docker
    if (project_path / "Dockerfile").exists() or (project_path / "docker-compose.yml").exists():
        detected.add("docker")

    return detected


def detect_tech_stack(project_path: Path, readme_content: str = "") -> List[str]:
    """
    Full tech stack detection: dependencies + files + README confirmation.

    This is the primary entry point for tech detection.
    Consolidated from CoworkSkillCreator._detect_tech_stack().
    """
    detected = set()

    # 1. Most reliable: actual dependency files
    detected.update(detect_from_dependencies(project_path))

    # 2. Check for tech-specific files
    detected.update(_detect_from_files(project_path))

    # 3. README - confirmation for common techs, primary source for canvas/DXF/specialized techs
    if readme_content:
        readme_detected = detect_from_readme(readme_content)
        # These techs rarely appear in dependency files (CDN, inline, or specialized)
        # so README is the primary source for them
        readme_primary_techs = {
            "konva",
            "canvas",
            "dxf",
            "threejs",
            "babylon",
            "supabase",
            "reportlab",
            "pdf",
        }
        # Infrastructure/ops techs (docker, linux, yaml, …) also belong here — they
        # live in docs/README for ops-heavy projects that have no Python/Node
        # dependency files at all.
        try:
            from generator.tech.lookups import TECH_CATEGORIES
        except Exception:  # noqa: BLE001 — guard against import issues at startup
            TECH_CATEGORIES = {}
        if TECH_CATEGORIES:
            readme_primary_techs.update(name for name, cat in TECH_CATEGORIES.items() if cat == "infrastructure")
        else:
            readme_primary_techs.update({"docker", "docker-compose", "telegram", "yaml", "linux", "vite"})

        # Does the project have a *real build stack* — an actual language or
        # framework detected from manifests/source (not just infrastructure)?
        # Communication CHANNELS (telegram, whatsapp, …) are promoted from README
        # prose ONLY when there is no such stack: a deps-free ops/bot repo whose
        # README genuinely lists Telegram as its operational stack still surfaces
        # it, but a Vite/React app that merely *sends alerts via* Telegram does not.
        has_build_stack = any(TECH_CATEGORIES.get(t, "backend") != "infrastructure" for t in detected)

        # If no dep files were found at all, treat README as the primary source
        # for everything (docs-only / agent-skills projects).
        allow_all_from_readme = len(detected) == 0

        # Languages are intentionally NOT confirmed from README prose alone: a
        # Python project that merely *describes* a planned React/TS frontend must
        # not pick up javascript/typescript. Languages come from dependency files
        # (requirements.txt, package.json) and actual source files instead. When
        # there are no dep/source signals at all, allow_all_from_readme still lets
        # docs-only projects surface their primary language.
        for tech in readme_detected:
            if tech in CHANNEL_TECHS:
                # Already dep-backed channels stay; prose-only channels surface
                # only for deps-free ops repos with no real build stack.
                if tech in detected or not has_build_stack:
                    detected.add(tech)
                continue
            if allow_all_from_readme or tech in detected or tech in readme_primary_techs:
                detected.add(tech)

    return _reconcile_test_runner(project_path, detected)


def _reconcile_test_runner(project_path: Path, detected: Set[str]) -> List[str]:
    """Never emit two competing JS test runners.

    A project is configured for exactly one of Jest / Vitest. If both surfaced
    (e.g. a leftover ``jest`` dependency alongside a Vitest migration), keep the
    one whose config file is actually present; drop the unconfigured one.
    """
    if "jest" in detected and "vitest" in detected:
        jest_cfg = any(
            (project_path / f).exists()
            for f in ("jest.config.js", "jest.config.ts", "jest.config.cjs", "jest.config.mjs")
        )
        vitest_cfg = any(
            (project_path / f).exists() for f in ("vitest.config.js", "vitest.config.ts", "vitest.config.mjs")
        )
        if vitest_cfg and not jest_cfg:
            detected.discard("jest")
        elif jest_cfg and not vitest_cfg:
            detected.discard("vitest")
    return list(detected)


_FILE_SCAN_EXCLUDE: frozenset = frozenset(
    {".web", "node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build"}
)


def _rglob_excluding(project_path: Path, pattern: str) -> bool:
    """Return True if any file matching pattern exists outside excluded directories."""
    for p in project_path.rglob(pattern):
        if not any(part in _FILE_SCAN_EXCLUDE for part in p.parts):
            return True
    return False


def _detect_from_files(project_path: Path) -> Set[str]:
    """Detect tech from actual project files, skipping generated/vendor directories.

    Two complementary signals:

    * source-file extensions (``*.py`` / ``*.ts`` / ``*.tsx`` / ``*.jsx``) prove a
      language/framework is actually written here, not just described; and
    * config-file and directory *presence* (``vite.config.ts``, ``vitest.config.ts``,
      ``tailwind.config.ts``, ``components.json``, ``Dockerfile``, ``.github/workflows``…)
      grounds tooling that may not appear as a top-level dependency. These rules are
      data-driven via FILE_DETECTION_MAP / DIR_DETECTION_MAP, so adding a tech needs
      only a TechProfile ``detection_files`` / ``detection_dirs`` entry.
    """
    from generator.tech.lookups import DIR_DETECTION_MAP, FILE_DETECTION_MAP

    detected = set()

    if _rglob_excluding(project_path, "*.py"):
        detected.add("python")
    if _rglob_excluding(project_path, "*.ts") or _rglob_excluding(project_path, "*.tsx"):
        detected.add("typescript")
    if _rglob_excluding(project_path, "*.jsx"):
        detected.add("react")

    # Config-file presence (root-level, exact filename) — vendor dirs are not
    # consulted, so node_modules stubs cannot cause false positives.
    for filename, tech_name in FILE_DETECTION_MAP.items():
        if (project_path / filename).exists():
            detected.add(tech_name)
    for dirname, tech_name in DIR_DETECTION_MAP.items():
        if (project_path / dirname).is_dir():
            detected.add(tech_name)

    return detected
