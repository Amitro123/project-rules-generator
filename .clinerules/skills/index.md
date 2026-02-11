# PROJECT CONTEXT
## Overview
This document provides an overview of the CLI Tool project, including its type, technology stack, and domain.

### Type
**CLI Tool**: A command-line interface (CLI) tool is a software application that interacts with users through a text-based interface.

### Tech Stack
**Python 3.9**: The programming language used for the project.
**Gemini**: The integrated development environment (IDE) used for development.
**Claude**: The agent used for code analysis and refactoring.
**Click**: The library used for building CLI tools.
**Pytest**: The testing framework used for the project's skills.

### Domain
**Code Analysis and Refactoring**: The project aims to develop a CLI tool that analyzes and refactors codebases for quality issues.

## CORE SKILLS

### analyze-code
Parse and analyze codebases for quality issues using the built-in `read`, `search`, and `exec` tools.

#### Triggers
- `analyze code`
- `check quality`
- `lint`

#### Output
A quality report with suggestions.

#### Usage
Run the following command in your terminal to analyze the `src/` directory:
```bash
analyze-code src/
**Example Use Case:** Analyze the codebase for quality issues and receive a report with suggestions for improvement.

#### Error Handling
If the `src/` directory does not exist, the tool will display an error message indicating that the directory is not found.

### refactor-module
Refactor code modules according to project rules using the built-in `exec` tool.

#### Triggers
- `refactor`
- `clean up code`
- `improve structure`

#### Input
Module path.

#### Output
Refactored code and a diff report.

#### Usage
Run the following command in your terminal to refactor a module:
```bash
refactor-module src/module.py
**Example Use Case:** Refactor a module to improve its structure and receive a diff report of the changes.

#### Error Handling
If the module path is invalid, the tool will display an error message indicating that the module is not found.

### test-coverage
Run tests and generate coverage reports using the `pytest` tool.

#### Tools
- `exec`
- `pytest`

#### Triggers
- `check coverage`
- `run tests`

#### Usage
Run the following command in your terminal to generate a coverage report:
```bash
pytest --cov=src --cov-report=term
**Example Use Case:** Run tests and generate a coverage report to ensure that the codebase is well-tested.

## CLI TOOL SKILLS

### cli-usability-auditor
Audit CLI help messages and argument parsing for usability and consistency.

#### When to Use
- Adding new commands
- Inconsistent argument styling
- Missing help text

#### Usage
Run the following command in your terminal to audit the CLI help messages:
```bash
cli-usability-auditor
**Example Use Case:** Audit the CLI help messages and receive a report indicating areas for improvement.

### command-structure-improver
Suggest a better command hierarchy for improved usability.

#### When to Use
- Too many top-level commands
- Confusing command names

#### Usage
Run the following command in your terminal to suggest a better command hierarchy:
```bash
command-structure-improver
**Example Use Case:** Suggest a better command hierarchy and receive a report indicating areas for improvement.

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from `project-rules-generator-skills.md` by running the following command in your terminal:
```bash
claude load skills project-rules-generator-skills.md
### In OpenClaw
```bash
/skills load project-rules-generator-skills.md
### Manual Reference
Read this file before working on the project to understand the available skills and their usage.

## PROJECT FILES

* `project-rules-generator-skills.md`: Contains the project's skills configuration
* `src/`: The codebase to be analyzed and refactored
* `tests/`: The test suite for the project's skills

## TOOL REFERENCES

* Python 3.9: The programming language used for the project
* Gemini: The IDE used for development
* Claude: The agent used for code analysis and refactoring
* Click: The library used for building CLI tools
* Pytest: The testing framework used for the project's skills

Table of Contents
=================

1. [PROJECT CONTEXT](#project-context)
2. [CORE SKILLS](#core-skills)
3. [CLI TOOL SKILLS](#cli-tool-skills)
4. [USAGE](#usage)
5. [PROJECT FILES](#project-files)
6. [TOOL REFERENCES](#tool-references)