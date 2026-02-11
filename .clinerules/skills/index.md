# Project Context
## Project Overview
### Project Type: Command-Line Interface (CLI) Tool
### Technology Stack: Python, Gemini, Claude (Integrated Development Environment (IDE) Agent), Click
### Project Domain: AI-Powered Code Quality and Style Analysis

## Project Scope and Goals
The primary objective of this project is to develop a CLI tool that analyzes code quality and style, providing actionable suggestions for improvement. The tool will be built using Python, leveraging the Gemini and Claude IDE agents, and utilizing Click for command-line interface (CLI) functionality.

## Core Skills
### Analyze Code
Parse and analyze codebases for quality issues.

#### Description
Analyze codebases for quality issues, such as syntax errors, best practices, and performance optimizations. This skill will utilize the following tools:

- `read`: Reads code files using the `pycodestyle` library (`pycodestyle.read()` command)
- `search`: Searches for specific patterns in code using the `flake8` library (`flake8.search()` command)
- `exec`: Executes code snippets for analysis using the `ast` library (`ast.exec()` command)

#### Triggers:
- `analyze code`
- `check quality`
- `lint`

#### Output:
Quality report with suggestions for improvement

#### Usage:
```bash
analyze-code src/
Example usage: Analyze the `src` directory for quality issues and generate a report with suggestions.

### Refactor Module
Refactor code to follow project rules and best practices.

#### Description
Refactor code to adhere to project rules and best practices. This skill will utilize the following tools:

- `refactor`: Refactors code using the `black` library (`black.refactor()` command)
- `clean up code`: Cleans up code using the `isort` library (`isort.clean()` command)
- `improve structure`: Improves code structure using the `yapf` library (`yapf.improve()` command)

#### Triggers:
- `refactor`
- `clean up code`
- `improve structure`

#### Input:
Module path (`--module-path` option)

#### Output:
Refactored code + diff (`--diff` option)

#### Usage:
```bash
refactor-module src/module.py
Example usage: Refactor the `src/module.py` module to follow project rules and generate a diff of the changes.

### Test Coverage
Run tests and generate coverage.

#### Description
Run tests and generate test coverage report. This skill will utilize the following tools:

- `exec`: Executes test scripts using the `unittest` library (`unittest.exec()` command)
- `pytest`: Runs tests and generates coverage report using the `pytest-cov` library (`pytest-cov.run()` command)

#### Triggers:
- `check coverage`
- `run tests`

#### Usage:
```bash
pytest --cov=src --cov-report=term
Example usage: Run tests and generate a test coverage report for the `src` directory.

## CLI Tool Skills
### CLI Usability Auditor
Audit CLI help messages and argument parsing.

#### Description
Audit CLI help messages and argument parsing to ensure consistency and clarity. This skill will utilize the following tools:

- `click`: Parses CLI arguments using the `click` library (`click.parse()` command)
- `help`: Generates help messages using the `click` library (`click.help()` command)

#### When to use:
- Adding new commands
- Inconsistent argument styling
- Missing help text

#### Usage:
```bash
cli-usability-auditor src/cli.py
Example usage: Audit the `src/cli.py` file for CLI usability issues.

### Command Structure Improver
Suggest better command hierarchy.

#### Description
Suggest a better command hierarchy for the CLI. This skill will utilize the following tools:

- `click`: Parses CLI arguments using the `click` library (`click.parse()` command)
- `help`: Generates help messages using the `click` library (`click.help()` command)

#### When to use:
- Too many top-level commands
- Confusing command names

#### Usage:
```bash
command-structure-improver src/cli.py
Example usage: Suggest a better command hierarchy for the `src/cli.py` file.

## Project Architecture and Infrastructure
### Project Structure
The project is structured as follows:

- `src/`: Source code directory
- `tests/`: Test code directory
- `docs/`: Documentation directory
- `skills/`: Skills directory

### Dependencies
The project depends on the following libraries:

- `click` (version 7.0+)
- `gemini` (version 2.0+)
- `claude` (version 1.0+)
- `pytest` (version 5.0+)

## Usage
### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from `project-rules-generator-skills.md` file.

### In OpenClaw
```bash
/skills load project-rules-generator-skills.md
### Manual Reference
Read this file before working on the project.

### Project Setup
Before running the project, ensure you have the following tools installed:

- Python 3.8+
- Click 7.0+
- Gemini 2.0+
- Claude 1.0+
- Pytest 5.0+

### Running the Project
To run the project, navigate to the project directory and execute the following command:
```bash
python -m project-rules-generator
This will launch the CLI tool and allow you to interact with the skills.

### Contributing
Contributions to the project are welcome. Please read the contributing guide before submitting a pull request.

### CLI Tool Command-Line Interface
The CLI tool provides the following commands:

- `analyze-code`: Analyze code quality and style
- `refactor-module`: Refactor code to follow project rules and best practices
- `test-coverage`: Run tests and generate coverage report
- `cli-usability-auditor`: Audit CLI help messages and argument parsing
- `command-structure-improver`: Suggest better command hierarchy

### CLI Tool Options
The CLI tool provides the following options:

- `--module-path`: Specify module path for refactoring
- `--diff`: Generate diff of refactored code
- `--cov`: Specify coverage report directory
- `--cov-report`: Specify coverage report format