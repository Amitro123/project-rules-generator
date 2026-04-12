"""DO and DON'T rule builders."""

from __future__ import annotations

from typing import Dict, List


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
