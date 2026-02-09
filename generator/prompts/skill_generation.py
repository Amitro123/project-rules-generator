"""High-quality skill generation prompts with project-specific context."""

from pathlib import Path
from typing import Dict, List, Any, Optional

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

RULES FOR HIGH-QUALITY SKILLS:
1. Be SPECIFIC to this project's tech stack and patterns
2. Include ACTUAL code examples from the project — never invent examples
3. Reference ACTUAL file paths and line numbers
4. Every action item MUST be a runnable command (not prose)
5. Only include anti-patterns you can prove exist in the codebase
6. Include a "Tools" section listing runnable check/fix commands

EXAMPLE OF EXCELLENT SKILL:
### fastapi-auth-patterns
Secure authentication patterns for FastAPI using JWT tokens with refresh rotation.

**Context:** This project uses FastAPI with Pydantic models and SQLAlchemy ORM. Authentication is critical for the /api/v1/users endpoints.

**Triggers:** ["adding authenticated endpoint", "modifying token logic", "permission check"]

**When to use:**
- Adding new authenticated endpoints
- Modifying token refresh logic
- Updating user permission checks

**Check for:**
1. Missing `Depends(get_current_user)` on protected routes
2. Token expiry not validated before database queries

**Good pattern (from this project):**
```python
# File: src/api/routes/users.py:12
@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    return current_user
```

**Tools:**
```bash
check: ruff check --select S src/api/
test:  pytest tests/test_auth.py -v
lint:  mypy src/api/routes/ --strict
```

**Action items:**
1. `ruff check --select S src/api/routes/admin.py` — find unprotected routes
2. `pytest tests/test_auth.py -v` — verify auth coverage
3. `grep -rn "router\\." src/api/routes/ | grep -v "Depends"` — find routes missing auth

NOW GENERATE SKILL FOR: {skill_topic}
Topic Description: {topic_description}

OUTPUT FORMAT (markdown):
### {{skill_name}}
[One-line description]

**Context:** [Why this skill matters for THIS project]

**Triggers:** [list of short phrases that should activate this skill]

**When to use:**
- [Specific scenario 1]
- [Specific scenario 2]

**Check for:**
1. [Specific issue with code example from the project]
2. [Specific missing pattern found in the project]

**Good pattern (from this project):**
```
# File: [actual file path]:[line]
[actual code snippet from the project]
```

**Tools:**
```bash
check: [runnable command to check for issues]
test:  [runnable command to verify correctness]
lint:  [runnable command for static analysis]
```

**Action items:**
1. `[runnable command]` — [what it fixes]
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
        if (project_path / 'ruff.toml').exists() or (project_path / '.ruff.toml').exists():
            tools['check'] = 'ruff check .'
            tools['format'] = 'ruff format .'
        elif (project_path / 'pyproject.toml').exists():
            try:
                content = (project_path / 'pyproject.toml').read_text(encoding='utf-8', errors='replace')
                if 'ruff' in content:
                    tools['check'] = 'ruff check .'
                    tools['format'] = 'ruff format .'
                elif 'flake8' in content:
                    tools['check'] = 'flake8 .'
                if 'black' in content:
                    tools['format'] = 'black .'
                if 'mypy' in content:
                    tools['lint'] = 'mypy .'
            except Exception:
                pass

        # Detect from requirements
        for req_file in ['requirements.txt', 'requirements-dev.txt']:
            req_path = project_path / req_file
            if req_path.exists():
                try:
                    content = req_path.read_text(encoding='utf-8', errors='replace').lower()
                    if 'ruff' in content and 'check' not in tools:
                        tools['check'] = 'ruff check .'
                    if 'mypy' in content and 'lint' not in tools:
                        tools['lint'] = 'mypy .'
                    if 'black' in content and 'format' not in tools:
                        tools['format'] = 'black .'
                except Exception:
                    pass

    # Defaults based on tech stack
    if 'pytest' in tech:
        tools['test'] = 'pytest'
    elif 'jest' in tech:
        tools['test'] = 'npx jest'

    if 'python' in tech and 'check' not in tools:
        tools['check'] = 'ruff check .'
    if 'python' in tech and 'lint' not in tools:
        tools['lint'] = 'mypy .'

    if ('typescript' in tech or 'react' in tech) and 'check' not in tools:
        tools['check'] = 'npx tsc --noEmit'
    if ('typescript' in tech or 'react' in tech) and 'lint' not in tools:
        tools['lint'] = 'npx eslint .'

    return tools


def build_skill_prompt(
    skill_topic: str,
    project_name: str,
    context: Dict[str, Any],
    code_examples: List[Dict[str, Any]],
    detected_patterns: List[str],
    topic_description: str = '',
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
    patterns_str = '\n'.join(f'- {p}' for p in detected_patterns) if detected_patterns else 'No specific patterns detected.'

    # Format code examples
    examples_str = _format_code_examples(code_examples)

    # Detect tools
    tech_stack = context.get('metadata', {}).get('tech_stack', [])
    tools = detect_project_tools(project_path, tech_stack)
    tools_str = '\n'.join(f'{k}: {v}' for k, v in tools.items()) if tools else 'No specific tools detected.'

    if not topic_description:
        topic_description = f"Best practices and patterns for {skill_topic.replace('-', ' ')} in this project."

    return SKILL_GENERATION_PROMPT.format(
        project_name=project_name,
        context=context_str,
        patterns=patterns_str,
        code_examples=examples_str,
        tools=tools_str,
        skill_topic=skill_topic,
        topic_description=topic_description,
    )


def _format_context(context: Dict[str, Any]) -> str:
    """Format project context for the prompt."""
    parts = []

    metadata = context.get('metadata', {})
    if metadata:
        parts.append(f"Project Type: {metadata.get('project_type', 'unknown')}")
        parts.append(f"Tech Stack: {', '.join(metadata.get('tech_stack', []))}")
        parts.append(f"Languages: {', '.join(metadata.get('languages', []))}")

    readme = context.get('readme', {})
    description = readme.get('description', '')
    if description:
        parts.append(f"Description: {description}")

    deps = context.get('dependencies', {})
    python_deps = deps.get('python', [])
    if python_deps:
        dep_names = [d['name'] for d in python_deps[:15]]
        parts.append(f"Python Dependencies: {', '.join(dep_names)}")

    node_deps = deps.get('node', [])
    if node_deps:
        dep_names = [d['name'] for d in node_deps[:15]]
        parts.append(f"Node Dependencies: {', '.join(dep_names)}")

    tests = context.get('test_patterns', {})
    if tests.get('framework'):
        parts.append(f"Test Framework: {tests['framework']} ({tests.get('test_files', 0)} test files)")

    structure = context.get('structure', {})
    entry_points = structure.get('entry_points', [])
    if entry_points:
        parts.append(f"Entry Points: {', '.join(entry_points)}")

    return '\n'.join(parts)


def _format_code_examples(examples: List[Dict[str, Any]]) -> str:
    """Format code examples for the prompt."""
    if not examples:
        return 'No code examples extracted.'

    parts = []
    for ex in examples[:5]:  # Limit to 5 examples
        file_path = ex.get('file', 'unknown')
        line = ex.get('line', 0)
        code = ex.get('code', '')
        is_good = ex.get('is_good_example', True)
        reason = ex.get('reason', '')

        label = 'GOOD' if is_good else 'NEEDS IMPROVEMENT'
        header = f"**[{label}] {file_path}:{line}**"
        if reason:
            header += f" - {reason}"

        parts.append(f"{header}\n```\n{code}\n```")

    return '\n\n'.join(parts)
