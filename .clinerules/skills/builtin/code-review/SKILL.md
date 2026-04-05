---
name: code-review
description: |
  When the user needs to evaluate changes made to the codebase for quality, correctness, and adherence to project standards.
  When the user wants to ensure new code integrates seamlessly with existing features and dependencies like Gemini, Groq, Anthropic, and OpenAI.
  When the user is preparing code for merging and needs a structured approach to feedback.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  tags: [code-review, quality, python, testing, best-practices]
---

# Skill: Code Review Workflow

## Purpose

Without a structured code review process, developers often overlook critical bugs, introduce inconsistent patterns, or fail to leverage the full potential of specific libraries like `Pydantic` for data validation or `Click` for CLI structure. This leads to increased technical debt, harder-to-maintain code, and a higher risk of runtime errors, especially when integrating with complex LLM APIs. This skill provides a systematic approach to code review, ensuring that new contributions are robust, readable, and align with the project's standards and tech stack.

## Auto-Trigger

Activate when the user mentions:
- **"review this code"**
- **"perform a code review"**
- **"check code quality"**
- **"feedback on pull request"**

Do NOT activate for: "write code", "debug an error", "run tests"

## CRITICAL

- Always verify that all provided Python dependencies (`Click`, `Pydantic`, `pytest`, `Gemini`, `Groq`, `Anthropic`, `OpenAI`, `rich`, etc.) are being used effectively and correctly.
- Ensure that the review process is collaborative and constructive, focusing on code quality rather than developer criticism.
- Before attempting to reproduce any issues or verify fixes during a code review, explicitly instruct the user to verify their local environment parity (e.g., checking Python and dependency versions with `pip freeze`) with the CI/CD environment or the developer's environment.

## Process

### 1. Understand the Changes

To provide a meaningful review, it's crucial to first grasp the scope and intent of the changes, identifying which files were modified and the problem they aim to solve.

```bash
# Assuming a Git workflow, review the changes between the feature branch and the base branch.
# Replace 'feature-branch' and 'main' with the actual branch names.
git diff main...feature-branch
```

### 2. Run Project Tests

Running the project's tests locally is essential to catch any regressions or failures introduced by the new code and to ensure that new features are adequately covered by tests.

```bash
pytest
```

### 3. Check for Style & Structure

Maintaining consistent code style and structure, especially for `Click` commands, `Pydantic` models, and `rich` output, is vital for readability and long-term maintainability.

Manually review the code for:
- Adherence to Pythonic conventions (PEP 8 where applicable).
- Clear and consistent naming of variables, functions, and classes.
- Proper structuring of `Click` commands and options, ensuring user-friendliness.
- Correct and efficient use of `Pydantic` for data validation and schema definition, particularly for LLM inputs/outputs.
- Effective utilization of `rich` for formatting terminal output, if applicable.
- Avoidance of excessive complexity in functions or methods.

### 4. Evaluate Logic & Functionality

Thoroughly evaluating the logic ensures the code correctly implements the intended features, handles edge cases, and interacts reliably with the various LLM APIs (`Gemini`, `Groq`, `Anthropic`, `OpenAI`).

Manually review the code for:
- Correctness of algorithms and business logic.
- Proper handling of errors and exceptions, especially when interacting with external APIs.
- Efficiency of code, identifying potential performance bottlenecks.
- Security considerations, particularly when dealing with API keys or sensitive data.
- Correct integration and usage of `google-generativeai`, `groq`, `openai`, and `anthropic` libraries.

### 5. Review Documentation & Comments

Clear documentation and comments are crucial for future developers to understand, maintain, and extend the codebase, especially in complex projects involving multiple LLM integrations.

Manually review the code for:
- Presence of clear and concise docstrings for modules, classes, and functions.
- Inline comments explaining complex logic or non-obvious design choices.
- Updates to any existing project documentation that might be affected by the changes.

### 6. Provide Feedback

Providing clear, actionable, and constructive feedback is key to a successful code review process, enabling the author to understand and implement the suggested improvements.

Manually summarize findings, suggest improvements, and ask clarifying questions. Focus on specific lines or blocks of code.

## Validate

Validation ensures that the code review process was effective, confirming that all identified issues have been addressed and the code is ready for integration.

```bash
# After the author addresses feedback, re-run tests to confirm fixes and no new issues.
pytest
# If applicable, manually test the functionality to ensure it works as expected.
# Example: If main.py defines a CLI, run a relevant command.
python main.py --help
```

## Output

- A comprehensive set of comments and suggestions on the reviewed code.
- Identified potential bugs, performance issues, or architectural concerns.
- Confirmation that the code adheres to project standards and best practices.
- An approved Pull Request or a list of required changes for the author.

## Anti-Patterns

❌ **Don't** provide vague feedback like "This code is bad." This is unhelpful and doesn't guide the author towards improvement.
✅ **Do** provide specific, actionable feedback, referencing exact lines of code and explaining *why* a change is suggested (e.g., "Consider using a `Pydantic` `Field` with `min_length` for `api_key` on line X to ensure better validation, as `Pydantic` is already in use.").

❌ **Don't** ignore existing project conventions or established patterns for using libraries like `Click` or `Pydantic`. This leads to inconsistent code.
✅ **Do** ensure new code aligns with existing patterns, leveraging the strengths of each library as demonstrated in other parts of the project, or introducing new best practices consistently.

## Examples

```python
# Example of using Pydantic for robust input validation, a common area for code review.
# This ensures that API inputs are well-formed before interacting with LLM services.

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class LLMRequest(BaseModel):
    prompt: str = Field(..., min_length=10, description="The text prompt for the LLM.")
    model_name: str = Field("gpt-3.5-turbo", description="The name of the LLM model to use.")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Sampling temperature for text generation.")
    max_tokens: int = Field(150, ge=1, description="Maximum number of tokens to generate.")
    api_key: Optional[str] = Field(None, description="API key for the LLM service. Can be from environment.")

    # Example of a custom validator, often a good point for review
    # @validator('model_name')
    # def check_model_name(cls, v):
    #     supported_models = ["gpt-3.5-turbo", "gemini-pro", "claude-3-opus-20240229", "llama3-8b-8192"]
    #     if v not in supported_models:
    #         raise ValueError(f"Unsupported model name: {v}. Must be one of {supported_models}")
    #     return v

# In a code review, one might check if all necessary fields are validated,
# if custom validators are appropriate, and if the default values make sense.
```