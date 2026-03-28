---
name: python-debugger-best-practices
description: |
  Developers struggle with inefficient bug resolution and lack of systematic debugging; this skill provides a structured approach using Python's built-in debugger to quickly identify and fix issues.
license: MIT
allowed-tools: "Bash Read Write Edit Glob Grep"
metadata:
  tags: [python, debugger, pdb, troubleshooting, best-practices]
---

# Skill: Python Debugger Best Practices

## Purpose

Without a structured approach to debugging, developers often resort to `print()` statements, leading to slow, inconsistent bug resolution and introducing temporary, messy code. This skill guides you through effective debugging techniques using Python's standard debugger (`pdb`), enabling faster issue identification, interactive problem-solving, and cleaner code.

## Auto-Trigger

Activate when the user mentions:
- **"debug python"**
- **"pdb"**
- **"breakpoint"**

Do NOT activate for: debugging javascript, debugging go, debugging CI

## CRITICAL

- Always remove `import pdb; pdb.set_trace()` or `breakpoint()` calls from your code before committing to avoid unintended behavior or security risks in production.
- Prioritize interactive debugging with `pdb` over excessive `print()` statements for complex issues, as it provides a full view of the program's state.

## Process

### 1. Verify Environment Parity

WHY: Inconsistent Python environments can lead to irreproducible bugs or unexpected debugger behavior, wasting valuable debugging time trying to diagnose environmental differences.

```bash
python --version
```

### 2. Insert Breakpoint Marker

WHY: Inserting a breakpoint marker directly into your code allows the debugger to pause execution at a precise moment, enabling focused inspection of variables and program flow without modifying runtime behavior.

```bash
echo "Edit the relevant Python file (e.g., main.py) and insert 'import pdb; pdb.set_trace()' at the desired line. For Python 3.7 and above, you can use the simpler 'breakpoint()' function instead. For example:"
cat <<EOF
# main.py (example)
def some_problematic_function(data):
    processed_data = []
    for item in data:
        # Imagine a bug where 'item' is not what's expected
        import pdb; pdb.set_trace() # Execution will pause here
        processed_data.append(item * 2)
    return processed_data
EOF
```

### 3. Run with Debugger

WHY: Running your script with the `pdb` module allows you to interactively step through code, inspect variables, and understand the program's state at runtime, which is crucial for identifying the root cause of issues.

```bash
# If your main script is `main.py`:
python -m pdb main.py

# If you need to debug a specific test (assuming a test runner like pytest is installed, though not explicitly in dependencies):
# pytest --pdb your_test_file.py
```

### 4. Navigate and Inspect

WHY: Using debugger commands to step through code and examine variables helps pinpoint the exact cause of an issue by observing the program's state changes, allowing you to trace execution flow and variable values interactively.

```bash
echo "Once in the pdb debugger (indicated by '(Pdb)'), use the following common commands:"
echo "  - n (next): Execute the current line and stop at the next line within the current function."
echo "  - s (step): Step *into* a function call on the current line, allowing inspection of its internal logic."
echo "  - c (continue): Continue execution until the next breakpoint is hit or the program finishes."
echo "  - p <variable_name> (print): Display the value of a specified variable."
echo "  - l (list): Show the current code context around the breakpoint."
echo "  - w (where): Display a stack traceback, showing the current position in the call stack."
echo "  - q (quit): Exit the debugger and terminate the program."
```

### 5. Validate (Remove Debugging Code)

WHY: Leaving temporary debugging code like `pdb.set_trace()` or `breakpoint()` in committed code can introduce security vulnerabilities, performance overhead, or unexpected behavior in production, making cleanup a critical final step.

```bash
echo "After successfully debugging and fixing the issue, ensure all 'import pdb; pdb.set_trace()' or 'breakpoint()' calls are removed from your code before committing changes."
echo "You can use grep to quickly find them:"
grep -r "pdb.set_trace()" .
grep -r "breakpoint()" .
```

## Output

- Interactive debugging session in your terminal.
- Clear understanding of program flow and variable states at specific execution points.
- Identification and resolution of bugs.

## Anti-Patterns

❌ **Don