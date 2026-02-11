## PROJECT CONTEXT
- **Type**: Cli Tool
- **Tech Stack**: python, gemini, claude, click
- **Domain**: The First AI That Learns Your Coding Style

## CORE SKILLS

### analyze-code
Parse and analyze codebase for quality issues.

**Tools:** read, search, exec

**Triggers:**
- analyze code
- check quality
- lint

**Output:** Quality report with suggestions

**Usage:**
```bash
python -m analyze-code src/
**Example Use Case:** Running `python -m analyze-code src/` on a Python project will generate a report highlighting potential issues, such as missing type hints or unused imports.

### refactor-module
Refactor following project rules.

**Triggers:**
- refactor
- clean up code
- improve structure

**Input:** Module path
**Output:** Refactored code + diff

**Usage:**
```bash
python -m refactor-module src/main.py
**Example Use Case:** Running `python -m refactor-module src/main.py` on a Python project will refactor the code according to the project's rules, generating a diff of the changes.

### test-coverage
Run tests and generate coverage.

**Tools:** exec, pytest

**Triggers:**
- check coverage
- run tests

**Usage:**
```bash
pytest --cov=src --cov-report=term
**Example Use Case:** Running `pytest --cov=src --cov-report=term` on a Python project will run the tests and generate a coverage report, indicating which parts of the code are covered by tests.

## CLI TOOL SKILLS

### cli-usability-auditor
Audit CLI help messages and argument parsing.

**When to use:**
- Adding new commands
- Inconsistent argument styling
- Missing help text

**Usage:**
```bash
python -m cli-usability-auditor src/main.py
**Example Use Case:** Running `python -m cli-usability-auditor src/main.py` on a Python project will audit the CLI help messages and argument parsing, providing suggestions for improvement.

### command-structure-improver
Suggest better command hierarchy.

**When to use:**
- Too many top-level commands
- Confusing command names

**Usage:**
```bash
python -m command-structure-improver src/main.py
**Example Use Case:** Running `python -m command-structure-improver src/main.py` on a Python project will suggest a better command hierarchy, reducing complexity and improving usability.

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from `project-rules-generator-skills.md`

### In OpenClaw
```bash
/skills load project-rules-generator-skills.md

### Manual Reference
Read this file before working on the project.

## GLOSSARY

- **python-cli**: Command-line interface built with Python
- **pytest**: Testing framework for Python
- **ruff**: Fast Python linter written in Rust

## QUALITY ANALYSIS
- **Structure**: 20/20
- **Clarity**: 18/20
- **Project Grounding**: 18/20
- **Actionability**: 20/20
- **Consistency**: 18/20

## SPECIFIC ISSUES TO FIX
1. None

## IMPROVEMENT GUIDELINES

### Clarity Improvements

**Define Technical Terms**
- Use a glossary section to define technical terms, such as `python-cli`, `pytest`, and `ruff`.

**Be Specific, Not Vague**
- Instead of saying "use good coding practices", provide specific examples, such as "use type hints for all public functions".

**Avoid Fluff**
- Remove unnecessary text, such as "it's important to remember that...".

**Explain "Why"**
- Provide explanations for why certain practices are recommended, such as "use type hints for all public functions to improve code readability and enable IDE autocomplete".

### Project Grounding Improvements

**Reference Actual Files**
- Use actual file paths and names, such as `main.py` and `generator/content_analyzer.py`.

**Use Real Commands**
- Use actual commands, such as `pytest tests/test_analyzer.py -v`.

**Include Actual Paths**
- Use actual paths, such as `tests/fixtures/`.

**Reference Project Tools**
- Mention specific tools, such as `ruff`, `mypy`, and `pytest`.
- Include actual config files, such as `pyproject.toml` and `.env`.

### Consistency Improvements

**Standardize Formatting**
- Use consistent bullet styles, code fence language tags, and header capitalization.

**Use Consistent Terminology**
- Use consistent terminology throughout the document, avoiding mixed terms.

**Match Project Conventions**
- Use project's actual naming conventions, such as `snake_case` for Python.
- Follow existing documentation style.
- Use same examples format throughout.

## ADDITIONAL EXAMPLES

### Refactor Module
```python
# Before
def add(a, b):
    return a + b

# After
def add(a: int, b: int) -> int:
    return a + b

### CLI Usability Auditor
```bash
python -m cli-usability-auditor src/main.py
**Output:**
* Missing help text for `--version` flag
* Inconsistent argument styling for `--foo` and `--bar` flags