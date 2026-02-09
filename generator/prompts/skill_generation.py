"""High-quality skill generation prompts with project-specific context."""

from typing import Dict, List, Any

SKILL_GENERATION_PROMPT = """
You are generating a SPECIFIC, ACTIONABLE skill for project "{project_name}".

CONTEXT:
{context}

DETECTED PATTERNS IN THIS PROJECT:
{patterns}

CODE EXAMPLES FROM THIS PROJECT:
{code_examples}

RULES FOR HIGH-QUALITY SKILLS:
1. Be SPECIFIC to this project's tech stack and patterns
2. Include ACTUAL code examples from the project
3. Reference ACTUAL file paths and line numbers
4. Provide CONCRETE action items

EXAMPLE OF EXCELLENT SKILL:
### fastapi-auth-patterns
Secure authentication patterns for FastAPI using JWT tokens with refresh rotation.

**Context:** This project uses FastAPI with Pydantic models and SQLAlchemy ORM. Authentication is critical for the /api/v1/users endpoints.

**When to use:**
- Adding new authenticated endpoints
- Modifying token refresh logic
- Updating user permission checks

**Check for:**
1. Missing `Depends(get_current_user)` on protected routes
2. Token expiry not validated before database queries

**Good pattern (from this project):**
```python
# File: src/api/routes/users.py
@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    return current_user
```

**Anti-pattern to fix:**
```python
# File: src/api/routes/admin.py
@router.delete("/users/{{user_id}}")  # Missing auth dependency!
async def delete_user(user_id: int):
    ...
```

**Action items:**
1. Add auth dependency to all /admin/* routes (src/api/routes/admin.py)
2. Run `pytest tests/test_auth.py -v` to verify

NOW GENERATE SKILL FOR: {skill_topic}
Topic Description: {topic_description}

OUTPUT FORMAT (markdown):
### {{skill_name}}
[One-line description]

**Context:** [Why this skill matters for THIS project]

**When to use:**
- [Specific scenario 1]
- [Specific scenario 2]

**Check for:**
1. [Specific anti-pattern with code example]
2. [Specific missing pattern]

**Good pattern (from this project):**
```python
# File: [actual file path]
[actual code snippet from the project]
```

**Anti-pattern to fix:**
```python
# File: [actual file path]
[actual bad code from the project]
```

**Action items:**
1. [Specific refactor with file:line]
2. [Specific test to run]
"""


def build_skill_prompt(
    skill_topic: str,
    project_name: str,
    context: Dict[str, Any],
    code_examples: List[Dict[str, Any]],
    detected_patterns: List[str],
    topic_description: str = '',
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

    Returns:
        Formatted prompt string for LLM
    """
    # Format context section
    context_str = _format_context(context)

    # Format patterns
    patterns_str = '\n'.join(f'- {p}' for p in detected_patterns) if detected_patterns else 'No specific patterns detected.'

    # Format code examples
    examples_str = _format_code_examples(code_examples)

    if not topic_description:
        topic_description = f"Best practices and patterns for {skill_topic.replace('-', ' ')} in this project."

    return SKILL_GENERATION_PROMPT.format(
        project_name=project_name,
        context=context_str,
        patterns=patterns_str,
        code_examples=examples_str,
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
