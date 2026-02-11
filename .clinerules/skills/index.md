## PROJECT CONTEXT
- **Type**: Cli Tool
- **Tech Stack**: python, gemini, claude, click
- **Domain**: The First AI That Learns Your Coding Style

## CORE SKILLS

### analyze-code
Parse and analyze codebase for quality issues.

#### Description
Analyze codebase for quality issues, providing a report with suggestions.

#### Tools
- **read**: Read code files
- **search**: Search codebase for issues
- **exec**: Execute code analysis tools

#### Triggers
- **analyze code**: Run code analysis
- **check quality**: Check code quality
- **lint**: Run linter to detect issues

#### Usage
```bash
analyze-code src/
```

#### Example Use Case
To analyze a Python project, run `analyze-code src/` and review the quality report.

### refactor-module
Refactor following project rules.

#### Description
Refactor code modules according to project rules, providing refactored code and a diff.

#### Triggers
- **refactor**: Refactor code
- **clean up code**: Clean up code structure
- **improve structure**: Improve code organization

#### Input
- **Module path**: Path to the module to refactor

#### Output
- **Refactored code**: Refactored code module
- **diff**: Diff of changes made

#### Usage
```bash
refactor-module src/module_to_refactor.py
```

#### Example Use Case
To refactor a Python module, run `refactor-module src/module_to_refactor.py` and review the refactored code and diff.

### test-coverage
Run tests and generate coverage.

#### Description
Run tests and generate test coverage report.

#### Tools
- **exec**: Execute tests
- **pytest**: Run pytest with coverage

#### Triggers
- **check coverage**: Check test coverage
- **run tests**: Run tests

#### Usage
```bash
pytest --cov=src --cov-report=term
```

#### Example Use Case
To run tests and generate coverage, run `pytest --cov=src --cov-report=term` and review the test coverage report.

## CLI TOOL SKILLS

### cli-usability-auditor
Audit CLI help messages and argument parsing.

#### Description
Audit CLI help messages and argument parsing to ensure consistency and usability.

#### When to Use
- **Adding new commands**: Ensure new commands have consistent help messages and argument parsing.
- **Inconsistent argument styling**: Identify and fix inconsistent argument styling.
- **Missing help text**: Add missing help text to CLI commands.

### command-structure-improver
Suggest better command hierarchy.

#### Description
Suggest a better command hierarchy to improve usability and consistency.

#### When to Use
- **Too many top-level commands**: Simplify command hierarchy by grouping related commands.
- **Confusing command names**: Rename commands to improve clarity and consistency.

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from `project-rules-generator-skills.md`

### In OpenClaw
```bash
/skills load project-rules-generator-skills.md
```

### Manual Reference
Read this file before working on the project.

## Quality Issues

### Structure (16/20)
- **Improve section headings**: Use clear and consistent section headings.
- **Organize content**: Organize content into clear sections and subsections.

### Clarity (18/20)
- **Use clear language**: Use clear and concise language throughout the document.
- **Define technical terms**: Define technical terms and concepts.

### Project Grounding (14/20)
- **Provide context**: Provide context for each skill and its usage.
- **Explain technical details**: Explain technical details and concepts.

### Actionability (12/20)
- **Provide concrete examples**: Provide concrete examples for each skill and its usage.
- **Specify usage**: Specify usage and input/output for each skill.

### Consistency (15/20)
- **Use consistent formatting**: Use consistent formatting throughout the document.
- **Consistent section headings**: Use consistent section headings.

## Specific Improvements Needed
- **Improve section headings**: Use clear and consistent section headings.
- **Organize content**: Organize content into clear sections and subsections.
- **Use clear language**: Use clear and concise language throughout the document.
- **Define technical terms**: Define technical terms and concepts.
- **Provide context**: Provide context for each skill and its usage.
- **Explain technical details**: Explain technical details and concepts.
- **Provide concrete examples**: Provide concrete examples for each skill and its usage.
- **Specify usage**: Specify usage and input/output for each skill.
- **Use consistent formatting**: Use consistent formatting throughout the document.
- **Consistent section headings**: Use consistent section headings.