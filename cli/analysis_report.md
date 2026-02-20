# Refactoring Analysis: main.py

## Overview
Current `main.py` is ~1722 lines. It contains CLI setup, configuration loading, and implementations for `analyze`, `design`, `plan`, `review`, `start`, `setup`, `exec`, `status`, and `agent` commands.

## Component Breakdown

1.  **CLI Setup**: `cli()` group, `load_config`, logging setup.
2.  **Analyze Command**: Giant function (~800 lines). Handles:
    -   Project source parsing
    -   Skill generation/matching
    -   Rules generation
    -   Constitution generation
    -   Skill listing/creation/removal (embedded logic)
3.  **Planning Commands**:
    -   `design`: Generates DESIGN.md
    -   `plan`: Generates PLAN.md / TASKS.yaml
    -   `review`: Reviews artifacts
4.  **Agent Workflow**:
    -   `start`: Orchestrates plan -> tasks -> ready
    -   `setup`: plan -> tasks
    -   `exec`: Executes tasks
    -   `status`: Shows progress
5.  **Agent Helper**:
    -   `agent`: Simulates auto-triggers.

## Refactoring Plan

We will split `main.py` into the following modules in `refactor/`:

### 1. `refactor/cli.py`
**Responsibility**: Entry point, Argument Parsing, Command Registration.
-   `cli()` click group.
-   `load_config()`
-   Global flags handling (verbose, etc).
-   Imports commands from other modules to register them.

### 2. `refactor/analyzer.py`
**Responsibility**: Core analysis and rules generation (`prg analyze`).
-   `analyze_command()`: The implementation of `analyze`.
-   Will need to refactor the giant function to delegate specific tasks (like listing skills) to helper functions.

### 3. `refactor/agent_commands.py` (extends User's `agent.py`)
**Responsibility**: AI Agent workflows.
-   `design_command`
-   `plan_command`
-   `review_command`
-   `start_command`
-   `setup_command`
-   `agent_command`

### 4. `refactor/jobs.py`
**Responsibility**: Task execution and status.
-   `exec_command`
-   `status_command`

### 5. `refactor/skills.py`
**Responsibility**: Skill management logic extracted from `analyze`.
-   `list_skills_impl()`
-   `create_skill_impl()`
-   `remove_skill_impl()`

## User's Requested Structure Mapping

| Current Component | New Module |
| :--- | :--- |
| `cli()`, `load_config` | `refactor/cli.py` |
| `analyze()` | `refactor/analyzer.py` |
| `agent()`, `design()`, `plan()` | `refactor/agent.py` |
| `exec()`, `status()` | `refactor/jobs.py` |
| Skill logic inside `analyze()` | `refactor/skills.py` |

## Execution Strategy
1.  Create `refactor/cli.py` with the skeleton.
2.  Extract `refactor/analyzer.py` (copy analyze content).
3.  Extract `refactor/agent.py`.
4.  Extract `refactor/jobs.py`.
5.  Extract `refactor/skills.py` and update `analyzer.py` to use it.
6.  Add `tests/test_cli.py`.
7.  Verify with `python refactor/cli.py --help`.
