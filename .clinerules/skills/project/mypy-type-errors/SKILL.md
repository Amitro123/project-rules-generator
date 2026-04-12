---
name: mypy-type-errors
description: |
  Developers struggle with inconsistent type checking, leading to runtime errors and hard-to-debug issues.
  When the user reports mypy errors or type checking failures, use this skill.
  When the user asks to fix type hints or resolve type annotation issues, use this skill.
  When the user encounters `Incompatible types`, `union-attr`, or `arg-type` errors, use this skill.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  tags: [python, type-checking, mypy, code-quality, troubleshooting]
---

# Skill: Mypy Type Errors

## Purpose

Without a consistent approach to type checking, developers often introduce subtle type mismatches that only manifest as runtime errors, leading to unexpected behavior and increased debugging time. The common mistake is to ignore type hints or not integrate type checking into the development workflow. This skill provides a systematic process for identifying, understanding, and resolving `mypy` type errors, ensuring code correctness and maintainability.

## Auto-Trigger

Activate when the user mentions:
- **"mypy errors"**
- **"type checking failed"**
- **"fix type hints"**

Do NOT activate for: `install mypy`, `mypy performance`, `mypy configuration`

## CRITICAL

- Ensure `mypy` is installed and accessible in your development environment and CI/CD pipelines. This skill assumes `mypy` is available to run.
- Verify environment parity (e.g., Python and `mypy` versions) between your local setup and any CI/CD environment before attempting to reproduce or fix issues.

## Process

### 1. Identify Existing Type Errors

To understand the current state of type compliance, run `mypy` across your project. This command will list all detected type errors, providing a baseline for your work.

```bash
mypy .
```

### 2. Focus on Critical Errors

Prioritize errors that indicate clear type mismatches in core logic, especially those in `main_directories` or files with `has_tests`, as these are most likely to cause runtime issues. Address them by adding or correcting type hints.

```bash
# Example: If mypy reports errors in a specific file
mypy path/to/your/module.py
```

### 3. Understand Error Messages

Each `mypy` error message provides context about the type mismatch. Consult the `mypy` documentation for specific error codes if the message is unclear. Sometimes, a variable's type might be inferred incorrectly, or a function signature might not match its usage.

```bash
# General guidance: Review the mypy output carefully.
# For example, an error like "Incompatible types in assignment"
# indicates you're trying to assign a value of one type to a variable of another.
```

### 4. Implement Type Hint Corrections

Based on the error messages, modify your code to include correct type hints. This might involve adding `Union`, `Optional`, `Any`, or more specific types. Always aim for the most precise type hint possible.

```bash
# Example: Adding a type hint to a function parameter in main.py
# (Note: This is a conceptual example, as main.py is empty in context)

# Original (conceptual)
# def process_data(data):
#     return data.strip()

# Corrected with type hint
def process_data(data: str) -> str:
    return data.strip()
```

### 5. Re-run Mypy Incrementally

After making changes, re-run `mypy` on the modified files or directories. This iterative approach helps confirm that your fixes are effective and haven't introduced new issues.

```bash
# Re-run mypy on a specific file after making changes
mypy path/to/your/modified_file.py
```

### 6. Validate

To ensure all type errors have been addressed and no regressions have been introduced, run the full `mypy` check on the entire project again. This catches any dependencies or broader type inconsistencies that might have been overlooked.

```bash
mypy .
```

## Output

- A clear list of `mypy` type errors or a confirmation that no errors were found.
- Modified Python source files with updated type hints.

## Anti-Patterns

❌ **Don't** use `type: ignore` comments indiscriminately to suppress errors. This hides potential bugs and undermines the purpose of type checking.
✅ **Do** use `type: ignore` sparingly and with a specific explanation when `mypy` genuinely cannot infer a complex type or when dealing with third-party libraries without type stubs.

❌ **Don't** rely solely on runtime checks for type validation. This delays error detection until execution, making issues harder to debug.
✅ **Do** integrate `mypy` into your CI/CD pipeline to catch type errors before code is merged, ensuring proactive quality control.

## AI Provider Client Patterns (project-specific)

These patterns appear in `generator/ai/providers/` when the SDK stubs use `Literal[...]` unions for model names or when response content is a union of block types.

### Pattern 1 — Optional[str] for api_key / config fields

```python
# BAD: mypy infers str and rejects Optional assignment
class MyClient:
    api_key: str  # error: Incompatible types in assignment ... str | None

# GOOD
from typing import Optional
class MyClient:
    api_key: Optional[str] = None
```

### Pattern 2 — SDK Literal union for model parameter

OpenAI and Anthropic SDKs type `model` as `Literal["gpt-4o", ...]` or `Literal["claude-opus-4-6", ...] | str`.
Passing a plain `str | None` triggers `[arg-type]`. Suppress with a targeted ignore:

```python
# openai_client.py
response = self._client.chat.completions.create(
    model=self.model,  # type: ignore[arg-type]
    ...
)

# anthropic_client.py
msg = self._client.messages.create(
    model=self.model,  # type: ignore[arg-type]
    ...
)
```

### Pattern 3 — union-attr on Anthropic response content blocks

`msg.content` is `list[TextBlock | ThinkingBlock | ToolUseBlock | ...]`.
Accessing `.text` directly raises `[union-attr]` for non-text block types.

```python
# BAD
text = msg.content[0].text  # union-attr error

# GOOD — filter to blocks that actually have .text
text = next((b.text for b in msg.content if hasattr(b, "text")), "")
```

### Pattern 4 — Null guard before attribute access

```python
# BAD — mypy reports [union-attr]: Item "None" of "AIClient | None" has no attribute "generate"
def generate(self, prompt: str) -> str:
    return self.client.generate(prompt)

# GOOD
def generate(self, prompt: str) -> str:
    if self.client is None:
        return ""
    return self.client.generate(prompt)
```

### Pattern 5 — Variable name collision hides type

```python
# BAD — 'content' used for both read_text() result (str) and json.loads() result (dict)
content = package_json.read_text(encoding="utf-8")
content = json.loads(content)  # mypy: str has no attribute "get"

# GOOD — use distinct names
raw = package_json.read_text(encoding="utf-8")
pkg_data = json.loads(raw)
deps = pkg_data.get("dependencies", {})
```

## Examples

```python
# Example of a simple type-hinted function (generic, as main.py is empty)
# This pattern ensures that the 'name' parameter is always a string.

# In a file like 'src/utils.py' or 'main.py'
def greet(name: str) -> str:
    """Greets a person by their name."""
    return f"Hello, {name}!"

# Example of handling potential None values
from typing import Optional

def get_user_id(username: str) -> Optional[int]:
    """Retrieves a user ID, returns None if not found."""
    if username == "admin":
        return 1
    return None

# Mypy will warn if you try to use the result of get_user_id() directly as an int
# without checking for None.
```