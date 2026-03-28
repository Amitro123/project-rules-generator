"""
Rules Generator — Orchestrator
================================

Replaces the old function-based rules_generator.py with a class-based
orchestrator that selects the right strategy via a chain:

    CoworkStrategy  → rich priority-scored rules (prg create-rules .)
    LegacyStrategy  → context-aware DO/DON'T rules  (prg analyze .)
    StubStrategy    → minimal fallback

Backward compatibility:
    ``from generator.rules_generator import generate_rules`` still works —
    the module-level function at the bottom delegates to RulesGenerator.
    ``from generator.rules_generator import rules_to_json`` also preserved.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from generator.rules_creator import append_mandatory_anti_patterns
from generator.utils.readme_bridge import bridge_missing_context, is_readme_sufficient

# ── Strategy Protocol ─────────────────────────────────────────────────────────


class _RulesStrategy:
    """Base class for inline rules generation strategies."""

    name: str = "base"

    def can_handle(self, **kwargs) -> bool:  # noqa: ANN003
        """Return True if this strategy should be tried."""
        return True

    def generate(self, **kwargs) -> Optional[str]:  # noqa: ANN003
        """Generate rules content. Return None to fall through to next strategy."""
        raise NotImplementedError


# ── CoworkStrategy ────────────────────────────────────────────────────────────


class _CoworkStrategy(_RulesStrategy):
    """
    Wraps CoworkRulesCreator to produce priority-scored rules.md.
    Used by: prg create-rules .
    """

    name = "cowork"

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def can_handle(self, **kwargs) -> bool:
        return True  # Always available

    def generate(
        self,
        readme_content: str = "",
        tech_stack: Optional[List[str]] = None,
        enhanced_context: Optional[Dict[str, Any]] = None,
        **_,
    ) -> Optional[str]:
        from generator.rules_creator import CoworkRulesCreator

        creator = CoworkRulesCreator(self.project_path)
        content, _metadata, _quality = creator.create_rules(
            readme_content=readme_content,
            tech_stack=tech_stack,
            enhanced_context=enhanced_context,
        )
        return content


# ── LegacyStrategy ────────────────────────────────────────────────────────────


class _LegacyStrategy(_RulesStrategy):
    """
    Context-aware rules generation from actual project analysis.
    Used by: prg analyze .
    Preserves all original _generate_enhanced_rules / _generate_basic_rules logic.
    """

    name = "legacy"

    def can_handle(self, **kwargs) -> bool:
        return True  # Always available as fallback

    def generate(
        self,
        project_data: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        enhanced_context: Optional[Dict[str, Any]] = None,
        **_,
    ) -> Optional[str]:
        if project_data is None:
            return None
        cfg = config or {}
        if enhanced_context:
            return _generate_enhanced_rules(project_data, cfg, enhanced_context)
        return _generate_basic_rules(project_data, cfg)


# ── StubStrategy ──────────────────────────────────────────────────────────────


class _StubStrategy(_RulesStrategy):
    """Minimal fallback when no context is available."""

    name = "stub"

    def generate(self, **kwargs) -> str:
        return (
            "# Project Rules\n\n"
            "## DO\n\n"
            "- Follow existing project structure\n"
            "- Write tests for new features\n"
            "- Don't commit secrets or API keys\n"
        )


# ── RulesGenerator (Orchestrator) ─────────────────────────────────────────────


class RulesGenerator:
    """
    Orchestrates rules generation via a strategy chain.

    Strategy priority:
        1. CoworkStrategy  — for prg create-rules (priority-scored output)
        2. LegacyStrategy  — for prg analyze (DO/DON'T/TESTING/WORKFLOWS output)
        3. StubStrategy    — minimal fallback
    """

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self._cowork = _CoworkStrategy(self.project_path)
        self._legacy = _LegacyStrategy()
        self._stub = _StubStrategy()

    # ── Cowork path (prg create-rules .) ──────────────────────────────────────

    def create_rules(
        self,
        tech_stack: Optional[List[str]] = None,
        quality_threshold: float = 85.0,
        output_dir: Optional[Path] = None,
        enhanced_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Path, Any, Any]:
        """
        Generate Cowork-quality rules.md and write to output_dir.

        Returns:
            (output_path, metadata, quality_report)
        """
        from generator.rules_creator import CoworkRulesCreator

        out_dir = output_dir or (self.project_path / ".clinerules")
        readme_content = self._read_readme()

        # If README is missing or sparse, bridge the gap with project tree
        # (+ optional user description in interactive/CLI mode)
        if not is_readme_sufficient(readme_content):
            supplement = bridge_missing_context(self.project_path, "rules")
            if supplement:
                readme_content = supplement + "\n\n" + readme_content

        creator = CoworkRulesCreator(self.project_path)
        content, metadata, quality = creator.create_rules(
            readme_content=readme_content,
            tech_stack=tech_stack,
            enhanced_context=enhanced_context,
        )

        output_path = creator.export_to_file(content, metadata, out_dir)
        return output_path, metadata, quality

    # ── Legacy path (prg analyze .) ───────────────────────────────────────────

    def generate_legacy(
        self,
        project_data: Dict[str, Any],
        config: Dict[str, Any],
        enhanced_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate rules via the legacy enhanced-analysis path.
        Preserves full DO/DON'T/TESTING/WORKFLOWS/CONTEXT STRATEGY output.
        """
        result = self._legacy.generate(
            project_data=project_data,
            config=config,
            enhanced_context=enhanced_context,
        )
        return result or self._stub.generate()

    # ── Shared utilities ──────────────────────────────────────────────────────

    def rules_to_json(self, rules_md: str) -> str:
        """Convert rules markdown to structured JSON."""
        return rules_to_json(rules_md)

    def _read_readme(self) -> str:
        """Read README from project path."""
        from generator.utils.readme_bridge import find_readme

        p = find_readme(self.project_path)
        return p.read_text(encoding="utf-8", errors="ignore") if p else ""


# ═════════════════════════════════════════════════════════════════════════════
# LEGACY STRATEGY IMPLEMENTATION
# All original _generate_enhanced_rules / _generate_basic_rules logic preserved
# verbatim — no changes to the rules content, only wrapped in the new structure.
# ═════════════════════════════════════════════════════════════════════════════


def _generate_enhanced_rules(project_data: Dict[str, Any], config: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    """Generate rules grounded in actual project analysis."""
    name = project_data["name"]
    max_desc = config.get("generation", {}).get("max_description_length", 200)
    description = project_data["description"][:max_desc]
    tech_stack = project_data["tech_stack"]
    tech_str = ", ".join(tech_stack) if tech_stack else "standard tools"

    metadata = ctx.get("metadata", {})
    project_type = metadata.get("project_type", "unknown")
    languages = metadata.get("languages", [])

    deps = ctx.get("dependencies", {})
    python_deps = [d["name"] for d in deps.get("python", [])]
    node_deps = [d["name"] for d in deps.get("node", [])]

    structure = ctx.get("structure", {})
    entry_points = structure.get("entry_points", [])
    raw_patterns = structure.get("patterns", [])
    patterns = [p for p in raw_patterns if p == project_type or p.endswith("-tests")]

    test_info = ctx.get("test_patterns", {})
    test_framework = test_info.get("framework", "")
    test_files = test_info.get("test_files", 0)

    readme_data = ctx.get("readme", {})
    installation = readme_data.get("installation", "")
    usage = readme_data.get("usage", "")
    troubleshooting = readme_data.get("troubleshooting", "")

    arch_lines = []
    if project_type != "unknown":
        arch_lines.append(f"- **Project type**: {project_type}")
    if entry_points:
        arch_lines.append(f"- **Entry points**: {', '.join(entry_points)}")
    if patterns:
        arch_lines.append(f"- **Structural patterns**: {', '.join(patterns)}")
    if languages:
        arch_lines.append(f"- **Languages**: {', '.join(languages)}")
    arch_section = "\n".join(arch_lines) if arch_lines else "- Standard project layout"

    do_rules = _build_do_rules(tech_stack, python_deps, node_deps, project_type, test_framework, structure)
    dont_rules = _build_dont_rules(tech_stack, python_deps, project_type, structure)

    features = project_data.get("features", [])
    priorities = features[:3] if features else []
    while len(priorities) < 3:
        defaults = ["Code quality", "Test coverage", "Documentation clarity"]
        priorities.append(defaults[len(priorities)])

    test_section = _build_test_section(test_framework, test_files, test_info)
    dep_section = _build_dep_section(python_deps, node_deps)
    file_structure = _build_file_structure(structure, entry_points, patterns)
    workflow_section = _build_workflow_section(installation, usage, troubleshooting, test_framework, tech_stack)
    context_strategy = _build_context_strategy(structure, entry_points, project_type, test_info)

    template = f"""---
project: {name}
purpose: Coding & contribution rules for this workspace
version: 2.0
generated: auto
project_type: {project_type}
---

## CONTEXT

{description}

This project uses: {tech_str}

## ARCHITECTURE

{arch_section}

## FILE STRUCTURE

{file_structure}

## DEPENDENCIES

{dep_section}

## DO (must follow)

{do_rules}

## DON'T

{dont_rules}

## TESTING

{test_section}

## PRIORITIES

1. {priorities[0]}
2. {priorities[1]}
3. {priorities[2]}

## CONTEXT STRATEGY

{context_strategy}

## WORKFLOWS

{workflow_section}

---
_Generated by project-rules-generator (enhanced analysis)_
"""
    framework_hint = "react" if tech_stack and "react" in tech_stack else ""
    return append_mandatory_anti_patterns(template, framework_hint)


def _build_do_rules(
    tech_stack: List[str],
    python_deps: List[str],
    node_deps: List[str],
    project_type: str,
    test_framework: str,
    structure: Dict,
) -> str:
    """Build DO rules specific to this project's tech."""
    rules = []

    if test_framework == "pytest":
        rules.append("- Run `pytest` before committing; add tests for new features")
        if "conftest" in str(structure):
            rules.append("- Use shared fixtures from `conftest.py` — don't duplicate test setup")
    elif test_framework == "jest":
        rules.append("- Run `npx jest` before committing; add tests for new features")
    elif test_framework:
        rules.append(f"- Run `{test_framework}` tests before committing")
    else:
        rules.append("- Write tests for new features and bug fixes")

    if "python" in tech_stack:
        rules.append("- Use type hints on all public function signatures")
        if "pydantic" in python_deps:
            rules.append("- Use Pydantic models for data validation (not raw dicts)")
        if "click" in python_deps:
            rules.append("- Use Click decorators for CLI arguments — don't parse sys.argv manually")
        if "typer" in python_deps:
            rules.append("- Use Typer for CLI commands — keep command functions thin")

    if "fastapi" in python_deps or project_type == "fastapi-api":
        rules.append("- Use `Depends()` for dependency injection in route handlers")
        rules.append("- Define Pydantic response models for all endpoints")

    if project_type == "django-app":
        rules.append("- Run `python manage.py makemigrations` after model changes")
        rules.append("- Use Django ORM — don't write raw SQL without justification")

    if "flask" in python_deps:
        rules.append("- Use Blueprints for route organization in Flask")

    if "react" in node_deps or "react" in tech_stack:
        rules.append("- Use functional components with hooks — no class components")
        rules.append("- Keep components under 200 lines; extract sub-components when needed")
    if "typescript" in tech_stack or "typescript" in node_deps:
        rules.append("- Use TypeScript strict mode; avoid `any` type")

    if "docker" in tech_stack:
        rules.append("- Use multi-stage Docker builds; keep final image minimal")

    ai_techs = [
        t
        for t in tech_stack
        if t in ("perplexity", "groq", "mistral", "cohere", "openai", "anthropic", "gemini", "langchain")
    ]
    if ai_techs:
        rules.append(f"- Store API keys in `.env` or environment variables — never hardcode ({', '.join(ai_techs)})")
        rules.append("- Add retry logic with exponential backoff for external API calls")
        rules.append("- Validate and type-check API responses before using them")

    rules.append("- Follow existing project structure and naming conventions")
    if any(ep.endswith(".py") for ep in structure.get("entry_points", [])):
        rules.append("- Keep module imports at file top; use absolute imports within the project")

    return "\n".join(rules)


def _build_dont_rules(tech_stack: List[str], python_deps: List[str], project_type: str, structure: Dict) -> str:
    """Build DON'T rules specific to this project."""
    rules = []

    if "python" in tech_stack:
        rules.append("- Don't use `print()` for logging — use the `logging` module")
        rules.append("- Don't catch bare `Exception` — catch specific exceptions")
        if "click" in python_deps:
            rules.append("- Don't use `sys.exit()` in library code — raise exceptions, let Click handle exit")

    if "fastapi" in python_deps or project_type == "fastapi-api":
        rules.append("- Don't use sync functions for I/O in async route handlers")
        rules.append("- Don't skip Pydantic validation by accessing `request.json()` directly")

    if "react" in tech_stack:
        rules.append("- Don't mutate state directly — use setState/dispatch")
        rules.append("- Don't use `useEffect` without dependency arrays")

    if "docker" in tech_stack:
        rules.append("- Don't include dev dependencies in production Docker image")

    ai_techs = [
        t
        for t in tech_stack
        if t in ("perplexity", "groq", "mistral", "cohere", "openai", "anthropic", "gemini", "langchain")
    ]
    if ai_techs:
        rules.append("- Don't log or print full API responses in production (may contain PII)")
        rules.append("- Don't ignore rate-limit headers from API providers")

    rules.append("- Don't commit secrets, API keys, or `.env` files")
    rules.append("- Don't add dependencies without checking license compatibility")

    return "\n".join(rules)


def _build_test_section(test_framework: str, test_files: int, test_info: Dict) -> str:
    """Build testing section from actual test analysis."""
    lines = []
    test_cases = test_info.get("test_cases", 0)
    if test_framework:
        lines.append(f"- **Framework**: {test_framework}")
        counts = str(test_files)
        if test_cases:
            counts += f" ({test_cases} test cases)"
        lines.append(f"- **Test files**: {counts}")
        test_patterns = test_info.get("patterns", [])
        if test_patterns:
            lines.append(f"- **Test types**: {', '.join(test_patterns)}")
        if test_info.get("has_conftest"):
            lines.append("- **Fixtures**: shared via `conftest.py`")
        if test_info.get("has_fixtures"):
            lines.append("- **Test data**: `tests/fixtures/` directory")

        if test_framework == "pytest":
            lines.append("\n```bash")
            lines.append("# Run all tests")
            lines.append("pytest")
            lines.append("# Run with coverage")
            lines.append("pytest --cov")
            lines.append("# Run specific test file")
            lines.append("pytest tests/test_specific.py -v")
            lines.append("```")
        elif test_framework == "jest":
            lines.append("\n```bash")
            lines.append("npx jest")
            lines.append("npx jest --coverage")
            lines.append("```")
    else:
        lines.append("- No test framework detected")

    return "\n".join(lines)


def _build_dep_section(python_deps: List[str], node_deps: List[str]) -> str:
    """Build dependency section from parsed deps."""
    lines = []
    if python_deps:
        lines.append(f"**Python** ({len(python_deps)} packages): {', '.join(python_deps[:15])}")
        if len(python_deps) > 15:
            lines.append(f"  ... and {len(python_deps) - 15} more")
    if node_deps:
        lines.append(f"**Node** ({len(node_deps)} packages): {', '.join(node_deps[:15])}")
        if len(node_deps) > 15:
            lines.append(f"  ... and {len(node_deps) - 15} more")
    if not lines:
        lines.append("No dependency files found.")
    return "\n".join(lines)


def _build_file_structure(structure: Dict, entry_points: List[str], patterns: List[str]) -> str:
    """Build file structure section."""
    lines = []
    if entry_points:
        lines.append("**Entry points:**")
        for ep in entry_points:
            lines.append(f"- `{ep}`")
    if patterns:
        lines.append("\n**Detected patterns:**")
        for p in patterns:
            lines.append(f"- {p}")
    if not lines:
        lines.append("Standard project layout.")
    return "\n".join(lines)


def _sanitize_readme_section(text: str, max_len: int = 500) -> str:
    """Trim README section content and ensure code blocks are balanced."""
    text = text[:max_len].strip()
    fence_count = text.count("```")
    if fence_count % 2 != 0:
        text += "\n```"
    return text


def _build_workflow_section(
    installation: str,
    usage: str,
    troubleshooting: str,
    test_framework: str,
    tech_stack: List[str],
) -> str:
    """Build workflow section from README content."""
    sections = []

    if installation:
        sections.append(f"### Setup\n{_sanitize_readme_section(installation)}")

    if usage:
        sections.append(f"### Usage\n{_sanitize_readme_section(usage)}")

    if troubleshooting:
        sections.append(f"### Troubleshooting\n{_sanitize_readme_section(troubleshooting, 300)}")

    dev_lines = ["### Development"]
    dev_lines.append("```bash")
    dev_lines.append("git checkout -b feat/descriptive-name")
    if test_framework == "pytest":
        dev_lines.append("# Write code + tests, then run:")
        dev_lines.append("pytest")
    elif test_framework == "jest":
        dev_lines.append("# Write code + tests, then run:")
        dev_lines.append("npx jest")
    else:
        dev_lines.append("# Write code + tests")
    dev_lines.append("git add .")
    dev_lines.append('git commit -m "feat: descriptive message"')
    dev_lines.append("```")
    sections.append("\n".join(dev_lines))

    return "\n\n".join(sections)


def _build_context_strategy(structure: Dict, entry_points: List[str], project_type: str, test_info: Dict) -> str:
    """Build context strategy section with file loading hints per task type."""
    lines: List[str] = []

    lines.append("### File Loading by Task Type")
    lines.append("")
    lines.append("| Task | Load first | Then load |")
    lines.append("|------|-----------|-----------|")

    bug_first = "relevant module source"
    bug_then = "corresponding `test_*.py` file" if test_info.get("framework") == "pytest" else "corresponding test file"
    lines.append(f"| Bug fix | {bug_first} | {bug_then} |")

    feat_first = f"`{entry_points[0]}`" if entry_points else "architecture overview"
    lines.append(f"| New feature | {feat_first} | related modules |")
    lines.append("| Refactor | module + its dependents | test suite |")

    test_first = "`conftest.py` + test directory" if test_info.get("has_conftest") else "test directory"
    lines.append(f"| Writing tests | {test_first} | source module under test |")
    lines.append("")

    if entry_points:
        lines.append("### Module Groupings")
        lines.append("")
        for ep in entry_points:
            ep_stem = ep.replace(".py", "").replace("/", ".").replace("\\", ".")
            lines.append(f"- **{ep_stem}**: `{ep}` and its imports")
        lines.append("")

    lines.append("### Exclude from Context")
    lines.append("")
    exclude_patterns = [
        "`**/*.pyc`",
        "`**/__pycache__/**`",
        "`**/.venv/**`",
        "`**/node_modules/**`",
        "`**/*-skills.md`",
        "`**/*-skills.json`",
        "`**/.clinerules*`",
    ]
    if project_type in ("django-app",):
        exclude_patterns.append("`**/migrations/**`")
    if "docker" in project_type or any("docker" in p for p in structure.get("patterns", [])):
        exclude_patterns.append("`**/docker-compose.override.yml`")

    for pat in exclude_patterns:
        lines.append(f"- {pat}")

    return "\n".join(lines)


def _generate_basic_rules(project_data: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Generate basic rules without enhanced context (fallback)."""
    name = project_data["name"]
    description = project_data["description"][: config.get("generation", {}).get("max_description_length", 200)]
    tech_stack = project_data["tech_stack"]
    features = project_data["features"]

    tech_str = ", ".join(tech_stack) if tech_stack else "standard tools"

    priorities: List[str] = []
    if features:
        priorities = features[:3]
    else:
        priorities = ["Code quality", "Documentation clarity", "Test coverage"]

    while len(priorities) < 3:
        defaults = ["Code quality", "Documentation clarity", "Test coverage", "Security", "Performance"]
        next_default = defaults[len(priorities)]
        if next_default not in priorities:
            priorities.append(next_default)

    template = f"""---
project: {name}
purpose: Coding & contribution rules for this workspace
version: 1.0
generated: auto
---

## CONTEXT

{description}{"..." if len(project_data["description"]) > len(description) else ""}

This project uses: {tech_str}

## DO (must follow)

- Use {tech_str} as the primary tech stack
- Add type hints and docstrings to all public functions
- Write tests for new features and bug fixes
- Follow existing project structure and naming conventions
- Document breaking changes in CHANGELOG.md or release notes
- Run linters/formatters before committing (black, ruff, eslint, etc.)
- Keep functions focused and under 50 lines when possible
- Review your own code before requesting review from others

## DON'T

- Don't commit secrets, API keys, or credentials to version control
- Don't use global variables without explicit justification
- Don't bypass linting rules without documenting why
- Don't modify core infrastructure without team discussion
- Don't leave commented-out code without explaining why
- Don't add dependencies without checking license compatibility

## PRIORITIES

1. {priorities[0]}
2. {priorities[1]}
3. {priorities[2]}

## WORKFLOWS

### New Feature
```bash
git checkout -b feat/descriptive-name
# Write code + tests
# Run test suite
git add .
git commit -m "feat: descriptive message"
git push origin feat/descriptive-name
# Open PR, request review, merge to main
```

### Bug Fix
```bash
git checkout -b fix/issue-description
# Fix the bug + add regression test
# Verify fix works
git add .
git commit -m "fix: resolve issue with X"
git push origin fix/issue-description
# Open PR referencing the issue
```

### Documentation
```bash
# Docs can be edited on main for small changes
git checkout main
git pull
git commit -am "docs: update README with new feature"
git push origin main
```

---
_Generated by project-rules-generator_
"""
    framework_hint = "react" if tech_stack and "react" in tech_stack else ""
    return append_mandatory_anti_patterns(template, framework_hint)


# ═════════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY — module-level functions
# analyze_cmd.py imports these directly; they now delegate to RulesGenerator.
# ═════════════════════════════════════════════════════════════════════════════


def generate_rules(
    project_data: Dict[str, Any],
    config: Dict[str, Any],
    enhanced_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Backward-compatible entry point used by analyze_cmd.py.

    Delegates to RulesGenerator.generate_legacy() — zero behavior change.
    """
    generator = RulesGenerator()
    return generator.generate_legacy(project_data, config, enhanced_context)


def rules_to_json(rules_md: str) -> str:
    """
    Convert rules markdown to structured JSON.

    Backward-compatible module-level function.
    """
    data: Dict[str, Any] = {}

    fm_match = re.match(r"^---\n(.*?)\n---", rules_md, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                data[key.strip()] = val.strip()

    sections: Dict[str, List[str]] = {}
    current_section = None
    for line in rules_md.split("\n"):
        header = re.match(r"^##\s+(.+)$", line)
        if header:
            current_section = header.group(1).strip()
            sections[current_section] = []
        elif current_section and line.strip().startswith("-"):
            item = line.strip().lstrip("-").strip()
            if item:
                sections[current_section].append(item)

    do_rules = sections.get("DO (must follow)", [])
    dont_rules = sections.get("DON'T", [])

    data["rules"] = {"do": do_rules, "dont": dont_rules}
    data["priorities"] = sections.get("PRIORITIES", [])
    data["rules_count"] = len(do_rules) + len(dont_rules)

    skip = {"DO (must follow)", "DON'T", "PRIORITIES"}
    for section_name, items in sections.items():
        if section_name not in skip and items:
            key = section_name.lower().replace(" ", "_")
            data[key] = items

    return json.dumps(data, indent=2, ensure_ascii=False)
