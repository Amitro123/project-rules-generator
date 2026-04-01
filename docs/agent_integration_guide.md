# Agent Rules Integration Guide

This document explains how to configure `project-rules-generator` to seamlessly inject generated rules into the host IDE Agent (e.g., Gemini / Antigravity).

## The Target Injection Path
The Agent UI natively looks for Workspace customizations and rules within the `/.agents/rules/` directory. For example, when creating a workspace rule from the UI, it saves to a path like:
`/.agents/rules/prgtest123.md`

Because the Agent automatically detects and parses Markdown files inside this directory, we can wire our generation script to output directly there!

## How to Automatically Inject Generated Rules
Since `project-rules-generator` already exports project context, DOs/DONTs, and the tech stack, we can update the Python export logic so that the final step writes the payload directly into the `/.agents/rules/` folder.

### Implementation Example
In your generator script (e.g., inside `main.py` or the `cli` export command), handle the file saving like this:

```python
import os
import pathlib

# 1. Define the target injection directory for the Agent
agent_rules_dir = pathlib.Path(".agents/rules")

# 2. Ensure the directory exists (create it programmatically if missing)
agent_rules_dir.mkdir(parents=True, exist_ok=True)

# 3. Write your generated project rules straight to the target path
output_file = agent_rules_dir / "project_rules.md"

with open(output_file, "w", encoding="utf-8") as f:
    f.write(your_generated_markdown_content)

print(f"Successfully injected project rules into {output_file}!")
```

### Why this approach?
As soon as the generator script finishes executing and saves the `.md` file into `/.agents/rules/`, the IDE extension's Agent will instantly detect the file operation. It will load the new Markdown rules and adapt its behavior for the specific project—entirely automatically!
