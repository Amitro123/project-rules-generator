---
name: code-duplication-test
description: Detect and remove duplicate code in the project
auto_triggers:
  - keywords: [code, duplication, test, project]
    project_signals: [has_code, has_unit_tests]
tools: [flake8, bandit]
---

# Skill: Code Duplication Test

## Purpose
Identify and eliminate duplicate code in this Python project to improve maintainability and reduce bugs.

## Process

### 1. Run Code Linters
```bash
# Install required tools
pip install flake8 bandit

# Run flake8 to detect style issues
flake8 .

# Run bandit to detect security vulnerabilities
bandit -r .
```

### 2. Analyze Duplicate Code
```bash
# Run pycodestyle to detect duplicate code
pycodestyle --max-complexity 10 --max-line-length 120 .

# Run dupes to find duplicate lines of code
dupes -r .
```

### 3. Refactor Duplicate Code
```bash
# Refactor duplicate code using extracted functions
# Use a code formatter like black to reformat the code
black .
```

## Output
- No duplicate code in the project
- No style or security issues
- Improved code maintainability and reduced bugs

## Anti-Patterns
❌ **Code Duplication**: Copying and pasting code without refactoring can lead to bugs and maintenance issues. → **Extract Functions**: Break down duplicated code into reusable functions.

❌ **Unmaintainable Code**: Ignoring style and security issues can lead to a messy codebase. → **Use Code Formatters**: Use tools like black to keep the code readable and enforce coding standards.

## Tech Stack Notes
This skill assumes the project uses Python and has a basic understanding of code linters and refactoring tools.