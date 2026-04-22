---
name: python-cli-patterns
description: |
  Provides best practices and patterns for structuring command-line interfaces in Python projects, leveraging common file organization.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  tags: [python, cli, patterns, best-practices, architecture]
---

# Skill: Python CLI Patterns

## Purpose

This project utilizes Python and appears to be setting up a command-line interface (CLI) given the presence of `main.py`, `cli.py`, and a `commands/` directory. This skill provides guidance on structuring the CLI effectively, promoting modularity, testability, and a good user experience. Implementing these patterns ensures a maintainable and scalable CLI as the project grows.

## Auto-Trigger

Activate when the user mentions:
- **"python cli structure"**
- **"command line interface patterns"**
- **"organize cli commands"**

Do NOT activate for: python web, gui, api, backend

## CRITICAL

- Ensure all CLI commands are testable in isolation.
- Maintain a clear separation of concerns between argument parsing, business logic, and output formatting.
- Verify your Python environment (e.g., `python --version`) before making changes that might affect CLI execution or dependencies.

## Process

### 1. Define the CLI Entry Point

Determine if `main.py` or `cli.py` will serve as the primary entry point for your command-line application. This file should be responsible for initializing the argument parser and dispatching to subcommands.

```bash
# Example: Check if main.py is executable
grep -q '#!/usr/bin/env python' main.py || echo "Consider adding a shebang to main.py for direct execution."
```

### 2. Modularize Commands in `commands/`

For each major command or subcommand, create a dedicated Python module or file within the `commands/` directory. This keeps the CLI logic organized and prevents the main entry point from becoming a monolithic file. Each module should encapsulate the logic for its specific command.

```bash
# Example: Create a new command module
mkdir -p commands
echo -e 'import argparse\n\ndef add_subparser(subparsers):\n    parser = subparsers.add_parser("mycommand", help="A new example command")\n    parser.add_argument("--name", help="Your name")\n    parser.set_defaults(func=run_mycommand)\n\ndef run_mycommand(args):\n    print(f"Hello, {args.name if args.name else \"World\"} from mycommand!")' > commands/mycommand.py
```

### 3. Implement Argument Parsing

Use a robust argument parsing library (e.g., Python's built-in `argparse` or a third-party library like `Click`) to define commands, subcommands, and their respective arguments and options. Integrate this parsing logic into your main CLI entry point, delegating to functions or classes defined in your `commands/` modules.

```bash
# This command is illustrative and assumes main.py exists.
# It demonstrates how to update main.py to integrate commands dynamically.
# BE CAREFUL: This will overwrite content if main.py is not empty.
# Given main.py is currently empty, this is a safe initial setup.
echo -e 'import argparse\nimport importlib.util\nimport os\n\ndef load_commands(parser):\n    commands_dir = os.path.join(os.path.dirname(__file__), "commands")\n    for filename in os.listdir(commands_dir):\n        if filename.endswith(".py") and filename != "__init__.py":\n            module_name = filename[:-3]\n            module_path = os.path.join(commands_dir, filename)\n            spec = importlib.util.spec_from_file_location(module_name, module_path)\n            if spec and spec.loader:\n                module = importlib.util.module_from_spec(spec)\n                spec.loader.exec_module(module)\n                if hasattr(module, "add_subparser"):\n                    module.add_subparser(parser)\n\ndef main():\n    parser = argparse.ArgumentParser(description="My project CLI")\n    subparsers = parser.add_subparsers(dest="command", help="Available commands")\n    subparsers.required = True\n\n    load_commands(subparsers)\n\n    args = parser.parse_args()\n    if hasattr(args, "func"):\n        args.func(args)\n    else:\n        parser.print_help()\n\nif __name__ == "__main__":\n    main()' > main.py
```

### 4. Validate

After setting up your CLI entry point and a sample command, run the application to verify that commands are recognized and arguments are parsed correctly.

```bash
python main.py mycommand --name Test
python main.py --help
```

## Output

- A well-structured Python CLI application.
- `main.py` configured as the central entry point for argument parsing.
- New modules within the `commands/` directory for each distinct CLI subcommand.
- Improved maintainability and scalability for future CLI additions.

## Anti-Patterns

❌ **Don't** put all command logic directly into `main.py` or `cli.py`.
✅ **Do** modularize commands into separate files within the `commands/` directory, imported and dispatched by the main entry point.

❌ **Don't** handle argument parsing manually with `sys.argv` for complex CLIs.
✅ **Do** use a dedicated argument parsing library like `argparse` or `Click` for robust and user-friendly CLI argument handling.

## Examples

Given the provided `main.py` and `cli.py` are empty, here's a generic example demonstrating a modular `argparse` setup that aligns with the suggested `commands/` directory structure:

```python
# Generic example for main.py (after step 3)
import argparse
import importlib.util
import os

def load_commands(parser):
    """Dynamically loads command modules from the 'commands' directory."""
    commands_dir = os.path.join(os.path.dirname(__file__), "commands")
    for filename in os.listdir(commands_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            module_path = os.path.join(commands_dir, filename)
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Assumes each command module has an 'add_subparser' function
                if hasattr(module, "add_subparser"):
                    module.add_subparser(parser)

def main():
    parser = argparse.ArgumentParser(description="My project CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True # Require a subcommand

    load_commands(subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        # Call the function associated with the chosen subcommand
        args.func(args)
    else:
        # If no subcommand was chosen (and subparsers.required is False), print help
        parser.print_help()

if __name__ == "__main__":
    main()

# Generic example for commands/mycommand.py (after step 2)
import argparse

def add_subparser(subparsers):
    """Adds 'mycommand' as a subparser to the main CLI."""
    parser = subparsers.add_parser("mycommand", help="A new example command")
    parser.add_argument("--name", help="Your name")
    parser.set_defaults(func=run_mycommand) # Link to the command's execution function

def run_mycommand(args):
    """Executes the logic for 'mycommand'."""
    print(f"Hello, {args.name if args.name else 'World'} from mycommand!")

# Generic example for commands/another_command.py
import argparse

def add_subparser(subparsers):
    """Adds 'another' as a subparser to the main CLI."""
    parser = subparsers.add_parser("another", help="Another example command")
    parser.add_argument("path", help="A required path argument")
    parser.set_defaults(func=run_another_command)

def run_another_command(args):
    """Executes the logic for 'another' command."""
    print(f"Processing path: {args.path}")
```