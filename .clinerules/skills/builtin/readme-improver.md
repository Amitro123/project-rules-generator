# Skill: README Improver

## Purpose
Automatically improve and maintain project README.md with professional content.

## Auto-Trigger
- "improve README" request
- New feature added to project
- Missing or minimal README detected

## Actions

### 1. Extract CLI Examples
- Run `click --help` or parse Click commands from `main.py`
- Generate usage examples with real flags and arguments
- Include common workflows (basic, AI, incremental)

### 2. Generate Badges
- pytest-cov coverage badge
- PyPI version badge (when published)
- Python version badge
- License badge
- CI/CD status badge

### 3. Add Quickstart + Usage
- Installation steps (pip install / from source)
- First-run example with expected output
- Common flags table with descriptions

### 4. Commit README.md
- Stage only README.md changes
- Commit with message: `docs: improve README with [changes]`

## Rules
- ALWAYS preserve existing custom content
- ALWAYS use Markdown best practices (headers, code blocks, tables)
- NEVER remove user-written sections
- NEVER add placeholder/lorem ipsum content
- Keep badges at the top, after the title
- Use `\b` blocks in Click help strings for proper formatting

## Example Output
```markdown
# Project Name

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-Passing-green.svg)](tests/)

## Quickstart

\```bash
pip install project-rules-generator
prg . --ai --constitution
\```

## Usage

| Flag | Description |
| :--- | :--- |
| `--ai` | Enable AI skill generation |
| `--incremental` | Update only changed files |
```
