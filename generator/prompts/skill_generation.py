"""High-quality skill generation prompts with project-specific context."""

from pathlib import Path
from typing import Any, Dict, List, Optional

SKILL_GENERATION_PROMPT = """
You are generating a SPECIFIC, ACTIONABLE skill for project "{project_name}".

CONTEXT:
{context}

DETECTED PATTERNS IN THIS PROJECT:
{patterns}

CODE EXAMPLES FROM THIS PROJECT:
{code_examples}

AVAILABLE TOOLS:
{tools}

CRITICAL RULES — FOLLOW EXACTLY:
1. Be SPECIFIC to this project's tech stack and patterns
2. NEVER invent file paths, line numbers, or code examples. If no code examples are provided above, write GENERAL best-practice patterns WITHOUT fake "File:" references
3. NEVER invent library names or packages that are not listed in the dependencies above
4. Every action item MUST be a runnable command (not prose)
5. Only include anti-patterns you can prove exist from the context above
6. Include a "Tools" section listing runnable check/fix commands
7. If you don't have enough context for a section, write a SHORT general guideline rather than fabricating specifics
8. If the skill involves CI/CD or troubleshooting, explicitly instruct the user to verify environment parity (e.g., checking tool versions) before attempting to reproduce the issue

NOW GENERATE SKILL FOR: {skill_topic}
Topic Description: {topic_description}

RELEVANT FILES (load these for context):
{relevant_files}

EXCLUDE FILES (never load these):
{exclude_files}

OUTPUT FORMAT (markdown):
### {{skill_name}}
[One-line description grounded in this project's actual tech stack]

**Context:** [Why this skill matters for THIS project — reference only known tech]

**Triggers:** [list of short phrases that should activate this skill]

**relevant_files:** [{relevant_files_list}]

**exclude_files:** [{exclude_files_list}]

**When to use:**
- [Specific scenario 1]
- [Specific scenario 2]

**Check for:**
1. [Common issue related to this skill topic]
2. [Missing pattern to look for]

**Good pattern:**
```
[Best-practice code pattern. ONLY reference actual project files if they were provided in CODE EXAMPLES above. Otherwise show a generic pattern WITHOUT any File: path.]
```

**Tools:**
```bash
check: [runnable command]
test:  [runnable command]
lint:  [runnable command]
```

**Action items:**
1. `[runnable command]` — [what it checks]
2. `[runnable command]` — [what it verifies]
"""


def detect_project_tools(project_path: Optional[Path] = None, tech_stack: Optional[List[str]] = None) -> Dict[str, str]:
    """Detect available tools/linters in the project.

    Returns dict like:
        {'check': 'ruff check .', 'test': 'pytest', 'lint': 'mypy .', 'format': 'black .'}
    """
    tools: Dict[str, str] = {}
    tech = set(tech_stack or [])

    if project_path:
        project_path = Path(project_path)

        # Python linting
        if (project_path / "ruff.toml").exists() or (project_path / ".ruff.toml").exists():
            tools["check"] = "ruff check ."
            tools["format"] = "ruff format ."
        elif (project_path / "pyproject.toml").exists():
            try:
                content = (project_path / "pyproject.toml").read_text(encoding="utf-8", errors="replace")
                if "ruff" in content:
                    tools["check"] = "ruff check ."
                    tools["format"] = "ruff format ."
                elif "flake8" in content:
                    tools["check"] = "flake8 ."
                if "black" in content:
                    tools["format"] = "black ."
                if "mypy" in content:
                    tools["lint"] = "mypy ."
            except Exception:
                pass

        # Detect from requirements
        for req_file in ["requirements.txt", "requirements-dev.txt"]:
            req_path = project_path / req_file
            if req_path.exists():
                try:
                    content = req_path.read_text(encoding="utf-8", errors="replace").lower()
                    if "ruff" in content and "check" not in tools:
                        tools["check"] = "ruff check ."
                    if "mypy" in content and "lint" not in tools:
                        tools["lint"] = "mypy ."
                    if "black" in content and "format" not in tools:
                        tools["format"] = "black ."
                except Exception:
                    pass

    # Defaults based on tech stack
    if "pytest" in tech:
        tools["test"] = "pytest"
    elif "jest" in tech:
        tools["test"] = "npx jest"

    if "python" in tech and "check" not in tools:
        tools["check"] = "ruff check ."
    if "python" in tech and "lint" not in tools:
        tools["lint"] = "mypy ."

    if ("typescript" in tech or "react" in tech) and "check" not in tools:
        tools["check"] = "npx tsc --noEmit"
    if ("typescript" in tech or "react" in tech) and "lint" not in tools:
        tools["lint"] = "npx eslint ."

    return tools


def build_skill_prompt(
    skill_topic: str,
    project_name: str,
    context: Dict[str, Any],
    code_examples: List[Dict[str, Any]],
    detected_patterns: List[str],
    topic_description: str = "",
    project_path: Optional[Path] = None,
) -> str:
    """
    Build a complete skill generation prompt with project-specific context.

    Args:
        skill_topic: e.g. 'fastapi-validation'
        project_name: e.g. 'my-api'
        context: Full project context from EnhancedProjectParser
        code_examples: From CodeExampleExtractor
        detected_patterns: From StructureAnalyzer
        topic_description: Optional description for the skill topic
        project_path: Optional project root for tool detection

    Returns:
        Formatted prompt string for LLM
    """
    # Format context section
    context_str = _format_context(context)

    # Format patterns
    patterns_str = (
        "\n".join(f"- {p}" for p in detected_patterns) if detected_patterns else "No specific patterns detected."
    )

    # Format code examples
    examples_str = _format_code_examples(code_examples)

    # Detect tools
    tech_stack = context.get("metadata", {}).get("tech_stack", [])
    tools = detect_project_tools(project_path, tech_stack)
    tools_str = "\n".join(f"{k}: {v}" for k, v in tools.items()) if tools else "No specific tools detected."

    if not topic_description:
        topic_description = f"Best practices and patterns for {skill_topic.replace('-', ' ')} in this project."

    # Detect relevant/exclude files for this skill topic
    relevant, exclude = _detect_relevant_files(skill_topic, context, project_path)
    relevant_files_str = "\n".join(f"- {f}" for f in relevant) if relevant else "No specific files detected."
    exclude_files_str = "\n".join(f"- {f}" for f in exclude) if exclude else "None."
    relevant_files_list = ", ".join(f'"{f}"' for f in relevant) if relevant else ""
    exclude_files_list = ", ".join(f'"{f}"' for f in exclude) if exclude else ""

    return SKILL_GENERATION_PROMPT.format(
        project_name=project_name,
        context=context_str,
        patterns=patterns_str,
        code_examples=examples_str,
        tools=tools_str,
        skill_topic=skill_topic,
        topic_description=topic_description,
        relevant_files=relevant_files_str,
        exclude_files=exclude_files_str,
        relevant_files_list=relevant_files_list,
        exclude_files_list=exclude_files_list,
    )


def _format_context(context: Dict[str, Any]) -> str:
    """Format project context for the prompt."""
    parts = []

    metadata = context.get("metadata", {})
    if metadata:
        parts.append(f"Project Type: {metadata.get('project_type', 'unknown')}")
        parts.append(f"Tech Stack: {', '.join(metadata.get('tech_stack', []))}")
        parts.append(f"Languages: {', '.join(metadata.get('languages', []))}")

    readme = context.get("readme", {})
    description = readme.get("description", "")
    if description:
        parts.append(f"Description: {description}")

    deps = context.get("dependencies", {})
    python_deps = deps.get("python", [])
    if python_deps:
        dep_names = [d["name"] for d in python_deps[:15]]
        parts.append(f"Python Dependencies: {', '.join(dep_names)}")

    node_deps = deps.get("node", [])
    if node_deps:
        dep_names = [d["name"] for d in node_deps[:15]]
        parts.append(f"Node Dependencies: {', '.join(dep_names)}")

    tests = context.get("test_patterns", {})
    if tests.get("framework"):
        parts.append(f"Test Framework: {tests['framework']} ({tests.get('test_files', 0)} test files)")

    structure = context.get("structure", {})
    entry_points = structure.get("entry_points", [])
    if entry_points:
        parts.append(f"Entry Points: {', '.join(entry_points)}")

    return "\n".join(parts)


def _detect_relevant_files(skill_topic: str, context: Dict[str, Any], project_path: Optional[Path] = None) -> tuple:
    """Map skill topics to relevant file patterns.

    Returns:
        (relevant_files, exclude_files) — lists of glob patterns
    """
    relevant: List[str] = []
    exclude: List[str] = [
        "**/*.pyc",
        "**/__pycache__/**",
        "**/.venv/**",
        "**/node_modules/**",
    ]

    structure = context.get("structure", {})
    entry_points = structure.get("entry_points", [])
    test_info = context.get("test_patterns", {})
    metadata = context.get("metadata", {})
    tech_stack = metadata.get("tech_stack", [])

    topic_lower = skill_topic.lower().replace("-", " ")

    # Map topics to file patterns
    topic_file_map = {
        "test": ["tests/**", "conftest.py"],
        "auth": ["**/auth*.py", "**/security*.py", "**/middleware*.py"],
        "api": ["**/routes/**", "**/endpoints/**", "**/api/**", "**/views/**"],
        "database": ["**/models/**", "**/models.py", "**/db/**", "**/migrations/**"],
        "docker": ["Dockerfile", "docker-compose*.yml", ".dockerignore"],
        "ci": [".github/**", ".gitlab-ci.yml", "Jenkinsfile"],
        "config": ["config.*", "settings.*", "*.toml", "*.yaml", "*.yml"],
        "cli": ["**/cli.py", "**/main.py", "**/commands/**"],
        "validation": ["**/schemas/**", "**/models/**", "**/validators/**"],
        "async": ["**/tasks/**", "**/workers/**", "**/celery*.py"],
    }

    for keyword, patterns in topic_file_map.items():
        if keyword in topic_lower:
            relevant.extend(patterns)

    # Always include entry points
    for ep in entry_points:
        if ep not in relevant:
            relevant.append(ep)

    # Add test files if topic is about testing
    if test_info.get("framework") and "test" not in topic_lower:
        # For non-test topics, tests are secondary
        exclude.append("tests/fixtures/**")

    # If nothing matched, include general source patterns
    if not relevant:
        if "python" in tech_stack:
            relevant.extend(["**/*.py"])
        if "typescript" in tech_stack or "javascript" in tech_stack:
            relevant.extend(["src/**/*.ts", "src/**/*.tsx", "src/**/*.js"])
        # Add entry points as fallback
        relevant.extend(entry_points)

    return relevant, exclude


def _format_code_examples(examples: List[Dict[str, Any]]) -> str:
    """Format code examples for the prompt."""
    if not examples:
        return "No code examples were found for this skill topic. DO NOT invent fake file paths or code — use general best-practice patterns instead."

    parts = []
    for ex in examples[:5]:  # Limit to 5 examples
        file_path = ex.get("file", "unknown")
        line = ex.get("line", 0)
        code = ex.get("code", "")
        is_good = ex.get("is_good_example", True)
        reason = ex.get("reason", "")

        label = "GOOD" if is_good else "NEEDS IMPROVEMENT"
        header = f"**[{label}] {file_path}:{line}**"
        if reason:
            header += f" - {reason}"

        parts.append(f"{header}\n```\n{code}\n```")

    return "\n\n".join(parts)
